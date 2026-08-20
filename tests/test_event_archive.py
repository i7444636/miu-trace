from backend.app.event_archive import archive_events, archived_events_for_barcode, mark_observed_events


def test_archive_keeps_first_seen_event_after_source_disappears(tmp_path):
    archive = tmp_path / "event-archive.sqlite"
    sale = {
        "barcode": "WW1002", "type": "SOLD", "from": "2026-08-19", "quantity": 1,
        "source_family": "DROPBOX_COMMON_SALES", "source_file": "2026.08_공동판매.xlsx", "worksheet": "전매장매출", "row": 2301,
    }
    assert archive_events([sale], archive) == {"seen": 1, "inserted": 1}
    assert archive_events([], archive) == {"seen": 0, "inserted": 0}
    saved = archived_events_for_barcode("WW1002", archive)
    assert len(saved) == 1
    assert saved[0]["type"] == "SOLD"
    assert saved[0]["archived"] is True


def test_archive_deduplicates_same_source_event(tmp_path):
    archive = tmp_path / "event-archive.sqlite"
    event = {"barcode": "SB26062015", "type": "REFUND", "from": "2026-08-20", "quantity": -1, "source_family": "DROPBOX_COMMON_SALES", "source_file": "2026.08_공동판매.xlsx", "worksheet": "전매장매출", "row": 8}
    assert archive_events([event], archive)["inserted"] == 1
    assert archive_events([event], archive)["inserted"] == 0
    assert len(archived_events_for_barcode("SB26062015", archive)) == 1


def test_live_event_is_marked_when_it_exists_in_archive(tmp_path):
    archive = tmp_path / "event-archive.sqlite"
    event = {"barcode": "WW1002", "type": "SOLD", "from": "2026-08-19", "quantity": 1, "source_family": "DROPBOX_COMMON_SALES", "source_file": "2026.08_공동판매.xlsx", "worksheet": "전매장매출", "row": 42}
    archive_events([event], archive)
    marked = mark_observed_events([event], archived_events_for_barcode("WW1002", archive))
    assert marked[0]["archived"] is True
