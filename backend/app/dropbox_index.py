from __future__ import annotations

import json
import re
import sqlite3
import zipfile
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from xml.etree import ElementTree as ET

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CELL_REF = re.compile(r"([A-Z]+)(\d+)")
BARCODE = re.compile(r"^(?:[A-Z]{1,6}\d{1,14}|\d{8,14})$")


def normalize(value) -> str:
    return re.sub(r"[\u200b-\u200d\ufeff\s]", "", str(value or "")).upper()


def excel_date(value):
    if value in (None, ""):
        return None
    text = str(value).strip()
    try:
        number = float(text)
        if 30000 < number < 80000:
            return (datetime(1899, 12, 30) + timedelta(days=number)).date().isoformat()
    except ValueError:
        pass
    match = re.search(r"(20\d{2})[.\-/년\s]+(\d{1,2})[.\-/월\s]+(\d{1,2})", text)
    if match:
        try:
            return date(*map(int, match.groups())).isoformat()
        except ValueError:
            return None
    return None


def column_number(reference: str) -> int:
    letters = CELL_REF.match(reference).group(1)
    result = 0
    for letter in letters:
        result = result * 26 + ord(letter) - 64
    return result


def workbook_period(path: Path):
    match = re.search(r"(20\d{2})[._년_-]?(\d{1,2})(?:월)?", path.name)
    if not match:
        return None
    year, month = map(int, match.groups())
    if not 1 <= month <= 12:
        return None
    return f"{year:04d}-{month:02d}-01"


def iter_sheet_rows(path: Path, wanted: set[str]):
    with zipfile.ZipFile(path) as archive:
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.parse(archive.open("xl/sharedStrings.xml")).getroot()
            shared = ["".join(node.itertext()) for node in root.findall(f"{{{MAIN_NS}}}si")]
        rels_root = ET.parse(archive.open("xl/_rels/workbook.xml.rels")).getroot()
        rels = {node.attrib["Id"]: node.attrib["Target"] for node in rels_root.findall(f"{{{PKG_NS}}}Relationship")}
        book = ET.parse(archive.open("xl/workbook.xml")).getroot()
        for sheet in book.findall(f"{{{MAIN_NS}}}sheets/{{{MAIN_NS}}}sheet"):
            name = sheet.attrib["name"]
            if name not in wanted:
                continue
            target = rels[sheet.attrib[f"{{{REL_NS}}}id"]].lstrip("/")
            xml_path = target if target.startswith("xl/") else "xl/" + target
            for _, row in ET.iterparse(archive.open(xml_path), events=("end",)):
                if row.tag != f"{{{MAIN_NS}}}row":
                    continue
                values = {}
                for cell in row.findall(f"{{{MAIN_NS}}}c"):
                    col = column_number(cell.attrib.get("r", "A1"))
                    kind = cell.attrib.get("t")
                    value_node = cell.find(f"{{{MAIN_NS}}}v")
                    if kind == "inlineStr":
                        value = "".join(cell.itertext())
                    elif value_node is None:
                        value = ""
                    elif kind == "s":
                        try:
                            value = shared[int(value_node.text or "0")]
                        except (ValueError, IndexError):
                            value = value_node.text or ""
                    else:
                        value = value_node.text or ""
                    if value not in (None, ""):
                        values[col] = value
                if values:
                    yield name, int(row.attrib.get("r", "0")), values
                row.clear()


def money(value):
    try:
        return int(round(float(str(value).replace(",", ""))))
    except (TypeError, ValueError):
        return None


def information_changes(before, after):
    labels = {"description": "상품명/설명", "category": "카테고리"}
    changes = []
    for field, label in labels.items():
        old, new = before.get(field), after.get(field)
        if old == new:
            continue
        if old and not new:
            kind = "MISSING"
        elif not old and new:
            kind = "RESTORED"
        else:
            kind = "CHANGED"
        changes.append({"field": field, "label": label, "before": old, "after": new, "kind": kind})
    return changes


