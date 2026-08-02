#!/usr/bin/env python3
"""Fetch Shenzhen Metro first/last train times from official web pages.

No private API key is required. The script reads the public Shenzhen Metro / MTR
Shenzhen timetable pages, validates the result, then updates shenzhen-data.json
and shenzhen-version.json atomically.
"""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

DATA_FILE = Path("shenzhen-data.json")
VERSION_FILE = Path("shenzhen-version.json")
REPORT_FILE = Path("shenzhen-service-hours-report.json")
TZ = dt.timezone(dt.timedelta(hours=8))
UA = "Mozilla/5.0 (compatible; MetroRoutePlanner/1.0; +https://github.com/danwo1415/metro-data-public)"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"})

# Shenzhen Metro official English timetable roots. Each root normally links to
# working-day, day-off and holiday tables.
LINE_ROOTS: dict[str, list[str]] = {
    "SZ1": ["https://www.szmc.net/szmc_en/Time_Table/line1/"],
    "SZ28": [
        "https://www.szmc.net/szmc_en/Time_Table/line2/",
        "https://www.szmc.net/szmc_en/Time_Table/line8/",
    ],
    "SZ3": ["https://www.szmc.net/szmc_en/Time_Table/line3/"],
    "SZ4": ["https://www.szmc.net/szmc_en/Time_Table/line4/"],
    "SZ5": ["https://www.szmc.net/szmc_en/Time_Table/line5/"],
    "SZ6": ["https://www.szmc.net/szmc_en/Time_Table/line6/"],
    "SZ6B": ["https://www.szmc.net/szmc_en/Time_Table/line6z/"],
    "SZ7": ["https://www.szmc.net/szmc_en/Time_Table/line7/"],
    "SZ9": ["https://www.szmc.net/szmc_en/Time_Table/line9/"],
    "SZ10": ["https://www.szmc.net/szmc_en/Time_Table/line10/"],
    "SZ11": ["https://www.szmc.net/szmc_en/Time_Table/Line11/"],
    "SZ12": ["https://www.szmc.net/szmc_en/Time_Table/Line12/"],
    "SZ14": ["https://www.szmc.net/szmc_en/Time_Table/Line14/"],
    "SZ16": ["https://www.szmc.net/szmc_en/Time_Table/Line16/"],
    "SZ20": ["https://www.szmc.net/szmc_en/Time_Table/Line20/"],
    # Line 13 is operated by MTR Shenzhen. These public pages are attempted;
    # if their content is image/JS-only, the report marks the line unresolved.
    "SZ13": [
        "https://www.mtrsz.com.cn/frontend/default/src/channel/operation_timetable_13line.html",
        "https://www.mtrsz.com.cn/frontend/default/src/channel/operation_timetable_13Line.html",
    ],
}

# Stable official article URLs used only when a line directory does not expose
# its current timetable links. They provide enough bootstrap coverage for the
# first successful data publication; station pages below then fill weak lines.
DIRECT_WORKDAY_HINTS: dict[str, list[str]] = {
    "SZ1": ["https://www.szmc.net/szmc_en/Time_Table/line1/202004/79726.html"],
    "SZ28": ["https://www.szmc.net/szmc_enm/Time_Table/Line2/202003/85128.html"],
    "SZ3": ["https://www.szmc.net/szmc_enm/Time_Table/Line3/202003/85129.html"],
    "SZ11": ["https://www.szmc.net/szmc_en/Time_Table/Line11/202003/75598.html"],
}

# Official 2026 holiday calendar. Holiday dates use the official holiday table;
# adjusted working weekends use the working-day table.
HOLIDAYS_2026 = {
    *(dt.date(2026, 1, 1) + dt.timedelta(days=i) for i in range(3)),
    *(dt.date(2026, 2, 15) + dt.timedelta(days=i) for i in range(9)),
    *(dt.date(2026, 4, 4) + dt.timedelta(days=i) for i in range(3)),
    *(dt.date(2026, 5, 1) + dt.timedelta(days=i) for i in range(5)),
    *(dt.date(2026, 6, 19) + dt.timedelta(days=i) for i in range(3)),
    *(dt.date(2026, 9, 25) + dt.timedelta(days=i) for i in range(3)),
    *(dt.date(2026, 10, 1) + dt.timedelta(days=i) for i in range(7)),
}
WORKDAYS_2026 = {
    dt.date(2026, 1, 4), dt.date(2026, 2, 14), dt.date(2026, 2, 28),
    dt.date(2026, 5, 9), dt.date(2026, 9, 20), dt.date(2026, 10, 10),
}

