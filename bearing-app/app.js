/* Bearing App — instant local search, i18n AR/EN, compare, export */
const $ = id => document.getElementById(id);
const norm = s => (s||"").toString().trim().toUpperCase().replace(/[\s\-_\/]/g,"");
const B = () => window.BEARINGS || [];

// ---------- i18n ----------
const I = {
  ar: { title:"دليل مقاسات رولمان البلي", subtitle:"بحث فوري • رسم هندسي • مقارنة ومطابقات — يعمل أوفلاين",
    tabA:"🔍 بحث بالكود", tabB:"📐 بحث بالمقاس", tabAll:"📋 كل المقاسات", popular:"الأكثر بحثاً:",
    searchLbl:"اكتب كود البلية (مثال: 6204 أو 6301-2RS)", searchHint:"البحث لحظي من قاعدة بيانات محلية — بدون إنترنت وبأقل من 10ms",
    resultFor:"النتيجة لـ", compare:"قارن", bore:"الداخلي", outer:"الخارجي", width:"العرض",
    weight:"الوزن التقريبي", series:"السلسلة", boreCode:"كود الثقب", fit:"شحط مقترح (عمود/بيت)",
    copy:"نسخ المواصفة", pdf:"طباعة / PDF", img:"حفظ صورة", diagram:"رسم هندسي تفاعلي — الأبعاد الحقيقية",
    equiv:"المطابقات عند الوكلاء (نفس المقاس)", revLbl:"بحث عكسي: أدخل الأبعاد (مم)", tol:"التفاوت", clear:"مسح",
    suffixT:"دليل اللواحق — يعني إيه 2RS و ZZ و C3؟", type:"النوع", cmpT:"مقارنة (حتى 3)",
    foot:"قاعدة بيانات محلية بعدد 100+ بلية • البحث يتم على جهازك فوراً • مناسب للورش والمحلات — صُنع للسرعة",
    copied:"✅ اتنسخت المواصفة", added:"✅ اتضافت للمقارنة", full:"المقارنة 3 فقط", noRes:"لا توجد نتيجة مطابقة", found:"نتيجة" },
  en: { title:"Bearing Dimensions Guide", subtitle:"Instant search • Technical drawing • Compare & cross-ref — works offline",
    tabA:"🔍 Code Search", tabB:"📐 Size Search", tabAll:"📋 Full Table", popular:"Popular:",
    searchLbl:"Enter bearing code (e.g. 6204 or 6301-2RS)", searchHint:"Instant local search — offline, under 10ms",
    resultFor:"Result for", compare:"Compare", bore:"Bore", outer:"Outer", width:"Width",
    weight:"Est. weight", series:"Series", boreCode:"Bore code", fit:"Suggested fit (shaft/housing)",
    copy:"Copy Specs", pdf:"Print / PDF", img:"Save Image", diagram:"Interactive drawing — true dimensions",
    equiv:"Brand equivalents (same size)", revLbl:"Reverse lookup: enter dimensions (mm)", tol:"Tolerance", clear:"Clear",
    suffixT:"Suffix guide — what do 2RS, ZZ, C3 mean?", type:"Type", cmpT:"Compare (up to 3)",
    foot:"Local dataset of 100+ bearings • On-device instant search • Built for workshops",
    copied:"✅ Specs copied", added:"✅ Added to compare", full:"Compare max 3", noRes:"No matching bearing", found:"result(s)" }
};
let lang = localStorage.getItem("brg-lang") || "ar";
function t(k){ return (I[lang]&&I[lang][k]) || I.ar[k] || k; }
function applyLang(){
  document.documentElement.lang = lang;
  document.documentElement.dir = lang==="ar" ? "rtl" : "ltr";
  document.querySelectorAll("[data-i18n]").forEach(el=>{ const k=el.getAttribute("data-i18n"); if(I[lang][k]) el.textContent=I[lang][k]; });
  $("langBtn").textContent = lang==="ar" ? "🌐 EN" : "🌐 عربي";
  renderChips(); renderSuffixes(); if(current) showResult(current.base, current.raw); runReverse(); renderAll(); renderCompare();
}

