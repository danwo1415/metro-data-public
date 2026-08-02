#!/usr/bin/env python3
"""Publish Shenzhen temperature, humidity, UV and PM2.5 for the Metro app.

Primary sources are Shenzhen Government Open Data APIs. Temperature/humidity
are mandatory. UV and PM2.5 are optional: an unavailable or unsubscribed
optional dataset never blocks the valid weather update, and the last valid
published optional value is preserved.
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
WEATHER_DATASET = "29200_00903509"
PM25_DATASETS = ("29200_01000344", "29200_00900269")
UV_DATASETS = ("29200_03001143",)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MetroDataUpdater/4.0; +https://github.com/danwo1415/metro-data-public)",
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7",
}
PERMISSION_TOKENS = (
    "invalid appkey", "appkey错误", "appkey无效", "无访问权限", "未订阅", "未授权",
    "请先订阅", "没有权限", "无权访问", "应用未授权",
)
STATION_KEYS = {
    "station", "stationname", "site", "sitename", "pointname", "monitorname",
    "站名", "站点", "站点名称", "监测站点", "监测点名称", "自动站名称", "测站名称",
    "area", "areaname", "city", "cityname", "城市", "区域",
}
TIME_KEYS = {
    "time", "datetime", "datatime", "obstime", "updatetime", "crttime", "ddatetime",
    "forecasttime", "publishtime", "monitoringtime", "timepoint", "发布时间", "更新时间",
    "监测时间", "观测时间", "数据时间", "预报时间",
}
VALUE_KEYS = {
    "value", "val", "reading", "concentration", "avg", "average", "浓度", "监测值",
    "数值", "值", "小时均值", "实时值", "指数值",
}
POLLUTANT_KEYS = {"pollutant", "pollutantname", "factor", "factorname", "item", "name", "污染物", "因子", "指标", "项目"}


def norm_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", str(value or "").lower())


def number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    # Do not turn explanatory ranges such as 3-5 into a live value.
    if re.search(r"\d\s*(?:-|~|—|–|至)\s*\d", text):
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(m.group()) if m else None


def walk_dicts(node: Any) -> Iterable[dict[str, Any]]:
    if isinstance(node, dict):
        yield node
        for child in node.values():
            yield from walk_dicts(child)
    elif isinstance(node, list):
        for child in node:
            yield from walk_dicts(child)


def first_text(record: dict[str, Any], keys: set[str]) -> str:
    normalized = {norm_key(x) for x in keys}
    for key, value in record.items():
        if norm_key(key) in normalized and value not in (None, ""):
            return str(value).strip()
    return ""


def fetch_dataset(dataset: str, app_key: str, rows: int = 5000) -> Any:
    response = requests.get(
        API_BASE.format(dataset=dataset),
        params={"appKey": app_key, "page": 1, "rows": rows},
        headers=HEADERS,
        timeout=45,
    )
    response.raise_for_status()
    try:
        payload = response.json()
    except Exception as exc:
        raise RuntimeError(f"dataset {dataset} returned non-JSON content: {response.text[:180]!r}") from exc
    preview = json.dumps(payload, ensure_ascii=False)[:4000].lower()
    if any(token in preview for token in PERMISSION_TOKENS):
        raise PermissionError(f"dataset {dataset} is not subscribed/authorized for this appKey")
    # Some platform errors arrive with HTTP 200.
    if isinstance(payload, dict):
        code = str(payload.get("code", payload.get("status", ""))).lower()
        msg = str(payload.get("message", payload.get("msg", ""))).strip()
        if code in {"401", "403", "-1", "false"}:
            raise RuntimeError(f"dataset {dataset} rejected request: {msg or code}")
    return payload


def optional_dataset(dataset: str, app_key: str, report: dict[str, Any]) -> Any | None:
    try:
        payload = fetch_dataset(dataset, app_key)
        report.setdefault("datasetAttempts", []).append({"dataset": dataset, "status": "ok"})
        return payload
    except PermissionError as exc:
        report.setdefault("datasetAttempts", []).append({"dataset": dataset, "status": "subscription-required", "error": str(exc)})
    except Exception as exc:  # noqa: BLE001
        report.setdefault("datasetAttempts", []).append({"dataset": dataset, "status": "failed", "error": str(exc)})
    return None


def alias_match(key: str, aliases: set[str]) -> bool:
    nk = norm_key(key)
    for alias in {norm_key(x) for x in aliases}:
        if nk == alias or (len(alias) >= 3 and alias in nk):
            return True
    return False


def metric_candidates(payload: Any, aliases: set[str], low: float, high: float) -> list[dict[str, Any]]:
    """Extract both wide records (PM2.5 is a column) and long records
    (pollutant='PM2.5', value=...).
    """
    out: list[dict[str, Any]] = []
    value_keys_n = {norm_key(x) for x in VALUE_KEYS}
    pollutant_keys_n = {norm_key(x) for x in POLLUTANT_KEYS}
    for record in walk_dicts(payload):
        station = first_text(record, STATION_KEYS)
        observed = first_text(record, TIME_KEYS)
        for key, raw in record.items():
            if not alias_match(str(key), aliases):
                continue
            value = number(raw)
            if value is not None and low <= value <= high:
                out.append({"value": value, "station": station, "time": observed, "field": str(key)})
        pollutant = ""
        for key, raw in record.items():
            if norm_key(key) in pollutant_keys_n and raw not in (None, ""):
                pollutant = str(raw)
                break
        if pollutant and any(alias_match(pollutant, {a}) for a in aliases):
            for key, raw in record.items():
                if norm_key(key) not in value_keys_n:
                    continue
                value = number(raw)
                if value is not None and low <= value <= high:
                    out.append({"value": value, "station": station, "time": observed, "field": f"{pollutant}/{key}"})
    # Remove exact duplicates caused by nested response wrappers.
    unique: dict[tuple[Any, ...], dict[str, Any]] = {}
    for item in out:
        unique[(item["value"], item.get("station", ""), item.get("time", ""), item.get("field", ""))] = item
    return list(unique.values())


def choose_preferred(candidates: list[dict[str, Any]], preferred: tuple[str, ...]) -> dict[str, Any] | None:
    if not candidates:
        return None
    prefs = tuple(norm_key(x) for x in preferred)
    def rank(item: dict[str, Any]) -> tuple[int, str]:
        station = norm_key(item.get("station", ""))
        r = len(prefs)
        for i, name in enumerate(prefs):
            if name and name in station:
                r = i
                break
        return r, str(item.get("time", ""))
    best_rank = min(rank(x)[0] for x in candidates)
    pool = [x for x in candidates if rank(x)[0] == best_rank]
    dated = [x for x in pool if x.get("time")]
    if dated:
        return max(dated, key=lambda x: str(x.get("time", "")))
    selected = dict(pool[0])
    selected["value"] = float(statistics.median(x["value"] for x in pool))
    selected["station"] = selected.get("station") or "深圳市"
    return selected


def choose_pm25(candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not candidates:
        return None
    # Use the latest published hour when timestamps are available.
    times = [str(x.get("time", "")) for x in candidates if x.get("time")]
    pool = candidates
    if times:
        latest = max(times)
        pool = [x for x in candidates if str(x.get("time", "")) == latest]
    # Prefer an explicit city-wide record. Otherwise publish the median of the
    # latest monitoring-station values, which is more robust than selecting an
    # arbitrary station.
    citywide = [x for x in pool if norm_key(x.get("station", "")) in {"深圳", "深圳市", "shenzhen"}]
    if citywide:
        return dict(citywide[0])
    selected = dict(pool[0])
    selected["value"] = float(statistics.median(x["value"] for x in pool))
    selected["station"] = "深圳市监测站中位数"
    selected["field"] = "median/latest-monitoring-hour"
    return selected


def clean(value: float | None) -> float | int | None:
    if value is None:
        return None
    return int(value) if float(value).is_integer() else round(float(value), 1)


def old_optional(old: dict[str, Any], key: str) -> dict[str, Any] | None:
    value = number(old.get(key))
    if value is None:
        return None
    stations = old.get("station") if isinstance(old.get("station"), dict) else {}
    return {
        "value": value,
        "station": stations.get(key) or stations.get("weather") or "深圳市",
        "time": old.get(f"{key}SourceUpdatedAt") or old.get("sourceUpdatedAt") or "",
        "field": "preserved-previous-value",
        "preserved": True,
    }


def main() -> int:
    app_key = os.environ.get("SZ_OPEN_DATA_APP_KEY", "").strip()
    if not app_key:
        print("ERROR: missing SZ_OPEN_DATA_APP_KEY; no files changed", file=sys.stderr)
        return 2
    old: dict[str, Any] = {}
    if OUTPUT.exists():
        try:
            old = json.loads(OUTPUT.read_text(encoding="utf-8"))
        except Exception:
            old = {}
    report: dict[str, Any] = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "officialDatasets": {"weather": WEATHER_DATASET, "pm25": list(PM25_DATASETS), "uvForecast": list(UV_DATASETS)},
    }

    print("[1/4] Fetching Shenzhen official temperature and humidity...", flush=True)
    try:
        weather = fetch_dataset(WEATHER_DATASET, app_key)
    except Exception as exc:  # noqa: BLE001
        report["fatalError"] = str(exc)
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"ERROR: official weather dataset failed: {exc}", file=sys.stderr)
        return 3
    temperature_candidates = metric_candidates(weather, {"T", "temperature", "airtemperature", "temp", "气温", "温度"}, -30, 60)
    humidity_candidates = metric_candidates(weather, {"RHSFC", "relativehumidity", "humidity", "rh", "相对湿度", "湿度"}, 0, 100)
    preferred = ("深圳国家基本气象站", "福田国家基本气象站", "竹子林", "福田")
    temperature = choose_preferred(temperature_candidates, preferred)
    humidity = choose_preferred(humidity_candidates, preferred)
    report["weatherCandidateCounts"] = {"temperature": len(temperature_candidates), "humidity": len(humidity_candidates)}
    if not temperature or not humidity:
        report["fatalError"] = "No valid temperature/humidity candidates"
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("ERROR: official weather API returned no valid temperature/humidity", file=sys.stderr)
        return 4

    print("[2/4] Fetching official Shenzhen PM2.5 dataset...", flush=True)
    pm25 = None
    pm_dataset = None
    pm_count = 0
    for dataset in PM25_DATASETS:
        payload = optional_dataset(dataset, app_key, report)
        if payload is None:
            continue
        candidates = metric_candidates(payload, {"PM2.5", "PM25", "PM2_5", "细颗粒物", "细颗粒物浓度"}, 0, 1000)
        pm_count += len(candidates)
        selected = choose_pm25(candidates)
        if selected:
            pm25, pm_dataset = selected, dataset
            break
    if not pm25:
        pm25 = old_optional(old, "pm25")

    print("[3/4] Fetching official Shenzhen UV-index forecast dataset...", flush=True)
    uv = None
    uv_dataset = None
    uv_count = 0
    for dataset in UV_DATASETS:
        payload = optional_dataset(dataset, app_key, report)
        if payload is None:
            continue
        candidates = metric_candidates(payload, {"UV", "UVI", "UVIndex", "UV指数", "紫外线指数", "指数值"}, 0, 20)
        uv_count += len(candidates)
        selected = choose_preferred(candidates, ("深圳", "全市"))
        if selected:
            uv, uv_dataset = selected, dataset
            break
    if not uv:
        uv = old_optional(old, "uv") or old_optional(old, "uvIndex")

    now = datetime.now(timezone.utc).replace(microsecond=0)
    source_times = [str(x.get("time", "")) for x in (temperature, humidity) if x.get("time")]
    optional_live = sum(bool(x and not x.get("preserved")) for x in (uv, pm25))
    payload = {
        "temperature": clean(temperature["value"]),
        "humidity": clean(humidity["value"]),
        "uv": clean(uv["value"]) if uv else None,
        "uvIndex": clean(uv["value"]) if uv else None,
        "pm25": clean(pm25["value"]) if pm25 else None,
        "station": {
            "weather": temperature.get("station") or humidity.get("station") or "深圳市",
            "uv": uv.get("station") if uv else None,
            "pm25": pm25.get("station") if pm25 else None,
        },
        "sourceUpdatedAt": max(source_times) if source_times else None,
        "uvSourceUpdatedAt": uv.get("time") if uv else None,
        "pm25SourceUpdatedAt": pm25.get("time") if pm25 else None,
        "publishedAt": now.isoformat(),
        "source": "深圳市政府数据开放平台／深圳市气象局",
        "sources": {
            "weatherDataset": WEATHER_DATASET,
            "uvDataset": uv_dataset,
            "pm25Dataset": pm_dataset,
        },
        "status": "ok" if optional_live == 2 else ("partial-preserved" if uv or pm25 else "partial-optional-unavailable"),
    }
    report.update({
        "candidateCounts": {"pm25": pm_count, "uv": uv_count},
        "selected": {"temperature": temperature, "humidity": humidity, "pm25": pm25, "uv": uv},
        "publishedStatus": payload["status"],
    })
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    comparable = ("temperature", "humidity", "uv", "uvIndex", "pm25", "station", "sourceUpdatedAt", "uvSourceUpdatedAt", "pm25SourceUpdatedAt", "status")
    if old and all(old.get(k) == payload.get(k) for k in comparable):
        print("[4/4] NO_CHANGE: official values are unchanged", flush=True)
        return 0
    tmp = OUTPUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(OUTPUT)
    print(f"[4/4] SUCCESS: temp={payload['temperature']}C humidity={payload['humidity']}% uv={payload['uv']} pm25={payload['pm25']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
