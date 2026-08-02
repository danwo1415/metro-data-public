#!/usr/bin/env python3
"""Publish Shenzhen weather, UV and official CNEMC PM2.5 for the app.

Temperature/humidity: Shenzhen Open Data automatic-station dataset (appKey).
UV: Shenzhen Meteorological Bureau public health-weather page.
PM2.5: China National Environmental Monitoring Centre's public real-time
platform. PM2.5 failure never blocks weather publication; the last valid
official PM2.5 is preserved when the platform is temporarily unavailable.
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
from urllib.parse import urljoin, urlparse, urlencode, parse_qsl, urlunparse

import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "shenzhen-environment.json"
REPORT = ROOT / "shenzhen-environment-report.json"
API_BASE = "https://opendata.sz.gov.cn/api/{dataset}/1/service.xhtml"
WEATHER_DATASET = "29200_00903509"
UV_URL = "https://weather.sz.gov.cn/qixiangfuwu/zhuanxiangfuwu/jiankangqixiangfuwu/index.html"
CNEMC_ROOTS = ["https://air.cnemc.cn:18007/", "http://air.cnemc.cn:18007/"]
CNEMC_KNOWN = [
    "https://air.cnemc.cn:18007/HourDataPublish.ashx?city=深圳市",
    "https://air.cnemc.cn:18007/CityDataPublishLive.ashx?city=深圳市",
    "https://air.cnemc.cn:18007/CityDataPublishLive.ashx",
    "https://air.cnemc.cn:18007/Ajax/CityDataPublishLive.ashx?city=深圳市",
    "http://air.cnemc.cn:18007/HourDataPublish.ashx?city=深圳市",
    "http://air.cnemc.cn:18007/CityDataPublishLive.ashx?city=深圳市",
]
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MetroDataUpdater/2.0; +https://github.com/danwo1415/metro-data-public)",
    "Accept": "application/json,text/html,application/xhtml+xml,*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7",
    "Referer": "https://air.cnemc.cn:18007/",
}


def norm_key(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", str(value or "").lower())


def number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    m = re.search(r"-?\d+(?:\.\d+)?", str(value).replace(",", ""))
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
    for key, value in record.items():
        if norm_key(key) in keys and value not in (None, ""):
            return str(value).strip()
    return ""


def fetch_dataset(dataset: str, app_key: str) -> Any:
    r = requests.get(
        API_BASE.format(dataset=dataset),
        params={"appKey": app_key, "page": 1, "rows": 5000},
        headers=HEADERS,
        timeout=45,
    )
    r.raise_for_status()
    try:
        payload = r.json()
    except Exception as exc:
        raise RuntimeError(f"Shenzhen Open Data returned non-JSON content: {r.text[:200]!r}") from exc
    text = json.dumps(payload, ensure_ascii=False)[:2000].lower()
    if any(token in text for token in ("invalid appkey", "appkey错误", "appkey无效", "无访问权限", "未订阅", "未授权", "请先订阅", "没有权限")):
        raise RuntimeError(f"Shenzhen Open Data rejected dataset {dataset}; verify the appKey/subscription")
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return payload
    summary = list(payload.keys())[:20] if isinstance(payload, dict) else type(payload).__name__
    raise RuntimeError(f"Unexpected Shenzhen Open Data response for {dataset}: {summary}")


STATION_KEYS = {"station", "stationname", "站名", "站点名称", "监测站点", "自动站名称", "测站名称", "area", "areaname", "city", "cityname", "城市"}
TIME_KEYS = {"time", "datetime", "datatime", "obstime", "updatetime", "crttime", "ddatetime", "forecasttime", "发布时间", "更新时间", "监测时间", "观测时间", "数据时间", "timepoint"}


def metric_candidates(payload: Any, aliases: set[str], low: float, high: float) -> list[dict[str, Any]]:
    aliases = {norm_key(x) for x in aliases}
    out: list[dict[str, Any]] = []
    for record in walk_dicts(payload):
        station = first_text(record, STATION_KEYS)
        observed = first_text(record, TIME_KEYS)
        for key, raw in record.items():
            nk = norm_key(key)
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
    def p(item: dict[str, Any]) -> tuple[int, str]:
        station = norm_key(item.get("station", ""))
        rank = len(preferred_norm)
        for i, name in enumerate(preferred_norm):
            if name and name in station:
                rank = i
                break
        return rank, str(item.get("time", ""))
    rank = min(p(x)[0] for x in candidates)
    pool = [x for x in candidates if p(x)[0] == rank]
    dated = [x for x in pool if x.get("time")]
    if dated:
        return max(dated, key=lambda x: str(x.get("time", "")))
    item = dict(pool[0])
    item["value"] = float(statistics.median([x["value"] for x in pool]))
    item["station"] = item.get("station") or "Shenzhen citywide median"
    return item


def fetch_uv() -> tuple[float | None, str | None, dict[str, Any]]:
    """Read only an explicitly published current UV value.

    The official page also contains explanatory tables with values such as
    0-2, 3-5 and 6-7. Those ranges must never be mistaken for the live value.
    If the live widget remains JavaScript-only (for example, ``loading`` in
    the raw HTML), return None and preserve the previous valid value.
    """
    r = requests.get(UV_URL, headers=HEADERS, timeout=45)
    r.raise_for_status()
    html = r.text
    soup = BeautifulSoup(html, "lxml")
    matches: list[dict[str, Any]] = []

    # First accept explicit machine-readable current-value fields only.
    explicit_patterns = [
        r"(?:currentUv|currentUV|uvIndex|uv_index|uvi|uvValue)[\"']?\s*[:=]\s*[\"']?(\d+(?:\.\d+)?)",
        r"data-(?:uv|uvi|uv-index|uv-value)=[\"'](\d+(?:\.\d+)?)[\"']",
    ]
    for pattern in explicit_patterns:
        for match in re.finditer(pattern, html, re.I):
            value = float(match.group(1))
            if 0 <= value <= 20:
                matches.append({"value": value, "method": "explicit-field", "context": html[max(0, match.start()-120):match.end()+120]})

    # Then inspect only the content between the live heading and the
    # explanatory heading. A single standalone numeric value is acceptable;
    # dates/times, level labels and range-table numbers are excluded.
    live_heading = soup.find(string=re.compile(r"今日紫外线实况"))
    live_text = ""
    if live_heading:
        node = live_heading.parent
        chunks: list[str] = []
        for sibling in node.next_siblings:
            text = sibling.get_text(" ", strip=True) if hasattr(sibling, "get_text") else str(sibling).strip()
            if re.search(r"紫外线指数说明", text):
                break
            if text:
                chunks.append(text)
            if len(" ".join(chunks)) > 700:
                break
        live_text = re.sub(r"\s+", " ", " ".join(chunks)).strip()
        if live_text and "loading" not in live_text.lower():
            cleaned = re.sub(r"实况时间[：:]?\s*[0-9年月日时分:\-\s]+", " ", live_text)
            cleaned = re.sub(r"(?:弱|中|强|很强|极强)\s*[（(]?\d+级[）)]?", " ", cleaned)
            nums = [float(x) for x in re.findall(r"(?<![\d.])(\d+(?:\.\d+)?)(?![\d.])", cleaned)]
            nums = [x for x in nums if 0 <= x <= 20]
            if len(nums) == 1:
                matches.append({"value": nums[0], "method": "live-block", "context": live_text[:500]})

    tm = re.search(r"实况时间[^0-9]{0,20}([0-9年月日时分:\-\s]+)", html)
    observed = tm.group(1).strip() if tm else None
    value = matches[0]["value"] if matches else None
    return value, observed, {"matches": matches[:20], "liveBlock": live_text[:700]}


def city_is_shenzhen(value: str) -> bool:
    n = norm_key(value)
    return n in {"深圳", "深圳市", "shenzhen"} or "深圳" in n


def extract_pm_json(payload: Any, city_optional: bool = False) -> list[dict[str, Any]]:
    aliases = {"pm25", "pm2_5", "pm2.5", "pm2_5_24h", "pm2524h", "细颗粒物", "细颗粒物pm25"}
    aliases_n = {norm_key(x) for x in aliases}
    out: list[dict[str, Any]] = []
    for record in walk_dicts(payload):
        city = first_text(record, STATION_KEYS)
        if city and not city_is_shenzhen(city):
            continue
        if not city and not city_optional:
            continue
        observed = first_text(record, TIME_KEYS)
        for key, raw in record.items():
            nk = norm_key(key)
            if nk not in aliases_n and not any(len(a) >= 4 and a in nk for a in aliases_n):
                continue
            value = number(raw)
            if value is not None and 0 <= value <= 1000:
                out.append({"value": value, "station": city or "深圳市", "time": observed, "field": str(key)})
    return out


def extract_pm_html(text: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    soup = BeautifulSoup(text, "lxml")
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        headers = [norm_key(x.get_text(" ", strip=True)) for x in rows[0].find_all(["th", "td"])]
        city_col = next((i for i, h in enumerate(headers) if h in {"城市", "city", "cityname", "area", "areaname"}), None)
        pm_col = next((i for i, h in enumerate(headers) if h in {"pm25", "pm2524h", "细颗粒物pm25", "细颗粒物"}), None)
        time_col = next((i for i, h in enumerate(headers) if "时间" in h or h in {"time", "timepoint", "updatetime"}), None)
        if pm_col is None:
            continue
        for row in rows[1:]:
            cells = [x.get_text(" ", strip=True) for x in row.find_all(["th", "td"])]
            if pm_col >= len(cells):
                continue
            city = cells[city_col] if city_col is not None and city_col < len(cells) else ""
            if city and not city_is_shenzhen(city):
                continue
            if not city and "深圳" not in row.get_text(" ", strip=True):
                continue
            value = number(cells[pm_col])
            if value is not None and 0 <= value <= 1000:
                out.append({"value": value, "station": city or "深圳市", "time": cells[time_col] if time_col is not None and time_col < len(cells) else "", "field": headers[pm_col]})
    # JSON/JavaScript text fallback around the Shenzhen token.
    for m in re.finditer(r"深圳市?[\s\S]{0,500}?(?:PM2[._]?5|pm2[._]?5|细颗粒物)[^0-9\-]{0,40}(\d+(?:\.\d+)?)", text, re.I):
        value = float(m.group(1))
        if 0 <= value <= 1000:
            out.append({"value": value, "station": "深圳市", "time": "", "field": "text-regex"})
    return out


def add_city_query(url: str, key: str) -> str:
    p = urlparse(url)
    q = dict(parse_qsl(p.query, keep_blank_values=True))
    q.setdefault(key, "深圳市")
    return urlunparse((p.scheme, p.netloc, p.path, p.params, urlencode(q), p.fragment))


def discover_cnemc_endpoints(root_html: str, root_url: str, session: requests.Session) -> list[str]:
    soup = BeautifulSoup(root_html, "lxml")
    texts = [root_html]
    for tag in soup.find_all("script", src=True)[:15]:
        url = urljoin(root_url, tag["src"])
        if urlparse(url).hostname != "air.cnemc.cn":
            continue
        try:
            r = session.get(url, headers=HEADERS, timeout=20, verify=False)
            if r.ok and len(r.text) < 5_000_000:
                texts.append(r.text)
        except Exception:
            pass
    endpoints: list[str] = []
    pattern = re.compile(r"[\"']([^\"']*(?:\.ashx|/api/[^\"']+|\.json)(?:\?[^\"']*)?)[\"']", re.I)
    for text in texts:
        for match in pattern.finditer(text):
            url = urljoin(root_url, match.group(1).replace("\\/", "/"))
            if urlparse(url).hostname == "air.cnemc.cn":
                endpoints.append(url)
    return list(dict.fromkeys(endpoints))[:40]


def fetch_cnemc_pm25() -> tuple[dict[str, Any] | None, dict[str, Any]]:
    session = requests.Session()
    candidates = list(CNEMC_KNOWN)
    debug: dict[str, Any] = {"attempts": []}
    for root in CNEMC_ROOTS:
        try:
            r = session.get(root, headers=HEADERS, timeout=25, verify=False)
            debug["attempts"].append({"url": root, "status": r.status_code, "bytes": len(r.content)})
            if r.ok:
                candidates.extend(discover_cnemc_endpoints(r.text, root, session))
        except Exception as exc:
            debug["attempts"].append({"url": root, "error": str(exc)})
    expanded: list[str] = []
    for url in list(dict.fromkeys(candidates)):
        expanded.append(url)
        if not urlparse(url).query and re.search(r"city|hour|publish|live", url, re.I):
            expanded.extend(add_city_query(url, k) for k in ("city", "cityName", "area"))
    records: list[dict[str, Any]] = []
    for url in list(dict.fromkeys(expanded))[:80]:
        try:
            r = session.get(url, headers=HEADERS, timeout=25, verify=False)
            item = {"url": url, "status": r.status_code, "bytes": len(r.content)}
            if not r.ok:
                debug["attempts"].append(item)
                continue
            city_optional = any(x in url for x in ("%E6%B7%B1%E5%9C%B3", "深圳"))
            found: list[dict[str, Any]] = []
            try:
                found.extend(extract_pm_json(r.json(), city_optional=city_optional))
            except Exception:
                pass
            found.extend(extract_pm_html(r.text))
            item["records"] = len(found)
            debug["attempts"].append(item)
            for rec in found:
                rec["sourceUrl"] = url
            records.extend(found)
        except Exception as exc:
            debug["attempts"].append({"url": url, "error": str(exc)})
    if not records:
        return None, debug
    dated = [x for x in records if x.get("time")]
    selected = max(dated, key=lambda x: str(x.get("time", ""))) if dated else records[0]
    debug["selected"] = selected
    debug["recordCount"] = len(records)
    return selected, debug


def clean(value: float | None) -> float | int | None:
    if value is None:
        return None
    return int(value) if float(value).is_integer() else round(float(value), 1)


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

    print("[1/4] Fetching Shenzhen official weather observations...", flush=True)
    weather = fetch_dataset(WEATHER_DATASET, app_key)
    temp_candidates = metric_candidates(weather, {"T", "temperature", "airtemperature", "temp", "气温", "温度"}, -30, 60)
    humidity_candidates = metric_candidates(weather, {"RHSFC", "relativehumidity", "humidity", "rh", "相对湿度", "湿度"}, 0, 100)
    preferred = ("深圳国家基本气象站", "福田国家基本气象站", "竹子林", "福田")
    temperature = choose(temp_candidates, preferred)
    humidity = choose(humidity_candidates, preferred)
    if not temperature or not humidity:
        REPORT.write_text(json.dumps({"temperatureCandidates": len(temp_candidates), "humidityCandidates": len(humidity_candidates)}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("ERROR: official weather API returned no valid temperature/humidity", file=sys.stderr)
        return 3

    print("[2/4] Reading China National Environmental Monitoring Centre PM2.5...", flush=True)
    pm25, pm_debug = fetch_cnemc_pm25()
    if not pm25 and number(old.get("pm25")) is not None:
        pm25 = {
            "value": number(old.get("pm25")),
            "station": (old.get("station") or {}).get("pm25") or "深圳市",
            "time": old.get("pm25SourceUpdatedAt") or old.get("sourceUpdatedAt") or "",
            "sourceUrl": old.get("pm25SourceUrl") or "",
            "preserved": True,
        }

    print("[3/4] Reading Shenzhen Meteorological Bureau UV page...", flush=True)
    try:
        uv, uv_time, uv_debug = fetch_uv()
    except Exception as exc:
        uv, uv_time, uv_debug = None, None, {"error": str(exc)}
        if number(old.get("uv")) is not None:
            uv = number(old.get("uv"))

    source_times = [str(x.get("time", "")) for x in (temperature, humidity) if x.get("time")]
    payload = {
        "temperature": clean(temperature["value"]),
        "humidity": clean(humidity["value"]),
        "uv": clean(uv),
        "pm25": clean(pm25["value"]) if pm25 else None,
        "station": {
            "weather": temperature.get("station") or humidity.get("station") or "Shenzhen",
            "pm25": pm25.get("station") if pm25 else None,
        },
        "sourceUpdatedAt": max(source_times) if source_times else uv_time,
        "pm25SourceUpdatedAt": pm25.get("time") if pm25 else None,
        "pm25SourceUrl": pm25.get("sourceUrl") if pm25 else None,
        "publishedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source": "Shenzhen Meteorological Bureau, Shenzhen Open Data Platform and China National Environmental Monitoring Centre",
        "sources": {
            "weatherDataset": WEATHER_DATASET,
            "uvUrl": UV_URL,
            "pm25Platform": "https://air.cnemc.cn:18007/",
        },
        "status": "ok" if uv is not None and pm25 and not pm25.get("preserved") else ("partial-pm25-preserved" if pm25 else "partial-pm25-unavailable"),
    }
    report = {
        "temperatureCandidates": len(temp_candidates),
        "humidityCandidates": len(humidity_candidates),
        "selected": {"temperature": temperature, "humidity": humidity, "pm25": pm25},
        "uv": uv_debug,
        "cnemc": pm_debug,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    comparable = ("temperature", "humidity", "uv", "pm25", "station", "sourceUpdatedAt", "pm25SourceUpdatedAt", "status")
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
