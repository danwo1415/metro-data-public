#!/usr/bin/env python3
"""Publish the latest official Hong Kong EPD PM2.5 reading as compact JSON."""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.etree import ElementTree as ET

import requests

SOURCE_URL = "https://www.aqhi.gov.hk/epd/ddata/html/out/24pc_Eng.xml"
OUTPUT_PATH = Path("hk-environment.json")
REPORT_PATH = Path("hk-environment-report.json")
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "Chrome/130.0 Safari/537.36"
    ),
    "Accept": "application/xml,text/xml,text/plain,*/*",
    "Accept-Language": "en-HK,en;q=0.9",
    "Cache-Control": "no-cache",
}
PREFERRED = [
    "central/western",
    "centralandwestern",
    "central western",
    "mong kok",
    "mongkok",
    "eastern",
]


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def normalized(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def clean_number(value: str | None) -> float | None:
    text = (value or "").strip()
    if not text or text.upper() in {"N.A.", "N/A", "NA", "-", "--"}:
        return None
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if not match:
        return None
    number = float(match.group(0))
    return number if 0 <= number <= 1000 else None


def parse_time(value: str | None) -> datetime:
    text = (value or "").strip()
    if not text:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        dt = parsedate_to_datetime(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return datetime.min.replace(tzinfo=timezone.utc)


def fetch_xml() -> bytes:
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = requests.get(SOURCE_URL, headers=HEADERS, timeout=30)
            response.raise_for_status()
            if len(response.content) < 1000:
                raise RuntimeError(f"unexpectedly small response: {len(response.content)} bytes")
            return response.content
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"official EPD download failed: {last_error}")


def child_text(node: ET.Element, wanted: str) -> str:
    for child in list(node):
        if local_name(child.tag).lower() == wanted.lower():
            return "".join(child.itertext()).strip()
    return ""


def parse_records(content: bytes) -> list[dict[str, object]]:
    root = ET.fromstring(content)
    records: list[dict[str, object]] = []
    for node in root.iter():
        if local_name(node.tag).lower() != "pollutantconcentration":
            continue
        station = child_text(node, "StationName")
        source_time = child_text(node, "DateTime")
        pm25 = clean_number(child_text(node, "PM2.5"))
        if station and pm25 is not None:
            records.append(
                {
                    "station": station,
                    "stationNorm": normalized(station),
                    "sourceUpdatedAt": source_time,
                    "sortTime": parse_time(source_time),
                    "pm25": pm25,
                }
            )
    return records


def priority(station_norm: str) -> int:
    compact = station_norm.replace(" ", "")
    for index, name in enumerate(PREFERRED):
        target = normalized(name)
        if target in station_norm or target.replace(" ", "") in compact:
            return index
    return len(PREFERRED)


def main() -> int:
    print("[1/3] Downloading official EPD PM2.5 XML...", flush=True)
    content = fetch_xml()
    print(f"[2/3] Parsing {len(content)} bytes...", flush=True)
    records = parse_records(content)
    stations = {str(item["station"]) for item in records}
    if len(stations) < 10 or len(records) < 80:
        raise RuntimeError(
            f"safety gate failed: stations={len(stations)} valid_pm25_records={len(records)}"
        )

    records.sort(
        key=lambda item: (
            -priority(str(item["stationNorm"])),
            item["sortTime"],
        ),
        reverse=True,
    )
    chosen = records[0]
    value = float(chosen["pm25"])
    payload = {
        "pm25": int(value) if value.is_integer() else round(value, 1),
        "unit": "µg/m³",
        "station": chosen["station"],
        "sourceUpdatedAt": chosen["sourceUpdatedAt"],
        "publishedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "Hong Kong Environmental Protection Department",
        "sourceUrl": SOURCE_URL,
    }
    report = {
        "stations": len(stations),
        "validPm25Records": len(records),
        "selected": payload,
    }

    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"[3/3] SUCCESS: {payload['station']} PM2.5={payload['pm25']} {payload['unit']} "
        f"source_time={payload['sourceUpdatedAt']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}; existing published file was not intentionally removed", file=sys.stderr)
        raise SystemExit(1)
