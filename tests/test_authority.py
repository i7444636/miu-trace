from datetime import date
from app.domain import EventType,is_allowed_event,normalize_barcode,calculate_coverage

def test_authority():
    assert is_allowed_event("DROPBOX_COMMON_SALES","입고",EventType.RECEIVED)
    assert not is_allowed_event("DROPBOX_STORE_SALES","매입",EventType.RECEIVED)
    assert not is_allowed_event("DROPBOX_STORE_SALES","출고",EventType.LOCATION_CHANGE)
    assert is_allowed_event("DROPBOX_STORE_SALES","매출",EventType.SOLD)

def test_fallback_and_normalization():
    end=date(2026,7,31)
    assert not is_allowed_event("DROPBOX_COMMON_SALES","전매장매출",EventType.SOLD,date(2025,1,1),end)
    assert is_allowed_event("DROPBOX_COMMON_SALES","전매장매출",EventType.SOLD,date(2026,8,5),end)
    assert normalize_barcode(" c24304\u200b ")=="C24304"
    assert calculate_coverage([end],date(2026,8,11))["uncovered_start"]==date(2026,8,1)