def build_index(paths: list[Path]):
    snapshots = defaultdict(list)
    sales = defaultdict(list)
    diagnostics = []
    finalized_coverage_end = None
    for path in sorted(paths):
        is_store = "전매장매입매출" in path.name
        period = workbook_period(path)
        counts = defaultdict(int)
        try:
            for sheet, row, values in iter_sheet_rows(path, {"입고", "매출", "전매장매출"}):
                if sheet == "입고":
                    code = normalize(values.get(7))
                    if not BARCODE.match(code):
                        continue
                    snapshots[code].append({
                        "barcode": code, "as_of": period, "received_at": excel_date(values.get(3)),
                        "location": str(values.get(2, "")).strip() or None,
                        "description": str(values.get(4, "")).strip() or None,
                        "price": money(values.get(5)), "quantity": money(values.get(6)),
                        "category": str(values.get(8, "")).strip() or None,
                        "updated_at": excel_date(values.get(15)), "source_file": path.name,
                        "sheet": sheet, "row": row,
                    })
                    counts[sheet] += 1
                elif sheet == "매출" and is_store:
                    code = normalize(values.get(5))
                    occurred = excel_date(values.get(3))
                    quantity = money(values.get(8))
                    if not BARCODE.match(code) or not occurred or not quantity:
                        continue
                    finalized_coverage_end = max(filter(None, [finalized_coverage_end, occurred]))
                    sales[code].append({
                        "barcode": code, "type": "REFUND" if quantity < 0 else "SOLD",
                        "label": "환불" if quantity < 0 else "판매", "from": occurred,
                        "precision": "DATE", "confidence": "CONFIRMED",
                        "location": str(values.get(2, "")).replace("공동판매", "").strip() or None,
                        "description": str(values.get(6, "")).strip() or None,
                        "price": money(values.get(7)), "quantity": quantity,
                        "amount": money(values.get(12)), "source_family": "DROPBOX_STORE_SALES",
                        "source_file": path.name, "worksheet": sheet, "row": row,
                        "evidence": f"Dropbox 확정 매출 · {path.name} · {sheet} {row}행",
                    })
                    counts[sheet] += 1
                elif sheet == "전매장매출" and not is_store:
                    code = normalize(values.get(4))
                    occurred = excel_date(values.get(2))
                    quantity = money(values.get(7))
                    if not BARCODE.match(code) or not occurred or not quantity:
                        continue
                    sales[code].append({
                        "barcode": code, "type": "REFUND" if quantity < 0 else "SOLD",
                        "label": "환불" if quantity < 0 else "판매", "from": occurred,
                        "precision": "DATE", "confidence": "HIGH", "fallback": True,
                        "location": str(values.get(1, "")).replace("공동판매", "").strip() or None,
                        "description": str(values.get(5, "")).strip() or None,
                        "price": money(values.get(6)), "quantity": quantity,
                        "amount": money(values.get(11)), "source_family": "DROPBOX_COMMON_SALES",
                        "source_file": path.name, "worksheet": sheet, "row": row,
                        "evidence": f"Dropbox 미마감 매출 · {path.name} · {sheet} {row}행",
                    })
                    counts[sheet] += 1
            diagnostics.append({"source": path.name, "status": "INDEXED", "records": dict(counts)})
        except Exception as exc:
            diagnostics.append({"source": path.name, "status": "ERROR", "error": str(exc)})

    products, events = {}, []
    for code, observations in snapshots.items():
        unique = {}
        for observation in observations:
            key = observation.get("as_of") or observation["source_file"]
            unique[key] = observation
        ordered = sorted(unique.values(), key=lambda item: item.get("as_of") or "")
        latest = ordered[-1]
        status = "폐기" if latest.get("location") == "폐기" else "판매됨" if any(e["type"] == "SOLD" for e in sales.get(code, [])) and not any(e["type"] == "REFUND" for e in sales.get(code, [])) else "보유"
        products[code] = {key: latest.get(key) for key in ("barcode", "received_at", "location", "description", "price", "quantity", "category", "updated_at")}
        products[code]["status"] = status
        received = next((item.get("received_at") for item in ordered if item.get("received_at")), None)
        if received:
            events.append({"barcode": code, "type": "RECEIVED", "label": "정식 입고", "from": received, "precision": "DATE", "confidence": "CONFIRMED", "after": ordered[0].get("location"), "price": ordered[0].get("price"), "source_family": "DROPBOX_COMMON_SALES", "source_file": ordered[0]["source_file"], "worksheet": "입고", "row": ordered[0]["row"], "evidence": f"Dropbox 공식 입고 · {ordered[0]['source_file']} · 입고 {ordered[0]['row']}행"})
        for before, after in zip(ordered, ordered[1:]):
            time_from, time_to = before.get("as_of"), after.get("as_of")
            if received and time_from and time_from < received:
                time_from = received
            if time_from and time_to and time_to <= time_from:
                continue
            if before.get("location") != after.get("location"):
                event_type = "DISCARDED" if after.get("location") == "폐기" else "LOCATION_CHANGE"
                events.append({"barcode": code, "type": event_type, "label": "폐기" if event_type == "DISCARDED" else "위치 이동", "from": time_from, "to": time_to, "precision": "RANGE", "confidence": "HIGH", "before": before.get("location"), "after": after.get("location"), "source_family": "DROPBOX_COMMON_SALES", "evidence": f"Dropbox 월별 입고 스냅샷 비교 · {before['source_file']} → {after['source_file']}"})
            if before.get("price") != after.get("price") and after.get("price") is not None:
                events.append({"barcode": code, "type": "PRICE_CHANGE", "label": "가격 변경", "from": time_from, "to": time_to, "precision": "RANGE", "confidence": "HIGH", "before": before.get("price"), "after": after.get("price"), "location": after.get("location"), "source_family": "DROPBOX_COMMON_SALES", "evidence": f"Dropbox 월별 입고 스냅샷 비교 · {before['source_file']} → {after['source_file']}"})
            changes = information_changes(before, after)
            if changes:
                kinds = {change["kind"] for change in changes}
                label = "상품 정보 수정" if kinds == {"CHANGED"} else "정보 누락/복원 가능성"
                confidence = "HIGH" if kinds == {"CHANGED"} else "MEDIUM"
                events.append({"barcode": code, "type": "INFO_CHANGE", "label": label, "from": time_from, "to": time_to, "precision": "RANGE", "confidence": confidence, "changes": changes, "source_family": "DROPBOX_COMMON_SALES", "evidence": f"Dropbox 월별 입고 스냅샷 비교 · {before['source_file']} → {after['source_file']}"})

    sales_keys = set()
    for code, rows in sales.items():
        for event in rows:
            if event.get("fallback") and finalized_coverage_end and event["from"] <= finalized_coverage_end:
                continue
            key = (code, event["type"], event["from"], event.get("location"), event.get("quantity"), event.get("price"))
            if key not in sales_keys:
                sales_keys.add(key)
                event.pop("fallback", None)
                events.append(event)
    events.sort(key=lambda event: (event["barcode"], event.get("from") or "", event["type"]))
    return {"generated_at": datetime.now().astimezone().isoformat(timespec="seconds"), "mode": "DROPBOX_AUTHORITY_BETA", "sales_coverage_end": finalized_coverage_end, "products": products, "events": events, "diagnostics": diagnostics}


