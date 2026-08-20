"""Append-only evidence archive for events first observed in source ledgers."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = Path(__import__("os").getenv("MIU_TRACE_EVENT_ARCHIVE", ROOT / "var" / "event-archive.sqlite"))
IDENTITY_FIELDS = (
    "barcode", "type", "from", "to", "before", "after", "location", "price", "quantity", "amount",
    "source_family", "source_file", "worksheet", "row", "source_id", "column",
)


def event_fingerprint(event: dict) -> str:
    identity = {field: event.get(field) for field in IDENTITY_FIELDS if event.get(field) is not None}
    encoded = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def connection(path: Path = ARCHIVE) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    database = sqlite3.connect(path)
    database.execute(
        "CREATE TABLE IF NOT EXISTS archived_events("
        "fingerprint TEXT PRIMARY KEY, barcode TEXT NOT NULL, occurred TEXT NOT NULL, "
        "payload TEXT NOT NULL, first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL)"
    )
    database.execute("CREATE INDEX IF NOT EXISTS archived_events_barcode_time ON archived_events(barcode, occurred)")
    return database


def archive_events(events: list[dict], path: Path = ARCHIVE) -> dict[str, int]:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    inserted = seen = 0
    database = connection(path)
    try:
        for original in events:
            barcode = str(original.get("barcode") or "").strip().upper()
            occurred = original.get("from") or ""
            if not barcode or not occurred or not original.get("type"):
                continue
            fingerprint = event_fingerprint(original)
            archived = dict(original)
            archived["archived"] = True
            archived["archive_first_seen_at"] = now
            archived["archive_fingerprint"] = fingerprint
            cursor = database.execute(
                "INSERT OR IGNORE INTO archived_events VALUES (?,?,?,?,?,?)",
                (fingerprint, barcode, occurred, json.dumps(archived, ensure_ascii=False, separators=(",", ":")), now, now),
            )
            inserted += cursor.rowcount
            seen += 1
        database.commit()
    finally:
        database.close()
    return {"seen": seen, "inserted": inserted}


def archived_events_for_barcode(barcode: str, path: Path = ARCHIVE) -> list[dict]:
    if not path.exists():
        return []
    database = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        return [json.loads(row[0]) for row in database.execute("SELECT payload FROM archived_events WHERE barcode=? ORDER BY occurred", (barcode,))]
    finally:
        database.close()