// ---------- theme ----------
function applyTheme(){
  const th = localStorage.getItem("brg-theme") || "light";
  document.documentElement.classList.toggle("dark", th==="dark");
  $("themeBtn").textContent = th==="dark" ? "☀️" : "🌙";
}

// ---------- helpers ----------
function parseQuery(q){
  const raw=(q||"").trim(); const n=norm(raw);
  const m=n.match(/^([A-Z]*)(\d{3,5})([A-Z0-9]*)$/);
  let base=n, suffix="";
  if(m){ base=m[2]; suffix=(m[1]||"")+(m[3]||""); }
  // UC series keep letters
  const uc = n.match(/^(UC\d{3,4})/); if(uc) base=uc[1];
  return {raw, base, suffix};
}
function findBearing(base){
  const b=norm(base);
  return B().find(x=>norm(x.code)===b) || B().find(x=>b.startsWith(norm(x.code))||norm(x.code).startsWith(b));
}
function estWeight(b){ // kg, hollow-cylinder approx ×0.55
  const v=Math.PI/4*(b.D*b.D-b.d*b.d)*b.B; return (v*7.85e-6*0.55);
}
function seriesOf(code){ const d=code.replace(/\D/g,""); if(/^68|^69/.test(d))return d.slice(0,4); if(/^160/.test(d))return "16000"; if(/^UC/.test(norm(code)))return "UC"; return d.slice(0,3)+"00"; }
function suffixInfo(suf){
  if(!suf) return null;
  const s=suf.toUpperCase();
  const hit=(window.SUFFIXES||[]).find(x=>{ const key=x.s.split("/")[0].trim().replace(/\s/g,""); return s.includes(key.replace("2",""))||s.includes(key); });
  // direct keyword checks
  const out=[];
  if(/2RS|RS1|LLU|DDU|2NSE|2RSR/.test(s)) out.push(window.SUFFIXES[0]);
  else if(/ZZ|2Z/.test(s)) out.push(window.SUFFIXES[1]);
  else if(/(^|[^Z])RS/.test(s)) out.push(window.SUFFIXES[2]);
  if(/C3/.test(s)) out.push(window.SUFFIXES[4]);
  if(/C4/.test(s)) out.push(window.SUFFIXES[5]);
  if(/(^|[^A-Z])K($|[^A-Z])/.test(s)) out.push(window.SUFFIXES[6]);
  return out.length?out:(hit?[hit]:null);
}

// ---------- state ----------
let current=null; let compare=JSON.parse(localStorage.getItem("brg-cmp")||"[]");

// ---------- Mode A ----------
const search=$("search"), suggest=$("suggest");
search.addEventListener("input", ()=>{
  const q=search.value; if(!q.trim()){suggest.classList.add("hidden");return;}
  const t0=performance.now();
  const n=norm(q);
  const hits=B().filter(x=>norm(x.code).includes(n)).slice(0,8);
  const ms=(performance.now()-t0).toFixed(1);
  if(!hits.length){suggest.innerHTML=`<div class="p-3 text-sm text-slate-500">${t("noRes")}</div>`;}
  else suggest.innerHTML=hits.map((h,i)=>`<div class="sug ${i===0?"sel":""}" data-c="${h.code}"><span>${h.code}</span><span class="text-slate-400 text-xs">d${h.d}×D${h.D}×B${h.B} · ${ms}ms</span></div>`).join("");
  suggest.classList.remove("hidden");
  suggest.querySelectorAll(".sug").forEach(el=>el.onclick=()=>{search.value=el.dataset.c; suggest.classList.add("hidden"); runCodeSearch();});
  // live first-hit preview
  if(hits.length) showResult(hits[0].code, q);
});
search.addEventListener("keydown", e=>{ if(e.key==="Enter"){suggest.classList.add("hidden"); runCodeSearch();} if(e.key==="Escape") suggest.classList.add("hidden"); });
document.addEventListener("click", e=>{ if(!suggest.contains(e.target)&&e.target!==search) suggest.classList.add("hidden"); });

function runCodeSearch(){ const q=search.value; if(!q.trim())return; const {base}=parseQuery(q); const hit=findBearing(base); if(hit) showResult(hit.code,q); }

