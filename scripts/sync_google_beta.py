"""Build a no-secret Google Sheets beta dataset for known-answer barcodes."""
from __future__ import annotations
import csv, io, json, re, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"frontend"/"data"/"beta-events.json"
TARGETS={"C24306","HK30034","YH25032085"}
MOVEMENT={
 "google_sheet_01":("1CTbxn5MdvSaxlukEOBVlIzqPgFJn5wAaczE8-V4o4PI",["25/01","25/02","25/03","25/04","25/05","25/06","25/07"]),
 "google_sheet_02":("1g2an-a3jnyDR9XTrCn_4bg-JEyinWaVW2yuLtRlvARU",["25/08","25/09","25/10","25/11","25/12"]),
 "google_sheet_03":("19d7I0iczbb8oaVmoTejAU2BxdnZDkm-DJhoVN4Pd1b4",["26/01","26/02","26/03","26/04"]),
 "google_sheet_04":("1oEm00RGr3KL0fFx0HTXdFX855_DlMeHzjryZk_i89tc",["26/04_2"]),
}
PRICE=("google_sheet_05","1-tpMUl-MRmdMzVLE7F637FVBOhSjkWA1rQLT0_-H67I",["공동물류","온라인"])
DATE8=re.compile(r"(?<![0-9])(20[0-9]{6})(?![0-9])")
ROUTE=re.compile(r"([^\s\d]+?)\s*->\s*([^\s\d]+)")

def norm(v): return re.sub(r"[\u200b-\u200d\ufeff\s]","",str(v or "")).upper()
def fetch(book,sheet):
 q=urllib.parse.urlencode({"tqx":"out:csv","sheet":sheet})
 req=urllib.request.Request(f"https://docs.google.com/spreadsheets/d/{book}/gviz/tq?{q}",headers={"User-Agent":"MIU-Trace-Beta/0.2"})
 with urllib.request.urlopen(req,timeout=45) as res: return list(csv.reader(io.StringIO(res.read().decode("utf-8-sig"))))
def source_url(book,sheet): return f"https://docs.google.com/spreadsheets/d/{book}/edit#sheet={urllib.parse.quote(sheet)}"
def movement_events(source,book,sheet,rows,targets=TARGETS):
 out=[]
 if not rows:return out
 for col in range(max(map(len,rows))):
  header=rows[0][col].strip() if col<len(rows[0]) else ""
  dm,rm=DATE8.search(header),ROUTE.search(header)
  if not dm or not rm:continue
  raw_day=dm.group(1)
  try: day=date(int(raw_day[:4]),int(raw_day[4:6]),int(raw_day[6:8])).isoformat()
  except ValueError: continue
  before,after=rm.group(1).strip(),rm.group(2).strip()
  found=set()
  for token in re.findall(r"[A-Za-z]{1,5}\d{1,12}|\d{12,14}",header):
   code=norm(token)
   if code in targets:found.add((code,1))
  for row_no,row in enumerate(rows[1:],2):
   if col<len(row) and norm(row[col]) in targets:found.add((norm(row[col]),row_no))
  for code,row_no in found:
   out.append({"barcode":code,"type":"LOCATION_CHANGE","label":"위치 이동","from":day,"precision":"DATE","confidence":"HIGH","before":before,"after":after,"source_family":"GOOGLE_SHEETS","source_id":source,"worksheet":sheet,"row":row_no,"column":col+1,"evidence":f"Google Sheets · {sheet} · {day} · {before} → {after}","source_url":source_url(book,sheet)})
 return out
def parse_day(v):
 m=re.search(r"(20\d{2})\s*\.\s*(\d{1,2})\s*\.\s*(\d{1,2})",v)
 return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else None
def price_events(source,book,sheet,rows,targets=TARGETS):
 out=[]
 if not rows:return out
 for col in range(max(map(len,rows))):
  day=parse_day(rows[0][col].strip() if col<len(rows[0]) else "")
  if not day:continue
  for row_no,row in enumerate(rows[1:],2):
   if col>=len(row) or norm(row[col]) not in targets:continue
   code=norm(row[col]); raw=row[col+1] if col+1<len(row) else ""; digits=re.sub(r"[^0-9-]","",raw)
   out.append({"barcode":code,"type":"PRICE_CHANGE","label":"가격 수정","from":day,"precision":"DATE","confidence":"HIGH","after":int(digits) if digits else None,"location":sheet,"source_family":"GOOGLE_SHEETS","source_id":source,"worksheet":sheet,"row":row_no,"column":col+1,"evidence":f"Google Sheets · {sheet} · {day} · {raw or '가격 미확인'}","source_url":source_url(book,sheet)})
 return out
def dedupe(events):
 grouped={}
 for event in events:
  key=(event["barcode"],event["type"],event["from"],event.get("before"),event.get("after"),event.get("location"))
  if key not in grouped:event["evidence_count"]=1;grouped[key]=event
  else:grouped[key]["evidence_count"]+=1
 return sorted(grouped.values(),key=lambda e:(e["barcode"],e["from"],e["type"]))
def collect_events(targets):
 targets={norm(value) for value in targets if norm(value)}
 jobs=[]
 for source,(book,sheets) in MOVEMENT.items():
  jobs += [("movement",source,book,sheet) for sheet in sheets]
 source,book,sheets=PRICE
 jobs += [("price",source,book,sheet) for sheet in sheets]
 events=[];diagnostics=[]
 def run(job):
  kind,source,book,sheet=job;rows=fetch(book,sheet)
  parsed=movement_events(source,book,sheet,rows,targets) if kind=="movement" else price_events(source,book,sheet,rows,targets)
  return parsed,{"source_id":source,"worksheet":sheet,"status":"INDEXED","rows":len(rows),"events":len(parsed)}
 with ThreadPoolExecutor(max_workers=6) as pool:
  futures={pool.submit(run,job):job for job in jobs}
  for future in as_completed(futures):
   kind,source,book,sheet=futures[future]
   try:parsed,diagnostic=future.result();events+=parsed;diagnostics.append(diagnostic)
   except Exception as exc:diagnostics.append({"source_id":source,"worksheet":sheet,"status":"ERROR","error":str(exc)})
 return dedupe(events),diagnostics
def main():
 events,diagnostics=collect_events(TARGETS)
 payload={"generated_at":datetime.now().astimezone().isoformat(timespec="seconds"),"mode":"PUBLIC_GOOGLE_SHEETS_BETA","barcodes":sorted(TARGETS),"events":events,"diagnostics":diagnostics}
 OUTPUT.parent.mkdir(parents=True,exist_ok=True);OUTPUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps({"output":str(OUTPUT),"events":len(payload["events"]),"errors":sum(d["status"]=="ERROR" for d in diagnostics)}))
if __name__=="__main__":main()
