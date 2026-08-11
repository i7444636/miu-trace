import json
from fastapi.testclient import TestClient
from backend.app.main import app

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