function showResult(code, rawInput){
  const b=findBearing(code); if(!b) return;
  current={base:b.code, raw:rawInput||b.code};
  const {suffix}=parseQuery(rawInput||b.code);
  $("result").classList.remove("hidden");
  $("rCode").textContent=b.code+(suffix&&!norm(b.code)===norm(rawInput||"")?"":"");
  if(rawInput && norm(rawInput)!==norm(b.code)){ $("rCode").textContent=rawInput.toUpperCase().replace(/\s+/g," "); }
  const meta=(window.TYPE_META||{})[b.type]||{};
  $("rType").textContent=b.type==="tapered"?"TAPER":"BALL";
  $("rTypeAr").textContent=(lang==="ar"?meta.ar:meta.en)||b.type;
  $("rD1").textContent=b.d; $("rD2").textContent=b.D; $("rB").textContent=b.B;
  $("rW").textContent="≈ "+estWeight(b).toFixed(b.d<10?3:2)+" kg";
  $("rS").textContent=seriesOf(b.code);
  const digits=b.code.replace(/\D/g,"");
  $("rBore").textContent=digits.length>=2?digits.slice(-2)+" × 5 = "+b.d:"—";
  $("rFit").textContent=b.type==="tapered"?"k5 / H7":"k5 / H7";
  // diagram labels
  $("lblD").textContent="d = "+b.d; $("lblO").textContent="D = "+b.D; $("lblW").textContent="B = "+b.B;
  // suffix note
  const infos=suffixInfo(suffix);
  const box=$("suffixHit");
  if(infos&&infos.length){ box.classList.remove("hidden");
    box.innerHTML="<b>🔧 "+(suffix||"")+"</b><br>"+infos.map(x=>"• <b dir='ltr'>"+x.s+"</b> — "+(lang==="ar"?x.ar:x.en)).join("<br>");
  } else box.classList.add("hidden");
  // equivalents
  $("equiv").innerHTML=(window.BRANDS||[]).map(br=>`<div class="mini-stat"><span>${br}</span><b dir="ltr">${window.brandVariant(b.code,br)}</b></div>`).join("");
  // whatsapp
  const txt=encodeURIComponent(specText(b, rawInput));
  $("waBtn").href="https://wa.me/?text="+txt;
  $("result").scrollIntoView({behavior:"smooth",block:"nearest"});
}
function specText(b, raw){
  const meta=((window.TYPE_META||{})[b.type]||{});
  const L = lang==="ar";
  return `${L?"رولمان بلي":"Bearing"} ${raw||b.code}\n`+
    `d(${(L?"داخلي":"bore")})=${b.d}mm | D(${(L?"خارجي":"outer")})=${b.D}mm | B(${(L?"عرض":"width")})=${b.B}mm\n`+
    `${L?meta.ar:meta.en}\n${L?"الوزن التقريبي":"Est weight"} ≈ ${estWeight(b).toFixed(2)}kg`;
}

// actions
$("copyBtn").onclick=async()=>{ if(!current)return; const b=findBearing(current.base); try{await navigator.clipboard.writeText(specText(b,current.raw));}catch(e){ const ta=document.createElement("textarea"); ta.value=specText(b,current.raw); document.body.appendChild(ta); ta.select(); document.execCommand("copy"); ta.remove(); } toast(t("copied")); };
$("pdfBtn").onclick=()=>window.print();
$("imgBtn").onclick=()=>{
  if(!current)return; const b=findBearing(current.base);
  const c=document.createElement("canvas"); c.width=900; c.height=520; const x=c.getContext("2d");
  const dark=document.documentElement.classList.contains("dark");
  x.fillStyle=dark?"#0f172a":"#ffffff"; x.fillRect(0,0,900,520);
  x.fillStyle="#f59e0b"; x.fillRect(0,0,900,14);
  x.fillStyle=dark?"#fff":"#0f172a"; x.font="900 54px Arial"; x.fillText(b.code,40,100);
  x.font="700 30px Arial"; x.fillStyle="#f59e0b"; x.fillText(`d=${b.d}  D=${b.D}  B=${b.B} mm`,40,160);
  x.fillStyle=dark?"#cbd5e1":"#334155"; x.font="28px Arial";
  x.fillText(((window.TYPE_META||{})[b.type]||{}).en||"",40,210);
  x.font="24px Arial"; (window.BRANDS||[]).forEach((br,i)=>x.fillText(`${br}: ${window.brandVariant(b.code,br)}`,40,260+i*36));
  x.fillStyle="#94a3b8"; x.font="20px Arial"; x.fillText("Bearing Guide • d×D×B mm",40,490);
  const a=document.createElement("a"); a.download="bearing-"+b.code+".png"; a.href=c.toDataURL("image/png"); a.click();
};
$("favBtn").onclick=()=>{ if(!current)return; addCompare(current.base); };

