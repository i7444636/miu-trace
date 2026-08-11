from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

import requests

from backend.app.dropbox_index import write_index

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CACHE = ROOT / "var" / "dropbox-cache"
DEFAULT_OUTPUT = ROOT / "var" / "dropbox-index.sqlite"


def token():
    response = requests.post("https://api.dropboxapi.com/oauth2/token", data={"grant_type": "refresh_token", "refresh_token": os.environ["DROPBOX_REFRESH_TOKEN"], "client_id": os.environ["DROPBOX_APP_KEY"], "client_secret": os.environ["DROPBOX_APP_SECRET"]}, timeout=30)
    response.raise_for_status()
    return response.json()["access_token"]


def list_files(access_token):
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    payload = {"path": "", "recursive": True, "include_deleted": False, "limit": 2000}
    entries = []
    endpoint = "https://api.dropboxapi.com/2/files/list_folder"
    while True:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=90)
        response.raise_for_status()
        body = response.json()
        entries.extend(body["entries"])
        if not body.get("has_more"):
            break
        endpoint = "https://api.dropboxapi.com/2/files/list_folder/continue"
        payload = {"cursor": body["cursor"]}
    return [entry for entry in entries if entry.get(".tag") == "file" and entry.get("name", "").lower().endswith(".xlsx") and ("공동판매_auto" in entry.get("path_display", "") or "전매장매입매출" in entry.get("path_display", ""))]


def download(access_token, entry, cache):
    safe = re.sub(r"[^0-9A-Za-z가-힣._-]+", "__", entry["path_display"].strip("/"))
    target = cache / safe
    revision_file = target.with_suffix(target.suffix + ".rev")
    if target.exists() and revision_file.exists() and revision_file.read_text() == entry.get("rev"):
        return target
    response = requests.post("https://content.dropboxapi.com/2/files/download", headers={"Authorization": f"Bearer {access_token}", "Dropbox-API-Arg": json.dumps({"path": entry["path_lower"]})}, timeout=180)
    response.raise_for_status()
    target.write_bytes(response.content)
    revision_file.write_text(entry.get("rev", ""))
    return target


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--local", action="store_true")
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    if args.local:
        paths = list(args.cache.glob("*.xlsx"))
    else:
        access_token = token()
        paths = [download(access_token, entry, args.cache) for entry in list_files(access_token)]
    result = write_index(paths, args.output)
    print(json.dumps({"files": len(paths), "products": len(result["products"]), "events": len(result["events"]), "coverage_end": result["sales_coverage_end"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
