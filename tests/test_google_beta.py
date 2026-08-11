import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "sync_google_beta.py"
spec = importlib.util.spec_from_file_location("sync_google_beta", MODULE_PATH)
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


def test_movement_column_parsing():
    rows = [["20260803\n온라인->성수 2"], ["YH25032085"], ["C24306"]]
    events = sync.movement_events("test", "book", "26/08", rows)
    assert {(e["barcode"], e["from"], e["before"], e["after"]) for e in events} == {
        ("YH25032085", "2026-08-03", "온라인", "성수"),
        ("C24306", "2026-08-03", "온라인", "성수"),
    }


def test_price_adjacent_column_parsing():
    rows = [["2026. 7. 24", "", ""], ["HK30034", "30,000", ""]]
    events = sync.price_events("test", "book", "공동물류", rows)
    assert events[0]["type"] == "PRICE_CHANGE"
    assert events[0]["after"] == 30000
    assert events[0]["precision"] == "DATE"


def test_duplicate_observations_keep_evidence_count():
    event = {"barcode":"C24306","type":"LOCATION_CHANGE","from":"2026-07-01","before":"폐기","after":"공동물류"}
    result = sync.dedupe([event.copy(), event.copy()])
    assert len(result) == 1
    assert result[0]["evidence_count"] == 2