// ---------- Mode B (reverse) ----------
function runReverse(){
  const d=parseFloat($("inD").value), o=parseFloat($("inO").value), w=parseFloat($("inW").value);
  const tol=parseFloat($("tol").value||"0");
  const list=$("revList");
  if(isNaN(d)&&isNaN(o)&&isNaN(w)){ list.innerHTML=""; $("revCount").textContent=""; return; }
  const hits=B().filter(b=>(isNaN(d)||Math.abs(b.d-d)<=tol)&&(isNaN(o)||Math.abs(b.D-o)<=tol)&&(isNaN(w)||Math.abs(b.B-w)<=tol)).slice(0,40);
  $("revCount").textContent=hits.length+" "+t("found");
  list.innerHTML=hits.length?hits.map(b=>`<div class="rev-card" data-c="${b.code}">
    <b dir="ltr" class="font-mono text-lg">${b.code}</b>
    <span dir="ltr" class="font-mono text-sm text-slate-500">d${b.d} × D${b.D} × B${b.B}</span>
    <button class="chip-btn ms-auto" data-add="${b.code}">⚖</button></div>`).join("")
    :`<div class="text-sm text-slate-500 p-4">${t("noRes")}</div>`;
  list.querySelectorAll(".rev-card").forEach(el=>el.onclick=e=>{ if(e.target.dataset.add){addCompare(e.target.dataset.add);return;} setTab("A"); search.value=el.dataset.c; showResult(el.dataset.c,el.dataset.c); window.scrollTo({top:0,behavior:"smooth"}); });
}
["inD","inO","inW","tol"].forEach(id=>$(id).addEventListener("input",runReverse));
$("revClear").onclick=()=>{ $("inD").value=$("inO").value=$("inW").value=""; runReverse(); };

// ---------- All table ----------
function renderAll(){
  const q=norm($("allQ").value||""), ty=$("allType").value;
  const rows=B().filter(b=>(!ty||b.type===ty)&&(!q||norm(b.code).includes(q)||String(b.d).includes(q)||String(b.D).includes(q))).slice(0,300);
  $("allBody").innerHTML=rows.map(b=>{const m=((window.TYPE_META||{})[b.type]||{});return `<tr data-c="${b.code}" class="cursor-pointer">
    <td class="font-black">${b.code}</td><td>${b.d}</td><td>${b.D}</td><td>${b.B}</td>
    <td class="font-sans text-xs">${lang==="ar"?m.ar:m.en}</td>
    <td><button class="chip-btn" data-add="${b.code}">⚖</button></td></tr>`;}).join("");
  $("allBody").querySelectorAll("tr").forEach(tr=>tr.onclick=e=>{ if(e.target.dataset.add){addCompare(e.target.dataset.add);return;} setTab("A"); search.value=tr.dataset.c; showResult(tr.dataset.c,tr.dataset.c); window.scrollTo({top:0,behavior:"smooth"}); });
}
$("allQ").addEventListener("input",renderAll); $("allType").addEventListener("change",renderAll);