ALIASES = {
    "oct": "華僑城",
    "baoanstadium": "寶體",
    "hitechpark": "高新園",
    "shenzhenuniversity": "深大",
    "conventionexhibitioncenter": "會展中心",
    "shoppingpark": "購物公園",
    "airporteast": "機場東",
    "sciencemuseum": "科學館",
    "grandtheater": "大劇院",
    "grandtheatre": "大劇院",
    "qiaocheng east": "僑城東",
    "liantangcheckpoint": "蓮塘口岸",
    "xianhurd": "仙湖路",
    "xianhuroad": "仙湖路",
    "qiaochengnorth": "僑城北",
    "antuohill": "安托山",
    "xiangmeinorth": "香梅北",
    "lianhuawest": "蓮花西",
    "civiccenter": "市民中心",
    "civiccentre": "市民中心",
    "gangxianorth": "崗廈北",
    "huaqiangnorth": "華強北",
    "huaqiangsouth": "華強南",
    "hongshuwansouth": "紅樹灣南",
    "airportnorth": "機場北",
    "shenzhenworld": "國展",
    "shenzhenworldnorth": "國展北",
    "shenzhenworldsouth": "國展南",
    "conventionexhibitioncity": "會展城",
    "futiancheckpoint": "福田口岸",
    "shenzhennorthstation": "深圳北站",
    "pekinguniversity": "北大",
    "shenzhenuniversitylihucampus": "深大麗湖",
}


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "").lower()
    value = value.replace("&", "and").replace("centre", "center")
    value = re.sub(r"\bstation\b", "", value)
    return re.sub(r"[^a-z0-9\u3400-\u9fff]", "", value)


def parse_time(value: str) -> str | None:
    value = clean_text(value)
    if not value or value in {"--", "-", "/", "—", "－"}:
        return None
    m = re.search(r"(?<!\d)(\d{1,2})[:：](\d{2})(?::(\d{2}))?", value)
    if not m:
        return None
    h, minute = int(m.group(1)), int(m.group(2))
    if h > 29 or minute > 59:
        return None
    return f"{h % 24:02d}:{minute:02d}"


def get(url: str, timeout: int = 10, attempts: int = 1) -> str:
    last: Exception | None = None
    for attempt in range(max(1, attempts)):
        try:
            r = SESSION.get(url, timeout=timeout)
            r.raise_for_status()
            r.encoding = r.apparent_encoding or r.encoding
            return r.text
        except Exception as exc:  # noqa: BLE001
            last = exc
            if attempt + 1 < max(1, attempts):
                time.sleep(0.8 * (attempt + 1))
    raise RuntimeError(f"GET failed: {url}: {last}")


def expanded_rows(table: Any) -> list[list[str]]:
    rows: list[list[str]] = []
    for tr in table.find_all("tr"):
        row: list[str] = []
        for cell in tr.find_all(["th", "td"], recursive=False):
            text = clean_text(cell.get_text(" ", strip=True))
            try:
                span = max(1, int(cell.get("colspan", 1)))
            except Exception:
                span = 1
            row.extend([text] * span)
        if row:
            rows.append(row)
    return rows


