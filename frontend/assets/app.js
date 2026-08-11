const demo={C24304:[
  {type:"LOCATION_CHANGE",label:"위치 이동",from:"2026-06-30T23:59:00+09:00",to:"2026-07-02T09:00:00+09:00",precision:"RANGE",confidence:"HIGH",before:"폐기",after:"공동물류",evidence:"공동판매_auto / 입고 월별 snapshot"},
  {type:"REFUND",label:"환불",from:"2026-05-17T14:21:00+09:00",precision:"EXACT",confidence:"CONFIRMED",evidence:"전매장매입매출 / 매출"},
  {type:"RECEIVED",label:"정식 입고",from:"2026-01-13T00:00:00+09:00",precision:"DATE",confidence:"CONFIRMED",evidence:"공동판매_auto / 입고"},
  {type:"SOLD",label:"판매",from:"2026-05-14T11:08:00+09:00",precision:"EXACT",confidence:"CONFIRMED",evidence:"전매장매입매출 / 매출"}
]};
const icons={RECEIVED:"＋",LOCATION_CHANGE:"↗",PRICE_CHANGE:"₩",SOLD:"✓",REFUND:"↩",STATUS_CHANGE:"●",INFO_CHANGE:"i",DISCARDED:"×",RESOLD:"↻"};
const precisionLabel={EXACT:"정확한 시각",DATE:"날짜",MONTH:"월 단위",RANGE:"추정 기간",UNKNOWN:"시점 불명"};
const form=document.querySelector("#search"),input=document.querySelector("#barcode"),out=document.querySelector("#result"),demoButton=document.querySelector("#demo-code");

form.addEventListener("submit",async event=>{event.preventDefault();await search(input.value)});
demoButton.addEventListener("click",async()=>{input.value="C24306";await search("C24306")});

async function search(raw){
  const code=raw.trim().toUpperCase(); if(!code)return;
  out.innerHTML='<div class="empty"><strong>기록을 조회하고 있습니다</strong><p>인덱스에서 근거를 확인하는 중입니다.</p></div>';
  try{
    let events;
    if(window.MIU_TRACE_CONFIG.API_BASE_URL){
      const response=await fetch(`${window.MIU_TRACE_CONFIG.API_BASE_URL}/api/barcodes/${encodeURIComponent(code)}/timeline`,{cache:"no-store"});
      if(!response.ok)throw new Error("API 조회에 실패했습니다."); events=(await response.json()).events;
    }else if(window.MIU_TRACE_CONFIG.STATIC_BETA_URL){
      const response=await fetch(window.MIU_TRACE_CONFIG.STATIC_BETA_URL,{cache:"no-store"});
      if(!response.ok)throw new Error("Google Sheets 베타 인덱스를 읽지 못했습니다.");
      const payload=await response.json(); events=payload.events.filter(item=>item.barcode===code);
    }else events=demo[code]||[];
    render(code,events);
  }catch(error){out.innerHTML=`<div class="empty"><strong>조회하지 못했습니다</strong><p>${escapeHtml(error.message)}</p></div>`}
}

function eventTime(event){return new Date(event.from||event.time_from||event.occurred_at||0).getTime()||0}
function render(code,events){
  const ordered=[...events].sort((a,b)=>eventTime(a)-eventTime(b));
  if(!ordered.length){out.innerHTML=`<div class="empty"><strong>${escapeHtml(code)} 기록 없음</strong><p>현재 연결된 근거에서 해당 바코드를 찾지 못했습니다.</p></div>`;return}
  out.innerHTML=`<div class="result-header"><div><h2>${escapeHtml(code)} 타임라인</h2><p>가장 오래된 기록부터 시간순으로 정렬했습니다.</p></div><span class="event-count">${ordered.length}개 사건</span></div><div class="timeline">${ordered.map(eventCard).join("")}</div>`;
}

function eventCard(item){
  const type=item.type||item.event_type,confidence=(item.confidence||"UNKNOWN").toUpperCase();
  const from=item.from||item.time_from,to=item.to||item.time_to,precision=item.precision||item.time_precision||"UNKNOWN";
  const change=item.before?`<div class="change"><span>${escapeHtml(item.before)}</span><span class="change-arrow">→</span><span>${escapeHtml(item.after)}</span></div>`:type==="PRICE_CHANGE"?`<div class="change"><span>${escapeHtml(item.location||"가격")}</span><span class="change-arrow">·</span><span>${formatPrice(item.after)}</span></div>`:"";
  const evidenceText=escapeHtml(item.evidence||`${item.evidence_count||0}건`);
  const evidence=item.source_url?`<a href="${escapeHtml(item.source_url)}" target="_blank" rel="noopener">${evidenceText}</a>`:evidenceText;
  return `<article class="event" data-type="${escapeHtml(type)}"><span class="timeline-node" aria-hidden="true"></span><div class="event-card"><div class="event-main"><div class="event-topline"><div class="event-title-wrap"><span class="type-icon">${icons[item.display_label]||icons[type]||"·"}</span><span class="event-title">${escapeHtml(item.label||item.display_label||type)}</span></div><span class="confidence ${confidence==="CONFIRMED"?"confirmed":""}">${confidence==="CONFIRMED"?"확정":confidence}</span></div><p class="event-time">${formatTime(from,to,precision)} <span class="precision">· ${precisionLabel[precision]||precision}</span></p>${change}</div><div class="evidence"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M1.75 2.5A1.75 1.75 0 0 1 3.5.75h5.25a1.75 1.75 0 0 1 1.75 1.75v.75h2A1.75 1.75 0 0 1 14.25 5v8.5a1.75 1.75 0 0 1-1.75 1.75h-9A1.75 1.75 0 0 1 1.75 13.5Zm1.5 0v11a.25.25 0 0 0 .25.25h9a.25.25 0 0 0 .25-.25V5a.25.25 0 0 0-.25-.25h-2v6.75a.75.75 0 0 1-1.5 0v-9a.25.25 0 0 0-.25-.25H3.5a.25.25 0 0 0-.25.25Z"/></svg><span>근거 · ${evidence}</span></div></div></article>`;
}

function formatTime(from,to,precision){if(!from)return"시점 불명";if(precision==="RANGE"&&to)return`${dateText(from)} ~ ${dateText(to)}`;return precision==="EXACT"?dateTimeText(from):dateText(from)}
function dateText(value){return new Intl.DateTimeFormat("ko-KR",{year:"numeric",month:"long",day:"numeric"}).format(new Date(value))}
function dateTimeText(value){return new Intl.DateTimeFormat("ko-KR",{year:"numeric",month:"long",day:"numeric",hour:"2-digit",minute:"2-digit",hour12:false}).format(new Date(value))}
function formatPrice(value){return value==null?"가격 미확인":`${new Intl.NumberFormat("ko-KR").format(value)}원`}
function escapeHtml(value){return String(value??"").replace(/[&<>'"]/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"})[char])}
if("serviceWorker" in navigator)navigator.serviceWorker.register("service-worker.js");