// ---------- Chips / suffixes ----------
function renderChips(){
  const pops=B().filter(b=>b.popular).slice(0,10);
  $("chips").innerHTML=pops.map(b=>`<button class="chip" data-c="${b.code}">${b.code}</button>`).join("");
  $("chips").querySelectorAll(".chip").forEach(c=>c.onclick=()=>{ setTab("A"); search.value=c.dataset.c; showResult(c.dataset.c,c.dataset.c); });
}
function renderSuffixes(){
  $("suffixGrid").innerHTML=(window.SUFFIXES||[]).map(s=>`<div class="mini-stat" style="align-items:flex-start"><b dir="ltr" class="text-amber-600">${s.s}</b><span class="text-start">${lang==="ar"?s.ar:s.en}</span></div>`).join("");
}

// ---------- Compare ----------
function addCompare(code){
  code=findBearing(code)?.code||code;
  if(compare.includes(code)){$("drawer").classList.remove("hidden");return;}
  if(compare.length>=3){toast(t("full"));return;}
  compare.push(code); localStorage.setItem("brg-cmp",JSON.stringify(compare));
  toast(t("added")); renderCompare();
}
function renderCompare(){
  $("fabN").textContent=compare.length; $("cmpCount").textContent=`(${compare.length}/3)`;
  $("cmpFab").classList.toggle("hidden",!compare.length);
  const g=$("cmpGrid");
  g.innerHTML=compare.length?compare.map(c=>{const b=findBearing(c); if(!b)return "";const m=((window.TYPE_META||{})[b.type]||{});
    return `<div class="cmp-cell"><div class="flex items-center gap-2"><b dir="ltr" class="font-mono text-lg">${b.code}</b>
    <button class="chip-btn ms-auto" data-rm="${b.code}">✕</button></div>
    <div dir="ltr" class="font-mono font-black text-amber-600 mt-1">d${b.d} × D${b.D} × B${b.B}</div>
    <div class="text-xs text-slate-500 mt-1">${lang==="ar"?m.ar:m.en}</div>
    <div class="text-xs mt-1">⚖ ≈ ${estWeight(b).toFixed(2)} kg</div>
    <button class="chip-btn mt-2" data-view="${b.code}">👁 ${lang==="ar"?"عرض":"view"}</button></div>`;}).join("")
    :`<div class="text-xs text-slate-500">${lang==="ar"?"اضغط ➕ على أي بلية لمقارنتها هنا":"Press ➕ on any bearing to compare"}</div>`;
  g.querySelectorAll("[data-rm]").forEach(x=>x.onclick=()=>{compare=compare.filter(c=>c!==x.dataset.rm);localStorage.setItem("brg-cmp",JSON.stringify(compare));renderCompare();});
  g.querySelectorAll("[data-view]").forEach(x=>x.onclick=()=>{setTab("A");search.value=x.dataset.view;showResult(x.dataset.view,x.dataset.view);});
}
$("cmpFab").onclick=()=>$("drawer").classList.toggle("hidden");
$("cmpClose").onclick=()=>$("drawer").classList.add("hidden");
$("cmpClear").onclick=()=>{compare=[];localStorage.setItem("brg-cmp","[]");renderCompare();};

// ---------- Tabs / lang / theme ----------
function setTab(which){
  ["A","B","All"].forEach(k=>$("tab"+k).classList.toggle("active",k===which));
  $("modeA").classList.toggle("hidden",which!=="A");
  $("modeB").classList.toggle("hidden",which!=="B");
  $("modeAll").classList.toggle("hidden",which!=="All");
}
$("tabA").onclick=()=>setTab("A"); $("tabB").onclick=()=>setTab("B"); $("tabAll").onclick=()=>setTab("All");
$("langBtn").onclick=()=>{lang=lang==="ar"?"en":"ar";localStorage.setItem("brg-lang",lang);applyLang();};
$("themeBtn").onclick=()=>{const cur=document.documentElement.classList.contains("dark")?"dark":"light";localStorage.setItem("brg-theme",cur==="dark"?"light":"dark");applyTheme();};

function toast(msg){ $("toastT").textContent=msg; const w=$("toast"); w.classList.remove("hidden"); w.classList.add("flex"); clearTimeout(w._h); w._h=setTimeout(()=>{w.classList.add("hidden");w.classList.remove("flex");},1600); }

// init
applyTheme(); applyLang(); renderCompare();
showResult("6204","6204");