def build_station_lookups(data: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    lookup: dict[str, str] = {}
    name_to_code: dict[str, str] = {}
    for line in data["L"].values():
        for code, trad in line["stations"]:
            simp = data.get("simplified", {}).get(code, trad)
            eng = data.get("english", {}).get(code, "")
            pinyin = data.get("roman", {}).get(trad) or data.get("roman", {}).get(simp) or ""
            for v in (trad, simp, eng, pinyin):
                if v:
                    lookup[norm(v)] = code
            name_to_code[trad] = code
            name_to_code[simp] = code
    for alias, chinese in ALIASES.items():
        code = name_to_code.get(chinese)
        if code:
            lookup[norm(alias)] = code
    return lookup, name_to_code


def map_name(value: str, lookup: dict[str, str]) -> str | None:
    v = clean_text(value)
    v = re.sub(r"^(to|往|开往)\s*", "", v, flags=re.I)
    v = re.sub(r"\s*(direction|方向)$", "", v, flags=re.I)
    key = norm(v)
    if key in lookup:
        return lookup[key]
    # Small semantic normalizations commonly used by the official English site.
    variants = {
        key.replace("road", "lu").replace("rd", "lu"),
        key.replace("north", "bei").replace("south", "nan").replace("east", "dong").replace("west", "xi"),
    }
    for variant in variants:
        if variant in lookup:
            return lookup[variant]
    return None


def align_station_rows(line_code: str, names: list[str], data: dict[str, Any], lookup: dict[str, str]) -> list[str | None]:
    internal = [x[0] for x in data["L"][line_code]["stations"]]
    direct = [map_name(x, lookup) for x in names]
    pos = {code: i for i, code in enumerate(internal)}
    anchors = [(i, pos[c]) for i, c in enumerate(direct) if c in pos]

    # Fill sequences around anchors when website rows are a contiguous line segment.
    if anchors:
        first_i, first_p = anchors[0]
        for i in range(first_i - 1, -1, -1):
            p = first_p - (first_i - i)
            if p >= 0 and direct[i] is None:
                direct[i] = internal[p]
        for (i1, p1), (i2, p2) in zip(anchors, anchors[1:]):
            if p2 - p1 == i2 - i1:
                for i in range(i1 + 1, i2):
                    if direct[i] is None:
                        direct[i] = internal[p1 + (i - i1)]
        last_i, last_p = anchors[-1]
        for i in range(last_i + 1, len(direct)):
            p = last_p + (i - last_i)
            if p < len(internal) and direct[i] is None:
                direct[i] = internal[p]
    elif len(names) == len(internal):
        direct = internal[:]
    return direct


def classify_schedule(text: str) -> str | None:
    t = clean_text(text).lower()
    if "working" in t or "工作日" in t:
        return "workday"
    if "days off" in t or "day off" in t or "休息日" in t or "周末" in t:
        return "dayoff"
    if "holiday" in t or "节假日" in t or "節假日" in t:
        return "holiday"
    return None


def discover_schedule_pages(root_url: str, html: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "lxml")
    found: dict[str, str] = {}
    for a in soup.find_all("a", href=True):
        typ = classify_schedule(a.get_text(" ", strip=True))
        if typ:
            found[typ] = urljoin(root_url, a["href"])
    # Some roots render a timetable directly but have incomplete links.
    if not found and ("First Train" in html or "首班车" in html):
        found["workday"] = root_url
    return found


def find_timetable_table(soup: BeautifulSoup) -> Any | None:
    best = None
    best_score = 0
    for table in soup.find_all("table"):
        text = clean_text(table.get_text(" ", strip=True)).lower()
        score = sum(x in text for x in ("first train", "last train", "首班车", "末班车"))
        score += min(4, len(table.find_all("tr")) // 5)
        if score > best_score:
            best_score, best = score, table
    return best if best_score >= 3 else None


def parse_english_table(html: str, line_code: str, data: dict[str, Any], lookup: dict[str, str], source: str) -> list[tuple[str, str, str, str, str]]:
    soup = BeautifulSoup(html, "lxml")
    table = find_timetable_table(soup)
    if table is None:
        return []
    rows = expanded_rows(table)
    header_idx = -1
    for i, row in enumerate(rows):
        joined = " ".join(row).lower()
        if "first train" in joined and "last train" in joined:
            header_idx = i
            break
    if header_idx < 0:
        return []
    terminal_row = rows[header_idx - 1] if header_idx else []
    # Data rows should contain at least two time-like cells.
    raw_rows: list[tuple[str, list[str]]] = []
    for row in rows[header_idx + 1:]:
        if len(row) < 3:
            continue
        times = [parse_time(x) for x in row[1:]]
        if sum(x is not None for x in times) >= 1:
            raw_rows.append((row[0], row))
    if not raw_rows:
        return []
    mapped = align_station_rows(line_code, [x[0] for x in raw_rows], data, lookup)

    # Determine terminal columns. Expanded colspan normally produces 5 columns.
    max_cols = max(len(x[1]) for x in raw_rows)
    direction_pairs: list[tuple[int, int, str | None]] = []
    for first_col in range(1, max_cols - 1, 2):
        last_col = first_col + 1
        label = terminal_row[first_col] if first_col < len(terminal_row) else ""
        terminal = map_name(label, lookup)
        direction_pairs.append((first_col, last_col, terminal))

    records: list[tuple[str, str, str, str, str]] = []
    for row_index, (_, row) in enumerate(raw_rows):
        station = mapped[row_index]
        if not station:
            continue
        for first_col, last_col, terminal in direction_pairs:
            first = parse_time(row[first_col]) if first_col < len(row) else None
            last = parse_time(row[last_col]) if last_col < len(row) else None
            if not first or not last:
                continue
            dest = terminal
            if not dest:
                # Infer destination from the end of this table segment.
                candidates = [c for c in mapped if c]
                if candidates:
                    dest = candidates[-1] if station != candidates[-1] else candidates[0]
            if dest and dest != station:
                records.append((station, line_code, dest, first, last))
    return records


def parse_chinese_station_page(html: str, data: dict[str, Any], lookup: dict[str, str], source: str, expected_station: str | None = None) -> list[tuple[str, str, str, str, str, str]]:
    soup = BeautifulSoup(html, "lxml")
    output: list[tuple[str, str, str, str, str, str]] = []
    for heading in soup.find_all(string=re.compile(r"运营时刻表|運營時刻表")):
        typ = classify_schedule(str(heading))
        if not typ:
            continue
        table = heading.parent.find_next("table") if heading.parent else None
        if table is None:
            continue
        rows = expanded_rows(table)
        for row in rows:
            if len(row) < 4:
                continue
            direction = map_name(row[0], lookup)
            first, last = parse_time(row[1]), parse_time(row[2])
            line_text = row[3]
            m = re.search(r"(\d+)\s*号线|6\s*号线\s*支线", line_text)
            if "支" in line_text and "6" in line_text:
                line_code = "SZ6B"
            elif m:
                num = m.group(1)
                line_code = "SZ28" if num in {"2", "8"} else f"SZ{num}"
            else:
                continue
            # Station name is normally in the page title / h1.
            title = clean_text((soup.find("h1") or soup.find("h2") or soup.title).get_text(" ", strip=True)) if (soup.find("h1") or soup.find("h2") or soup.title) else ""
            title = re.sub(r"站点介绍|站点|深圳地铁|[-|].*", "", title).strip()
            station = expected_station or map_name(title, lookup)
            if station and direction and first and last and station != direction:
                output.append((typ, station, line_code, direction, first, last))
    return output


def add_record(target: dict[str, Any], station: str, line: str, terminal: str, first: str, last: str, source: str) -> None:
    target.setdefault(station, {}).setdefault(line, {})[terminal] = {
        "first": first,
        "last": last,
        "source": source,
    }


def schedule_type_for(date: dt.date) -> str:
    if date.year == 2026:
        if date in WORKDAYS_2026:
            return "workday"
        if date in HOLIDAYS_2026:
            return "holiday"
    return "dayoff" if date.weekday() >= 5 else "workday"


def build_effective_hours(schedules: dict[str, Any], selected: str) -> tuple[dict[str, Any], dict[str, int]]:
    """Build today's usable table without inventing any times.

    Official sites sometimes expose only a working-day table, or one day-type
    page can be temporarily unavailable. Keep all records from the selected
    day type first, then supplement only missing station/line/direction records
    from the other official day types. Every supplemented record is marked so
    the provenance is visible in the JSON and diagnostic report.
    """
    order = [selected] + [x for x in ("workday", "dayoff", "holiday") if x != selected]
    effective: dict[str, Any] = {}
    fallback_counts = {"workday": 0, "dayoff": 0, "holiday": 0}
    for typ in order:
        for station, by_line in (schedules.get(typ) or {}).items():
            for line, by_terminal in by_line.items():
                for terminal, record in by_terminal.items():
                    target = effective.setdefault(station, {}).setdefault(line, {})
                    if terminal in target:
                        continue
                    copied = copy.deepcopy(record)
                    if typ != selected:
                        copied["fallbackDayType"] = typ
                        fallback_counts[typ] += 1
                    target[terminal] = copied
    return effective, fallback_counts


def canonical_service_data(schedules: dict[str, Any], selected: str, effective: dict[str, Any]) -> str:
    return json.dumps({"selected": selected, "schedules": schedules, "effective": effective}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def main() -> int:
    if not DATA_FILE.exists() or not VERSION_FILE.exists():
        print("ERROR: shenzhen-data.json or shenzhen-version.json is missing; no files changed", file=sys.stderr)
        return 2
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    manifest = json.loads(VERSION_FILE.read_text(encoding="utf-8"))
    lookup, _ = build_station_lookups(data)
    previous_schedules = copy.deepcopy(data.get("serviceHoursSchedules") or {"workday": {}, "dayoff": {}, "holiday": {}})
    schedules = {"workday": {}, "dayoff": {}, "holiday": {}}
    report: dict[str, Any] = {"sources": [], "errors": [], "unresolvedLines": [], "lineCounts": {}}

    print("[1/4] Reading official Shenzhen Metro timetable pages...", flush=True)
    for line_code, roots in LINE_ROOTS.items():
        line_total = 0
        for root in roots:
            try:
                root_html = get(root)
                pages = discover_schedule_pages(root, root_html)
                if not pages:
                    pages = {"workday": root}
                for typ, url in pages.items():
                    try:
                        html = root_html if url == root else get(url)
                        records = parse_english_table(html, line_code, data, lookup, url)
                        for station, line, terminal, first, last in records:
                            add_record(schedules[typ], station, line, terminal, first, last, url)
                        line_total += len(records)
                        report["sources"].append({"line": line_code, "schedule": typ, "url": url, "records": len(records)})
                    except Exception as exc:  # noqa: BLE001
                        report["errors"].append({"url": url, "error": str(exc)})
            except Exception as exc:  # noqa: BLE001
                report["errors"].append({"url": root, "error": str(exc)})
        if line_total < 10:
            for url in DIRECT_WORKDAY_HINTS.get(line_code, []):
                try:
                    html = get(url, timeout=12, attempts=1)
                    records = parse_english_table(html, line_code, data, lookup, url)
                    for station, line, terminal, first, last in records:
                        add_record(schedules["workday"], station, line, terminal, first, last, url)
                    line_total += len(records)
                    report["sources"].append({"line": line_code, "schedule": "workday", "url": url, "records": len(records), "fallback": "direct-official-page"})
                    if records:
                        break
                except Exception as exc:  # noqa: BLE001
                    report["errors"].append({"url": url, "error": str(exc)})
        report["lineCounts"][line_code] = line_total
        if line_total == 0:
            report["unresolvedLines"].append(line_code)
        print(f"  {line_code}: {line_total} direction records", flush=True)

    # Fallback: official Chinese station pages, mainly useful for newer extensions.
    print("[2/4] Checking official station pages for missing records...", flush=True)
    station_pages_checked = 0
    station_records = 0
    map_links: dict[str, str] = {}
    try:
        map_html = get("https://www.szmc.net/map/")
        soup = BeautifulSoup(map_html, "lxml")
        for a in soup.find_all("a", href=True):
            href = urljoin("https://www.szmc.net/map/", a["href"])
            if "/styles/index/zdWeb/" in href:
                code = map_name(a.get_text(" ", strip=True), lookup)
                if code:
                    map_links[code] = href
    except Exception as exc:  # noqa: BLE001
        report["errors"].append({"url": "https://www.szmc.net/map/", "error": str(exc)})

    # Only check stations on unresolved/weak lines, limiting load on the official site.
    weak_lines = {line for line, count in report["lineCounts"].items() if count < 10}
    candidate_codes: list[str] = []
    for line_code in weak_lines:
        candidate_codes.extend(code for code, _ in data["L"].get(line_code, {}).get("stations", []))
    candidate_codes = list(dict.fromkeys(candidate_codes))
    code_to_name = {c: name for line in data["L"].values() for c, name in line["stations"]}

    def fetch_station_record(code: str) -> tuple[str, str | None, list[tuple[str, str, str, str, str, str]]]:
        trad = code_to_name.get(code, "")
        simp = data.get("simplified", {}).get(code, trad)
        pinyin = data.get("roman", {}).get(trad) or data.get("roman", {}).get(simp) or data.get("roman", {}).get(code) or ""
        urls: list[str] = []
        if code in map_links:
            urls.append(map_links[code])
        slug = norm(pinyin)
        if slug:
            urls.append(f"https://www.szmc.net/styles/index/zdWeb/{slug}.html")
        for url in dict.fromkeys(urls):
            try:
                html = get(url, timeout=7, attempts=1)
                found = parse_chinese_station_page(html, data, lookup, url, expected_station=code)
                if found:
                    return code, url, found
            except Exception:
                continue
        return code, None, []

    # Bounded parallelism avoids a failed host making the workflow wait for
    # hundreds of sequential timeouts. This fallback runs only on weak lines.
    if candidate_codes:
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {executor.submit(fetch_station_record, code): code for code in candidate_codes}
            for future in as_completed(futures):
                station_pages_checked += 1
                try:
                    code, url, found = future.result()
                except Exception:
                    continue
                for typ, station, line, terminal, first, last in found:
                    add_record(schedules[typ], station, line, terminal, first, last, url or "")
                    station_records += 1
                if station_pages_checked % 25 == 0:
                    print(f"  checked {station_pages_checked}/{len(candidate_codes)} station pages; added {station_records} records", flush=True)

    # Preserve previously valid records when an official page is temporarily unavailable.
    for typ in schedules:
        old = previous_schedules.get(typ, {})
        for station, by_line in old.items():
            for line, by_terminal in by_line.items():
                for terminal, rec in by_terminal.items():
                    schedules[typ].setdefault(station, {}).setdefault(line, {}).setdefault(terminal, rec)

    now = dt.datetime.now(TZ)
    selected = schedule_type_for(now.date())
    selected_hours, fallback_counts = build_effective_hours(schedules, selected)
    station_count = len(selected_hours)
    record_count = sum(len(terms) for by_line in selected_hours.values() for terms in by_line.values())
    line_count = len({line for by_line in selected_hours.values() for line in by_line})
    direct_records = sum(len(terms) for by_line in (schedules.get(selected) or {}).values() for terms in by_line.values())
    report.update({
        "generatedAt": now.isoformat(),
        "selectedDayType": selected,
        "selectedDirectRecords": direct_records,
        "selectedStations": station_count,
        "selectedRecords": record_count,
        "selectedLines": line_count,
        "effectiveFallbackRecords": fallback_counts,
        "stationPagesChecked": station_pages_checked,
        "stationPageRecords": station_records,
    })
    REPORT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"[3/4] Validating: dayType={selected} stations={station_count} records={record_count} lines={line_count}", flush=True)
    if station_count < 40 or record_count < 70 or line_count < 4:
        print("ERROR: effective official service-hours coverage is below the safety threshold; data files not replaced. See shenzhen-service-hours-report.json", file=sys.stderr)
        return 3

    old_canon = canonical_service_data(previous_schedules, data.get("selectedServiceDayType", ""), data.get("serviceHours") or {})
    new_canon = canonical_service_data(schedules, selected, selected_hours)
    changed = old_canon != new_canon
    if changed:
        digest = hashlib.sha256(new_canon.encode("utf-8")).hexdigest()[:10]
        version = f"2.7.0-sz-data-{now:%Y%m%d%H%M}-{digest}"
        data["serviceHoursSchedules"] = schedules
        data["serviceHours"] = selected_hours
        data["selectedServiceDayType"] = selected
        data["serviceHoursUpdatedAt"] = now.isoformat()
        data["version"] = version
        data["updatedAt"] = now.date().isoformat()
        metadata = data.setdefault("metadata", {})
        metadata["serviceHoursSource"] = "Official Shenzhen Metro / MTR Shenzhen public timetable web pages"
        metadata["serviceHoursSelection"] = "2026 official holiday calendar; selected day type supplemented only with missing records from other official day-type tables"
        metadata["serviceHoursFallbackRecords"] = fallback_counts
        manifest["version"] = version
        manifest["updatedAt"] = now.date().isoformat()
        tmp_data = DATA_FILE.with_suffix(".json.tmp")
        tmp_version = VERSION_FILE.with_suffix(".json.tmp")
        tmp_data.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp_version.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp_data, DATA_FILE)
        os.replace(tmp_version, VERSION_FILE)
        print(f"[4/4] SUCCESS: updated version={version}", flush=True)
    else:
        print("[4/4] SUCCESS: official timetable data unchanged", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
