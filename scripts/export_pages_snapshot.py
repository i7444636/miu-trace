from __future__ import annotations

import gzip
import json
import sqlite3
from collections import defaultdict
from pathlib import Path

from backend.app.main import dedupe, enforce_lifecycle, static_payload, summarize

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "var" / "dropbox-index.sqlite"
OUTPUT = ROOT / "frontend" / "data" / "index"

def shard_name(barcode: str) -> str:
    first = (barcode[:1] or "_").upper()
    return first if first.isascii() and first.isalnum() else "_"

def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(f"file:{INDEX.as_posix()}?mode=ro", uri=True)
    products = {row[0]: json.loads(row[1]) for row in connection.execute("SELECT barcode,payload FROM products")}
    events: dict[str, list[dict]] = defaultdict(list)
    for barcode, payload in connection.execute("SELECT barcode,payload FROM events ORDER BY barcode,occurred"):
        events[barcode].append(json.loads(payload))
    meta = dict(connection.execute("SELECT key,value FROM meta"))
    connection.close()
    for event in static_payload().get("events", []):
        events[event["barcode"]].append(event)
    shards: dict[str, dict] = defaultdict(dict)
    for barcode in sorted(set(products) | set(events)):
        product = products.get(barcode)
        timeline = enforce_lifecycle(dedupe(events.get(barcode, [])), product)
        summary, counts = summarize(barcode, product, timeline)
        shards[shard_name(barcode)][barcode] = {"barcode":barcode,"found":True,"product":product,"current_state":{"location":(product or {}).get("location"),"status":(product or {}).get("status"),"price":(product or {}).get("price"),"updated_at":(product or {}).get("updated_at")},"summary":summary,"counts":counts,"events":timeline,"count":len(timeline),"generated_at":meta.get("generated_at"),"sales_coverage_end":meta.get("sales_coverage_end"),"google_diagnostics":[]}
    for old in OUTPUT.glob("*.json.gz"):
        old.unlink()
    for name, payload in shards.items():
        with gzip.open(OUTPUT / f"{name}.json.gz", "wt", encoding="utf-8", compresslevel=9) as handle:
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
    print(json.dumps({"products":sum(map(len,shards.values())),"shards":len(shards),"bytes":sum(p.stat().st_size for p in OUTPUT.glob('*.gz'))}))

if __name__ == "__main__":
    main()
