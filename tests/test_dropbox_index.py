from backend.app.dropbox_index import change_timestamp, information_changes, normalize_category


def test_information_change_preserves_before_and_after_values():
    changes = information_changes(
        {"description": "버버리 자켓", "category": "자켓"},
        {"description": "크레스트브릿지 자켓", "category": "자켓"},
    )
    assert changes == [{"field": "description", "label": "상품명/설명", "before": "버버리 자켓", "after": "크레스트브릿지 자켓", "kind": "CHANGED"}]


def test_information_change_marks_missing_and_restored_values():
    changes = information_changes(
        {"description": "셔츠", "category": None},
        {"description": None, "category": "상의"},
    )
    assert [change["kind"] for change in changes] == ["MISSING", "RESTORED"]


def test_round_is_not_an_information_change():
    assert information_changes({"round": "0202"}, {"round": None}) == []


def test_online_category_prefix_is_removed():
    assert normalize_category("온자켓") == "자켓"
    assert normalize_category("자켓") == "자켓"


def test_location_snapshot_uses_newer_row_update_date():
    before = {"updated_at": "2025-10-01"}
    after = {"updated_at": "2026-06-26"}
    assert change_timestamp(before, after, "2026-05-01", "2026-06-01") == (
        "2026-06-26", None, "DATE", "CONFIRMED", True,
    )


def test_location_snapshot_keeps_range_when_update_date_did_not_change():
    before = {"updated_at": "2025-10-01"}
    after = {"updated_at": "2025-10-01"}
    assert change_timestamp(before, after, "2026-05-01", "2026-06-01") == (
        "2026-05-01", "2026-06-01", "RANGE", "HIGH", False,
    )
