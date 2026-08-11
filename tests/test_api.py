import json
from fastapi.testclient import TestClient
from backend.app.main import app

def test_known_barcode_timeline_is_chronological():
    response=TestClient(app).get("/api/barcodes/HK30034/timeline")
    assert response.status_code==200
    events=response.json()["events"]
    assert len(events)==8
    assert [event["from"] for event in events]==sorted(event["from"] for event in events)
    assert events[-1]["type"]=="PRICE_CHANGE"
    assert events[-1]["after"]==30000

