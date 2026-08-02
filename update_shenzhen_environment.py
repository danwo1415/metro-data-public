#!/usr/bin/env python3
"""Publish Shenzhen official weather/air-quality values for the mobile app.

Required secret:
  SZ_OPEN_DATA_APP_KEY

The Shenzhen Open Data API response field names may evolve. This updater walks
nested JSON recursively, accepts common Chinese and English field names, and
writes a diagnostic report on every successful parse. It never invents a value.
"""
from __future__ import annotations

import json
import os
import re
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import requests

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "shenzhen-environment.json"
REPORT = ROOT / "shenzhen-environment-report.json"

API_BASE = "https://opendata.sz.gov.cn/api/{dataset}/1/service.xhtml"
WEATHER_DATASET = "29200_00903509"  # Shenzhen automatic-station observations
PM25_DATASET = None  # No currently discoverable official Shenzhen real-time PM2.5 dataset ID
UV_URL = "https://weather.sz.gov.cn/qixiangfuwu/zhuanxiangfuwu/jiankangqixiangfuwu/index.html"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MetroDataUpdater/1.0; +https://github.com/danwo1415/metro-data-public)",
    "Accept": "application/json,text/html,application/xhtml+xml,*/*",
}


def norm_key(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", value.lower())


def number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"-?\d+(?:\.\d+)?", str(value).replace(",", ""))
    return float(match.group()) if match else None


def walk_dicts(node: Any) -> Iterable[dict[str, Any]]:
    if isinstance(node, dict):
        yield node
        for child in node.values():
            yield from walk_dicts(child)
    elif isinstance(node, list):
        for child in node:
            yield from walk_dicts(child)


def first_text(record: dict[str, Any], keys: set[str]) -> str:
    for key, value in record.items():
        if norm_key(str(key)) in keys and value not in (None, ""):
            return str(value).strip()
    return ""


def fetch_dataset(dataset: str, app_key: str) -> Any:
    response = requests.get(
        API_BASE.format(dataset=dataset),
        params={"appKey": app_key, "page": 1, "rows": 5000},
        headers=HEADERS,
        timeout=45,
    )
    response.raise_for_status()
    try:
        payload = response.json()
    except Exception as exc:
        raise RuntimeError(
            f"Shenzhen Open Data returned non-JSON content from {response.url}: "
            f"{response.text[:200]!r}"
        ) from exc
    # Common Shenzhen Open Data error shapes. Never print the appKey.
    text = json.dumps(payload, ensure_ascii=False)[:2000]
    lowered = text.lower()
    if any(token in lowered for token in (
        "invalid appkey", "appkey错误", "appkey无效", "无访问权限",
        "未订阅", "尚未订阅", "未授权", "请先订阅", "没有权限"
    )):
        raise RuntimeError(
            f"Shenzhen Open Data rejected access to dataset {dataset}; "
            "confirm the appKey and subscribe this API in the platform"
        )
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return payload
    summary = list(payload.keys())[:20] if isinstance(payload, dict) else type(payload).__name__
    raise RuntimeError(
        f"Unexpected Shenzhen Open Data response for dataset {dataset}; "
        f"top-level structure={summary}"
    )


STATION_KEYS = {"station", "stationname", "站名", "站点名称", "监测站点", "自动站名称", "测站名称"}
TIME_KEYS = {"time", "datetime", "datatime", "obstime", "updatetime", "crttime", "ddatetime", "forecasttime", "发布时间", "更新时间", "监测时间", "观测时间", "数据时间"}


def metric_candidates(payload: Any, aliases: set[str], low: float, high: float) -> list[dict[str, Any]]:
    aliases = {norm_key(x) for x in aliases}
    out: list[dict[str, Any]] = []
    for record in walk_dicts(payload):
        station = first_text(record, STATION_KEYS)
        observed = first_text(record, TIME_KEYS)
        for key, raw in record.items():
            nk = norm_key(str(key))
            # One-letter official field names such as T must match exactly;
            # longer aliases may match descriptive field names.
            if not any(nk == alias or (len(alias) >= 3 and alias in nk) for alias in aliases):
                continue
            value = number(raw)
            if value is None or not low <= value <= high:
                continue
            out.append({"value": value, "station": station, "time": observed, "field": str(key)})
    return out


def choose(candidates: list[dict[str, Any]], preferred: tuple[str, ...]) -> dict[str, Any] | None:
    if not candidates:
        return None
    preferred_norm = tuple(norm_key(x) for x in preferred)

    def priority(item: dict[str, Any]) -> tuple[int, str]:
        station = norm_key(item.get("station", ""))
        p = len(preferred_norm)
        for index, name in enumerate(preferred_norm):
            if name and name in station:
                p = index
                break
        # Within the same station priority, prefer the lexicographically latest timestamp.
        return p, str(item.get("time", ""))

    best_priority = min(priority(item)[0] for item in candidates)
    pool = [item for item in candidates if priority(item)[0] == best_priority]
    dated = [item for item in pool if item.get("time")]
    if dated:
        return max(dated, key=lambda item: str(item.get("time", "")))
    # If the API exposes gridded/citywide records without a station label, use a
    # robust median rather than choosing an arbitrary first row.
    values = [item["value"] for item in pool]
    representative = dict(pool[0])
    representative["value"] = float(statistics.median(values))
    representative["station"] = representative.get("station") or "Shenzhen citywide median"
    return representative


