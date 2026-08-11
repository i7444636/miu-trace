from backend.app.dropbox_index import information_changes


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
