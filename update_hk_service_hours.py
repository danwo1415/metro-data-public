#!/usr/bin/env python3
"""Fetch official MTR first/last train data without a browser.

Station-number mapping comes from MTR's static barrier-free search page, which
prints the station name server-side. Service-hour pages use the same numeric
station IDs, so no JavaScript execution or Playwright/Chromium is required.
"""
from __future__ import annotations

import concurrent.futures as cf
import copy
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

SERVICE_URL = "https://www.mtr.com.hk/en/customer/services/service_hours_search.php"
NAME_URL = "https://www.mtr.com.hk/en/customer/services/free_search.php"
DATA_PATH = Path("hong-kong-data.json")
VERSION_PATH = Path("version.json")
REPORT_PATH = Path("service-hours-report.json")
DEBUG_PATH = Path("service-hours-debug.json")

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "Chrome/130.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": UA,
    "Accept-Language": "en-HK,en;q=0.9",
    "Cache-Control": "no-cache",
}
MAX_STATION_ID = 125
WORKERS = 8


def norm(value: str | None) -> str:
    text = (value or "").lower().replace("&", " and ")
    text = text.replace("asia world expo", "asiaworld expo")
    text = re.sub(r"\b(station|mtr|line)\b", " ", text)
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def hhmm(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 3:
        digits = "0" + digits
    if len(digits) != 4:
        raise ValueError(f"invalid time: {value!r}")
    hour, minute = int(digits[:2]), int(digits[2:])
    if hour > 23 or minute > 59:
        raise ValueError(f"invalid time: {value!r}")
    return f"{hour:02d}:{minute:02d}"


def fetch(url: str, params: dict[str, str], timeout: int = 12) -> str:
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = requests.get(
                url,
                params=params,
                headers=HEADERS,
                timeout=timeout,
            )
            response.raise_for_status()
            response.encoding = response.apparent_encoding or "utf-8"
            return response.text
        except Exception as exc:  # network errors are reported after one retry
            last_error = exc
            if attempt == 0:
                time.sleep(0.6)
    raise RuntimeError(str(last_error))


def station_name_from_facility_page(html: str) -> str | None:
    # Search raw HTML first, then normalized visible text. This tolerates minor
    # markup changes around the result heading.
    patterns = [
        r'Search\s*Result\s*for\s*["“](.*?)["”]\s*-',
        r'Search\s*Result\s*for\s*&quot;(.*?)&quot;\s*-',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.I | re.S)
        if match:
            return BeautifulSoup(match.group(1), "html.parser").get_text(" ", strip=True)

    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    match = re.search(r'Search\s+Result\s+for\s+["“](.*?)["”]\s*-', text, flags=re.I)
    return match.group(1).strip() if match else None


def get_name_record(station_id: int) -> tuple[int, str | None, str | None]:
    try:
        html = fetch(NAME_URL, {"station": str(station_id)}, timeout=10)
        return station_id, station_name_from_facility_page(html), None
    except Exception as exc:
        return station_id, None, str(exc)


def parse_service_page(
    html: str,
    current_code: str,
    id_to_code: dict[int, str],
    name_to_code: dict[str, str],
    valid_lines: set[str],
) -> tuple[dict[str, dict[str, dict[str, str]]], list[dict[str, Any]]]:
    soup = BeautifulSoup(html, "html.parser")
    station_result: dict[str, dict[str, dict[str, str]]] = {}
    unresolved: list[dict[str, Any]] = []

    fallback_names = dict(name_to_code)
    fallback_names.update(
        {
            "city": "HOK",
            "airport asiaworld expo": "AWE",
            "airport asiaworldexpo": "AWE",
            "airport": "AIR",
            "asiaworld expo": "AWE",
        }
    )

    for heading in soup.select("h2.trainLine"):
        classes = heading.get("class") or []
        line_code = next((item for item in classes if item != "trainLine"), None)
        if not line_code or line_code not in valid_lines:
            continue

        table = heading.find_next("table")
        if table is None:
            continue

        for row in table.select("tr"):
            first_cell = row.select_one("td.firstTrain")
            cells = row.find_all("td", recursive=False)
            if first_cell is None or len(cells) < 3:
                continue

            destination: str | None = None
            destination_id: int | None = None
            span = cells[0].find(class_=re.compile(r"^js_station_\d+$"))
            if span is not None:
                for class_name in span.get("class") or []:
                    match = re.fullmatch(r"js_station_(\d+)", class_name)
                    if match:
                        destination_id = int(match.group(1))
                        destination = id_to_code.get(destination_id)
                        break

            raw_destination = cells[0].get_text(" ", strip=True)
            if destination is None and raw_destination and raw_destination != "-":
                destination = fallback_names.get(norm(raw_destination))

            try:
                first_time = hhmm(first_cell.get_text(" ", strip=True))
                last_time = hhmm(cells[-1].get_text(" ", strip=True))
            except Exception as exc:
                unresolved.append(
                    {
                        "station": current_code,
                        "line": line_code,
                        "destinationId": destination_id,
                        "destinationText": raw_destination,
                        "reason": str(exc),
                    }
                )
                continue

            if destination is None:
                unresolved.append(
                    {
                        "station": current_code,
                        "line": line_code,
                        "destinationId": destination_id,
                        "destinationText": raw_destination,
                        "first": first_time,
                        "last": last_time,
                        "reason": "destination not mapped",
                    }
                )
                continue

            station_result.setdefault(line_code, {})[destination] = {
                "first": first_time,
                "last": last_time,
                "source": "MTR official service hours",
            }

    return station_result, unresolved


def get_service_record(
    station_id: int,
    current_code: str,
    id_to_code: dict[int, str],
    name_to_code: dict[str, str],
    valid_lines: set[str],
) -> tuple[str, dict[str, dict[str, dict[str, str]]], list[dict[str, Any]], str | None]:
    try:
        html = fetch(
            SERVICE_URL,
            {"query_type": "search", "station": str(station_id)},
            timeout=12,
        )
        result, unresolved = parse_service_page(
            html, current_code, id_to_code, name_to_code, valid_lines
        )
        return current_code, result, unresolved, None
    except Exception as exc:
        return current_code, {}, [], str(exc)


def atomic_write_json(path: Path, value: Any) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temp.replace(path)


def main() -> None:
    if not DATA_PATH.exists() or not VERSION_PATH.exists():
        sys.exit("ERROR: missing hong-kong-data.json or version.json")

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(VERSION_PATH.read_text(encoding="utf-8"))
    english = data.get("english", {})
    lines = data.get("L", {})
    if not english or not lines:
        sys.exit("ERROR: hong-kong-data.json has no english/L data")

    name_to_code = {norm(name): code for code, name in english.items()}
    # Explicit official-name variants.
    aliases = {
        "hku": "HKU",
        "lohas park": "LHP",
        "asiaworld expo": "AWE",
        "asiaworldexpo": "AWE",
        "exhibition centre": "EXC",
        "disneyland resort": "DIS",
        "lo wu": "LOW",
        "lok ma chau": "LMC",
        "sham shui po": "SSP",
        "shum shui po": "SSP",
    }
    name_to_code.update(aliases)

    print("[1/4] Preflight: reading official station name...", flush=True)
    try:
        preflight_html = fetch(NAME_URL, {"station": "1"}, timeout=15)
        preflight_name = station_name_from_facility_page(preflight_html)
    except Exception as exc:
        sys.exit(f"ERROR: cannot reach official MTR station-name page: {exc}")
    if norm(preflight_name) != "central":
        DEBUG_PATH.write_text(
            json.dumps(
                {"preflightName": preflight_name, "sampleLength": len(preflight_html)},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        sys.exit(
            "ERROR: official station-name page format was not recognized; "
            "no files changed. See service-hours-debug.json"
        )
    print("  station=1 -> Central (OK)", flush=True)

    print(f"[2/4] Mapping official station IDs 1-{MAX_STATION_ID}...", flush=True)
    id_to_code: dict[int, str] = {}
    raw_names: dict[int, str] = {}
    mapping_errors: list[dict[str, Any]] = []
    completed = 0
    with cf.ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = [executor.submit(get_name_record, station_id) for station_id in range(1, MAX_STATION_ID + 1)]
        for future in cf.as_completed(futures):
            station_id, station_name, error = future.result()
            completed += 1
            if station_name:
                raw_names[station_id] = station_name
                code = name_to_code.get(norm(station_name))
                if code:
                    id_to_code[station_id] = code
            if error:
                mapping_errors.append({"stationId": station_id, "error": error})
            if completed % 20 == 0 or completed == MAX_STATION_ID:
                print(
                    f"  checked {completed}/{MAX_STATION_ID}; "
                    f"matched {len(id_to_code)}/{len(english)}",
                    flush=True,
                )

    missing_codes = sorted(set(english) - set(id_to_code.values()))
    if len(id_to_code) < 95:
        atomic_write_json(
            DEBUG_PATH,
            {
                "mappedCount": len(id_to_code),
                "mapped": {str(k): v for k, v in sorted(id_to_code.items())},
                "missingCodes": missing_codes,
                "rawNames": {str(k): v for k, v in sorted(raw_names.items())},
                "mappingErrors": mapping_errors,
            },
        )
        sys.exit(
            f"ERROR: only {len(id_to_code)} local stations mapped; no files changed. "
            "See service-hours-debug.json"
        )

    print(
        f"  mapping complete: {len(id_to_code)} stations; "
        f"missing local codes: {len(missing_codes)}",
        flush=True,
    )
    print(f"[3/4] Fetching {len(id_to_code)} official service-hour pages...", flush=True)

    service_hours: dict[str, dict[str, dict[str, dict[str, str]]]] = {}
    unresolved: list[dict[str, Any]] = []
    page_errors: list[dict[str, Any]] = []
    valid_lines = set(lines)
    completed = 0
    records = 0

    with cf.ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = [
            executor.submit(
                get_service_record,
                station_id,
                current_code,
                id_to_code,
                name_to_code,
                valid_lines,
            )
            for station_id, current_code in sorted(id_to_code.items())
        ]
        for future in cf.as_completed(futures):
            current_code, station_result, station_unresolved, error = future.result()
            completed += 1
            if station_result:
                service_hours[current_code] = station_result
                records += sum(len(destinations) for destinations in station_result.values())
            unresolved.extend(station_unresolved)
            if error:
                page_errors.append({"station": current_code, "error": error})
            if completed % 10 == 0 or completed == len(futures):
                print(
                    f"  fetched {completed}/{len(futures)}; "
                    f"stations with data {len(service_hours)}; records {records}",
                    flush=True,
                )

    report = {
        "mappedStations": len(id_to_code),
        "stationsWithServiceHours": len(service_hours),
        "records": records,
        "missingCodes": missing_codes,
        "unresolved": unresolved,
        "mappingErrors": mapping_errors,
        "pageErrors": page_errors,
    }
    atomic_write_json(REPORT_PATH, report)

    if len(service_hours) < 90 or records < 180:
        sys.exit(
            f"ERROR: validation failed: stations={len(service_hours)}, records={records}; "
            "no data/version files changed. See service-hours-report.json"
        )

    new_version = "2.4.1-hk-data-2"
    new_data = copy.deepcopy(data)
    new_manifest = copy.deepcopy(manifest)
    new_data["serviceHours"] = service_hours
    new_data["version"] = new_version
    new_data["updatedAt"] = "2026-08-02"
    new_manifest["version"] = new_version
    new_manifest["updatedAt"] = "2026-08-02"

    # Backups are made only after all network and validation work succeeds.
    DATA_PATH.with_suffix(DATA_PATH.suffix + ".bak").write_bytes(DATA_PATH.read_bytes())
    VERSION_PATH.with_suffix(VERSION_PATH.suffix + ".bak").write_bytes(VERSION_PATH.read_bytes())
    atomic_write_json(DATA_PATH, new_data)
    atomic_write_json(VERSION_PATH, new_manifest)

    print(
        f"[4/4] SUCCESS: mapped={len(id_to_code)} "
        f"stations={len(service_hours)} records={records} version={new_version}",
        flush=True,
    )


if __name__ == "__main__":
    main()