def fetch_uv() -> tuple[float | None, str | None, dict[str, Any]]:
    response = requests.get(UV_URL, headers=HEADERS, timeout=45)
    response.raise_for_status()
    html = response.text
    candidates: list[tuple[float, str]] = []
    patterns = [
        r"(?:今日)?紫外线实况[\s\S]{0,800}?(?:紫外线指数|指数值|index)[^0-9]{0,30}(\d+(?:\.\d+)?)",
        r"(?:uvIndex|uv_index|uvi|uvValue)[\"']?\s*[:=]\s*[\"']?(\d+(?:\.\d+)?)",
        r"紫外线指数[^0-9]{0,40}(\d+(?:\.\d+)?)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, html, re.I):
            value = float(match.group(1))
            if 0 <= value <= 20:
                context = re.sub(r"\s+", " ", html[max(0, match.start()-80):match.end()+80])
                # Discard the static explanation bands such as 0-2, 3-5, 6-7.
                if re.search(r"0\s*-\s*2.{0,80}3\s*-\s*5", context):
                    continue
                candidates.append((value, context[:300]))
    time_match = re.search(r"实况时间[^0-9]{0,20}([0-9年月日时分:\-\s]+)", html)
    observed = time_match.group(1).strip() if time_match else None
    debug = {"matches": [{"value": value, "context": context} for value, context in candidates[:20]]}
    return (candidates[0][0] if candidates else None), observed, debug


def clean(value: float | None) -> float | int | None:
    if value is None:
        return None
    return int(value) if float(value).is_integer() else round(float(value), 1)


def main() -> int:
    app_key = os.environ.get("SZ_OPEN_DATA_APP_KEY", "").strip()
    if not app_key:
        print("ERROR: missing SZ_OPEN_DATA_APP_KEY; no files changed", file=sys.stderr)
        return 2

    print("[1/4] Fetching Shenzhen official weather observations...", flush=True)
    weather = fetch_dataset(WEATHER_DATASET, app_key)
    temp_candidates = metric_candidates(weather, {"T", "temperature", "airtemperature", "temp", "气温", "温度"}, -30, 60)
    humidity_candidates = metric_candidates(weather, {"RHSFC", "relativehumidity", "humidity", "rh", "相对湿度", "湿度"}, 0, 100)
    preferred_weather = ("深圳国家基本气象站", "福田国家基本气象站", "竹子林", "福田")
    temperature = choose(temp_candidates, preferred_weather)
    humidity = choose(humidity_candidates, preferred_weather)

    print("[2/4] PM2.5 skipped: no verified current official real-time dataset ID", flush=True)
    pm_candidates = []
    pm25 = None

    print("[3/4] Reading Shenzhen Meteorological Bureau UV page...", flush=True)
    try:
        uv, uv_time, uv_debug = fetch_uv()
    except Exception as exc:
        uv, uv_time, uv_debug = None, None, {"error": str(exc)}

    missing = [name for name, item in (("temperature", temperature), ("humidity", humidity)) if item is None]
    report = {
        "temperatureCandidates": len(temp_candidates),
        "humidityCandidates": len(humidity_candidates),
        "pm25Candidates": len(pm_candidates),
        "selected": {"temperature": temperature, "humidity": humidity, "pm25": pm25},
        "uv": uv_debug,
        "sources": {
            "weatherDataset": WEATHER_DATASET,
            "pm25Dataset": None,
            "pm25Status": "No verified current official Shenzhen real-time PM2.5 dataset ID",
            "uvUrl": UV_URL,
        },
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if missing:
        print("ERROR: official API returned no valid " + ", ".join(missing) + "; output not replaced", file=sys.stderr)
        return 3

    source_times = [str(x.get("time", "")) for x in (temperature, humidity) if x and x.get("time")]
    payload = {
        "temperature": clean(temperature["value"]),
        "humidity": clean(humidity["value"]),
        "uv": clean(uv),
        "pm25": None,
        "station": {
            "weather": temperature.get("station") or humidity.get("station") or "Shenzhen",
            "pm25": None,
        },
        "sourceUpdatedAt": max(source_times) if source_times else uv_time,
        "publishedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source": "Shenzhen Meteorological Bureau and Shenzhen Open Data Platform",
        "sources": {
            "weatherDataset": WEATHER_DATASET,
            "pm25Dataset": None,
            "pm25Status": "No verified current official Shenzhen real-time PM2.5 dataset ID",
            "uvUrl": UV_URL,
        },
        "status": "partial-pm25-unavailable" if uv is not None else "partial-uv-and-pm25-unavailable",
    }

    # Avoid a new commit when the official values and source timestamp did not change.
    if OUTPUT.exists():
        try:
            old = json.loads(OUTPUT.read_text(encoding="utf-8"))
            comparable = ("temperature", "humidity", "uv", "pm25", "station", "sourceUpdatedAt", "status")
            if all(old.get(key) == payload.get(key) for key in comparable):
                print("[4/4] NO_CHANGE: official values are unchanged", flush=True)
                return 0
        except Exception:
            pass

    temp_path = OUTPUT.with_suffix(".json.tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp_path.replace(OUTPUT)
    print(
        "[4/4] SUCCESS: temp={temperature}C humidity={humidity}% uv={uv} pm25=unavailable".format(**payload),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
