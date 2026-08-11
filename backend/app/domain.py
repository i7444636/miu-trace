from datetime import date, timedelta
from enum import StrEnum
import re

class EventType(StrEnum):
    RECEIVED="RECEIVED"; LOCATION_CHANGE="LOCATION_CHANGE"; PRICE_CHANGE="PRICE_CHANGE"
    SOLD="SOLD"; REFUND="REFUND"; STATUS_CHANGE="STATUS_CHANGE"; INFO_CHANGE="INFO_CHANGE"
    DISCARDED="DISCARDED"; STOCK_ADJUSTMENT="STOCK_ADJUSTMENT"; UNKNOWN_EVENT="UNKNOWN_EVENT"

ZERO_WIDTH=re.compile(r"[\u200b-\u200d\ufeff]")
def normalize_barcode(value): return ZERO_WIDTH.sub("",str(value or "")).strip().upper()

def is_allowed_event(family,sheet,event,occurred_on=None,coverage_end=None):
    if event==EventType.RECEIVED: return family=="DROPBOX_COMMON_SALES" and sheet=="입고"
    if event in {EventType.LOCATION_CHANGE,EventType.PRICE_CHANGE}: return family=="DROPBOX_COMMON_SALES" and sheet=="입고"
    if event in {EventType.SOLD,EventType.REFUND}:
        if family=="DROPBOX_STORE_SALES": return sheet=="매출"
        return family=="DROPBOX_COMMON_SALES" and sheet=="전매장매출" and occurred_on and coverage_end and occurred_on>coverage_end
    return family!="DROPBOX_STORE_SALES"

def calculate_coverage(dates,today):
    valid=sorted(d for d in dates if d<=today)
    end=valid[-1] if valid else None
    return {"start":valid[0] if valid else None,"end":end,"uncovered_start":end+timedelta(days=1) if end and end<today else None,"uncovered_end":today}

