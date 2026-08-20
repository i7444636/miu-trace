import json
from fastapi.testclient import TestClient
from backend.app.main import app, fill_event_state, resolve_current_state

def test_known_barcode_timeline_is_chronological():
    response=TestClient(app).get("/api/barcodes/HK30034/timeline")
    assert response.status_code==200
    events=response.json()["events"]
    assert len(events)>=12
    assert [event["from"] for event in events]==sorted(event["from"] for event in events)
    types={event["type"] for event in events}
    assert {"RECEIVED","SOLD","REFUND","LOCATION_CHANGE","PRICE_CHANGE"} <= types
    payload=response.json()
    assert payload["product"]["received_at"]=="2025-06-20"
    assert payload["current_state"]["location"]=="성수"
    assert "판매 1건, 환불 1건" in payload["summary"]
    assert events[0]["type"]=="RECEIVED"
    assert all(event["from"] >= payload["product"]["received_at"] for event in events)
    assert events[1]["from"]=="2025-06-25"
    assert not any(event.get("precision")=="RANGE" and event["type"]=="LOCATION_CHANGE" for event in events)
    assert not any(event.get("precision")=="RANGE" and event["type"]=="PRICE_CHANGE" for event in events)


def test_batch_lookup_deduplicates_codes_and_returns_compact_results():
    response=TestClient(app).post("/api/barcodes/batch",json={"barcodes":["HK30034"," C24306 ","HK30034"]})
    assert response.status_code==200
    payload=response.json()
    assert payload["requested"]==2
    assert [item["barcode"] for item in payload["results"]]==["HK30034","C24306"]


def test_price_change_uses_last_known_price():
    events = fill_event_state([
        {"type":"RECEIVED","from":"2025-01-01","price":45000},
        {"type":"PRICE_CHANGE","from":"2025-02-01","after":39000},
        {"type":"PRICE_CHANGE","from":"2025-03-01","after":35000},
    ])
    assert events[1]["before"] == 45000
    assert events[2]["before"] == 39000


def test_current_state_uses_latest_sale_or_refund_event():
    product = {"status": "보유", "location": "성수"}
    assert resolve_current_state(product, [{"type": "SOLD", "from": "2026-08-19"}])["status"] == "판매됨"
    assert resolve_current_state(product, [{"type": "SOLD", "from": "2026-08-19"}, {"type": "REFUND", "from": "2026-08-20"}])["status"] == "보유"