def write_index(paths, output):
    payload = build_index([Path(path) for path in paths])
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    if Path(output).suffix == ".sqlite":
        temporary = Path(str(output) + ".tmp")
        if temporary.exists():
            temporary.unlink()
        connection = sqlite3.connect(temporary)
        connection.executescript("CREATE TABLE products(barcode TEXT PRIMARY KEY,payload TEXT NOT NULL);CREATE TABLE events(barcode TEXT NOT NULL,occurred TEXT NOT NULL,payload TEXT NOT NULL);CREATE INDEX events_barcode_time ON events(barcode,occurred);CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT);")
        connection.executemany("INSERT INTO products VALUES (?,?)", ((code, json.dumps(product, ensure_ascii=False, separators=(",", ":"))) for code, product in payload["products"].items()))
        connection.executemany("INSERT INTO events VALUES (?,?,?)", ((event["barcode"], event.get("from") or "", json.dumps(event, ensure_ascii=False, separators=(",", ":"))) for event in payload["events"]))
        for key in ("generated_at", "mode", "sales_coverage_end"):
            connection.execute("INSERT INTO meta VALUES (?,?)", (key, payload.get(key)))
        connection.execute("INSERT INTO meta VALUES (?,?)", ("diagnostics", json.dumps(payload["diagnostics"], ensure_ascii=False)))
        connection.commit(); connection.close()
        temporary.replace(output)
    else:
        Path(output).write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return payload
