from __future__ import annotations
import json, os, re
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

ROOT=Path(__file__).resolve().parents[2]
DATA=Path(os.getenv("MIU_TRACE_DATA",ROOT/"frontend"/"data"/"beta-events.json"))
PAGES_ORIGIN=os.getenv("MIU_TRACE_PAGES_ORIGIN","https://i7444636.github.io")
app=FastAPI(title="MIU Trace Beta API",version="0.2.0")
app.add_middleware(CORSMiddleware,allow_origins=[PAGES_ORIGIN],allow_methods=["GET"],allow_headers=["*"])

def normalize(value:str)->str:return re.sub(r"[\u200b-\u200d\ufeff\s]","",value).upper()
def load()->dict:
    try:return json.loads(DATA.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as exc:raise HTTPException(503,f"beta index unavailable: {exc}")

@app.get("/api/health")
def health():
    payload=load()
    return {"status":"ok","version":app.version,"mode":payload.get("mode"),"generated_at":payload.get("generated_at"),"events":len(payload.get("events",[])),"checked_at":datetime.now(timezone.utc).isoformat()}

@app.get("/api/barcodes/{barcode}/timeline")
def timeline(barcode:str):
    code=normalize(barcode)
    if not code:raise HTTPException(400,"barcode required")
    payload=load();events=[event for event in payload.get("events",[]) if event.get("barcode")==code]
    events.sort(key=lambda event:(event.get("from") or "",event.get("type") or ""))
    return {"barcode":code,"events":events,"count":len(events),"generated_at":payload.get("generated_at")}

@app.get("/api/sources")
def sources():
    payload=load()
    return {"generated_at":payload.get("generated_at"),"diagnostics":payload.get("diagnostics",[])}

