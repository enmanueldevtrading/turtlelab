PORT = 8080
TURTLE_JOBS = {}

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

PAGE = """<!DOCTYPE html><html lang='es'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>TurtleLab - Panel Offline</title>
<style>
:root{--bg:#0a0e1a;--bg2:#0f1424;--card:#141b2d;--card2:#1a2236;--line:#2a3550;--line2:#3a4560;--txt:#f0f4fa;--mut:#8b9bb5;--mut2:#6b7a95;--ok:#30d158;--bad:#ff453a;--acc:#0a84ff;--acc2:#5ac8fa;--warn:#ff9f0a;--radius:12px;--radius-sm:8px;--shadow:0 4px 24px rgba(0,0,0,.35);--shadow-sm:0 2px 8px rgba(0,0,0,.2);--font:-apple-system,BlinkMacSystemFont,'SF Pro Display','SF Pro Text','Helvetica Neue',Arial,sans-serif}
*{box-sizing:border-box;margin:0;padding:0}body{font-family:var(--font);background:var(--bg);color:var(--txt);font-size:14px;line-height:1.5;-webkit-font-smoothing:antialiased}
header{background:rgba(10,14,26,.85);backdrop-filter:blur(20px);border-bottom:1px solid var(--line);padding:12px 24px;display:flex;align-items:center;gap:16px;position:sticky;top:0;z-index:50}
header h1{margin:0;font-size:17px;font-weight:600;letter-spacing:-.3px}header .sub{color:var(--mut);font-size:12px}
nav{display:flex;gap:2px;margin-left:auto;background:var(--card);border-radius:10px;padding:3px;border:1px solid var(--line)}
nav button{background:transparent;border:0;color:var(--mut);padding:7px 14px;font-size:13px;font-weight:500;cursor:pointer;border-radius:7px;transition:all .2s ease}
nav button.on{background:var(--acc);color:#fff;font-weight:600;box-shadow:0 2px 8px rgba(10,132,255,.3)}
nav button:hover:not(.on){color:var(--txt);background:var(--card2)}
main{max-width:1280px;margin:0 auto;padding:24px 20px}.view{display:none}.view.on{display:block;animation:fadeIn .3s ease}
@keyframes fadeIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
.grid4{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:16px 0}
.stat{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:18px 16px;text-align:center;transition:transform .2s ease,box-shadow .2s ease}
.stat:hover{transform:translateY(-2px);box-shadow:var(--shadow-sm)}.stat b{font-size:28px;font-weight:700;display:block;letter-spacing:-.5px}
.stat span{color:var(--mut);font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:.5px}
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:20px;margin:16px 0;box-shadow:var(--shadow-sm)}
.card h2{margin:0 0 4px;font-size:17px;font-weight:600;letter-spacing:-.3px}.card p.d{color:var(--mut);font-size:13px;margin:4px 0 12px;line-height:1.5}
table{border-collapse:collapse;width:100%;font-size:13px}td,th{border-bottom:1px solid var(--line);padding:9px 10px;text-align:left;white-space:nowrap}
th{color:var(--mut);font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;padding:10px}tbody tr{transition:background .15s ease}tbody tr:hover td{background:var(--card2)}
.g{color:var(--ok);font-weight:600}.p{color:var(--bad);font-weight:600}
a{color:var(--acc);text-decoration:none;transition:color .15s}a:hover{color:var(--acc2);text-decoration:underline}
button.run{background:var(--ok);border:0;color:#052e16;font-weight:600;padding:10px 20px;border-radius:10px;font-size:14px;cursor:pointer;transition:all .2s ease;box-shadow:0 2px 12px rgba(48,209,88,.25)}
button.run:disabled{opacity:.4;cursor:wait;box-shadow:none}button.run:hover:not(:disabled){transform:translateY(-1px);box-shadow:0 4px 16px rgba(48,209,88,.35)}
button.run:active:not(:disabled){transform:none}
button.ghost{background:var(--card2);border:1px solid var(--line);color:var(--txt);padding:8px 14px;border-radius:10px;font-size:13px;font-weight:500;cursor:pointer;transition:all .2s ease}
button.ghost:hover{background:var(--line);border-color:var(--line2)}
select,input{background:var(--bg2);color:var(--txt);border:1px solid var(--line);border-radius:8px;padding:8px 12px;font-size:13px;transition:border-color .2s,box-shadow .2s;font-family:var(--font)}
select:focus,input:focus{outline:none;border-color:var(--acc);box-shadow:0 0 0 3px rgba(10,132,255,.15)}
.bar{height:8px;background:var(--bg2);border-radius:4px;overflow:hidden;margin-top:10px;border:1px solid var(--line)}
.bar i{display:block;height:100%;background:linear-gradient(90deg,var(--ok),var(--acc));width:0%;transition:width .4s ease;border-radius:4px}
.badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;letter-spacing:.3px}
.bG{background:rgba(48,209,88,.15);color:var(--ok)}.bP{background:rgba(255,69,58,.15);color:var(--bad)}
.toolbar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:12px 0}.mut{color:var(--mut);font-size:13px}
.strat{border:1px solid var(--line);border-radius:var(--radius);padding:18px;margin:12px 0;background:var(--card);transition:all .2s ease}
.strat:hover{border-color:var(--acc);box-shadow:0 4px 20px rgba(10,132,255,.08)}.strat h3{margin:0 0 6px;font-size:16px;font-weight:600;letter-spacing:-.2px}
.pills{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0}.pill{border:1px solid var(--line);background:var(--bg2);color:var(--txt);padding:6px 14px;border-radius:20px;cursor:pointer;font-size:12.5px;font-weight:500;transition:all .2s ease}
.pill.on{background:var(--acc);border-color:var(--acc);color:#fff;font-weight:600;box-shadow:0 2px 8px rgba(10,132,255,.3)}
.pill:hover:not(.on){background:var(--card2);border-color:var(--line2)}
.skel{border-radius:8px;background:linear-gradient(90deg,var(--card) 25%,var(--card2) 50%,var(--card) 75%);background-size:200% 100%;animation:sh 1.2s infinite;min-height:40px;margin:6px 0}
@keyframes sh{to{background-position:-200% 0}}
.kv{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin:12px 0}
.kv div{background:var(--bg2);border:1px solid var(--line);border-radius:var(--radius-sm);padding:12px;text-align:center;transition:transform .2s ease}
.kv div:hover{transform:translateY(-1px)}.kv b{display:block;font-size:18px;font-weight:700;letter-spacing:-.3px;margin-bottom:2px}
.kv span{color:var(--mut);font-size:11px;font-weight:500;text-transform:uppercase;letter-spacing:.4px}
.drawer{border:1px solid var(--acc);border-radius:var(--radius);padding:20px;margin-top:14px;background:var(--card);animation:fadeUp .35s ease;box-shadow:var(--shadow)}
@keyframes fadeUp{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
.params{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}.chip{background:var(--bg2);border:1px solid var(--line);color:var(--txt);border-radius:8px;padding:5px 12px;font-size:12px;font-weight:500}
.chip b{color:var(--acc);font-weight:600}
details.rules{margin:8px 0;border:1px dashed var(--line);border-radius:var(--radius-sm);padding:10px 14px}
details.rules summary{cursor:pointer;color:var(--acc);font-weight:600;font-size:13px;transition:color .15s}details.rules summary:hover{color:var(--acc2)}
details.rules ul{margin:8px 0 4px;padding-left:20px;color:var(--txt);font-size:13px}details.rules li{margin:4px 0;line-height:1.5}
select:focus,input:focus,button:focus-visible{outline:2px solid var(--acc);outline-offset:1px}
@media(max-width:768px){header{flex-wrap:wrap;padding:10px 16px}main{padding:16px 12px}.grid4{grid-template-columns:repeat(2,1fr)}nav{margin-left:0;width:100%;justify-content:center}}
.scrollx{overflow-x:auto;border-radius:var(--radius-sm)}footer{color:var(--mut);font-size:12px;text-align:center;padding:24px;border-top:1px solid var(--line);margin-top:24px}
.errbox{background:rgba(255,69,58,.1);border:1px solid var(--bad);border-radius:var(--radius-sm);padding:12px;margin:12px 0;color:var(--bad)}
</style></head><body>
<header><svg width='26' height='26' viewBox='0 0 24 24'><rect x='2' y='12' width='20' height='2' fill='#0a84ff'/><path d='M3 15l3-4 3 3 3-6 3 4 3-2 3 3' fill='none' stroke='#30d158' stroke-width='2'/></svg><h1>TurtleLab</h1><span class='sub'>Laboratorio cuantitativo - Indices sinteticos de Weltrade</span>
<nav><button data-v='datos'>Datos</button><button data-v='estrat' class='on'>Estrategias</button><button data-v='job'>Trabajo</button><button data-v='bts'>Pruebas</button><button data-v='mc'>Monte Carlo</button></nav></header>
<main>
<div id='errbox' style='display:none' class='errbox'></div>
<section id='v-datos' class='view'>
<div class='grid4'><div class='stat'><b id='sFiles'>-</b><span>archivos</span></div>
<div class='stat'><b id='sSym'>-</b><span>simbolos</span></div>
<div class='stat'><b id='sBt'>-</b><span>pruebas</span></div>
<div class='stat'><b id='sWin'>-</b><span>ganadores</span></div></div>
<p class='mut' id='sYahoo'>Cargando...</p>
<div class='card'><h2>Datos locales</h2><p class='d'>Weltrade sale de MT5 (indices sinteticos). Yahoo sale de Yahoo Finance. No se mezclan.</p>
<div class='toolbar'><button class='pill on' id='pillW'>Weltrade</button><button class='pill' id='pillY'>Yahoo</button><input id='qSym' placeholder='Filtrar simbodo...' oninput='drawInv()'></div>
<div class='scrollx' id='invBox'><div class='skel'></div><div class='skel'></div></div></div>
</section>
<section id='v-estrat' class='view on'>
<div class='card'><h2>Estrategias registradas</h2><p class='d'>Anadir una estrategia nueva = registrarla en el motor. Sin tocar el panel.</p><div id='stratBox'><div class='skel'></div></div></div>
</section>
<section id='v-job' class='view'>
<div class='card'><h2>Trabajo en curso</h2><div class='bar'><i id='pbar'></i></div>
<div id='job' class='mut' style='margin-top:6px'>Sin trabajo en curso.</div>
<div style='margin-top:8px'><button class='ghost' id='btnCancel' style='display:none' onclick='cancelJob()'>Cancelar trabajo</button></div>
<div class='scrollx' id='jobRes' style='margin-top:8px'></div></div>
</section>
<section id='v-bts' class='view'>
<div class='card'><h2>Pruebas guardadas</h2>
<div class='toolbar'>
<input id='qAll' placeholder='Buscar: simbodo, estrategia, ID o temporalidad...' style='flex:1;min-width:220px'>
<select id='fStrat'><option value=''>Todas las estrategias</option></select>
<select id='fRes'><option value=''>Todos</option><option value='G'>Ganadores</option><option value='P'>Perdedores</option></select>
<button class='ghost' id='btnCsv'>Exportar CSV</button>
<button class='ghost' id='btnDel'>Eliminar todo</button>
</div>
<p class='mut'>Toca un encabezado para ordenar. Filtros en vivo.</p>
<div class='scrollx' id='resBox'><div class='skel'></div></div>
<div id='detail'></div></div>
</section>
<section id='v-mc' class='view'>
<div class='card'><h2>Monte Carlo (estadistica sobre operaciones reales)</h2>
<p class='d'>No genera senales. Reordena tus operaciones con semilla reproducible y mide robustez.</p>
<div class='toolbar'>
<select id='mcBt'></select>
<select id='mcSims'><option>100</option><option selected>500</option><option>1000</option><option>5000</option></select>
<input id='mcSeed' value='12345' size='8' title='Semilla'>
<button class='run' id='btnMc'>Ejecutar Monte Carlo</button>
</div>
<div id='mcOut' class='mut'>Sin resultados aun.</div></div>
</section>
</main>
<footer>TurtleLab - cada backtest guarda ID + config + trades + metricas en results/</footer>
<script>
let ALL=[], INV=[], META={}, JOB=null;
document.querySelectorAll('nav button').forEach(b=>b.onclick=()=>{
  document.querySelectorAll('nav button').forEach(x=>x.classList.remove('on')); b.classList.add('on');
  document.querySelectorAll('.view').forEach(v=>v.classList.remove('on'));
  document.getElementById('v-'+b.dataset.v).classList.add('on');});
async function api(p,opt){ const r=await fetch(p,opt); if(!r.ok) throw new Error('HTTP '+r.status+' en '+p); return r.json(); }
function showErr(m){ const e=document.getElementById('errbox'); e.style.display='block'; e.innerHTML='<b>Error:</b> '+m; }
function clearErr(){ const e=document.getElementById('errbox'); e.style.display='none'; e.innerHTML=''; }
async function fetchT(url,seg){
  const c=new AbortController(); const t=setTimeout(()=>c.abort(),(seg||30)*1000);
  try{ const r=await fetch(url,{signal:c.signal}); if(!r.ok) throw new Error('HTTP '+r.status); return await r.json(); }
  finally{ clearTimeout(t); }
}
async function boot(){
  clearErr();
  try{
    const s=await fetchT('/api/status',30); ALL=s.results;
    document.getElementById('sFiles').textContent=s.files;
    document.getElementById('sSym').textContent=s.symbols;
    META=await fetchT('/api/strategies',15);
    window.LBL={};
    Object.keys(META).forEach(mode=>{(META[mode].variants||[]).forEach(v=>{window.LBL[v[0]]=META[mode].label;});});
    document.getElementById('sBt').textContent=ALL.length;
    document.getElementById('sWin').textContent=ALL.filter(r=>r.net>=0).length;
    if(s.sources&&s.sources.yahoo) document.getElementById('sYahoo').textContent='Yahoo: '+s.sources.yahoo.files+' archivos ('+s.sources.yahoo.symbols+' simbolos) - Weltrade: '+s.files+' archivos ('+s.symbols+' simbolos)';
    drawStrats(); drawTable(); fillMc();
    window.SRC='weltrade';
    try{ const iv=await fetchT('/api/inventory?src=weltrade',60); INV=iv.inventory||[]; }catch(e){ INV=[]; }
    drawInv();
    document.getElementById('pillW').onclick=()=>setSrc('weltrade');
    document.getElementById('pillY').onclick=()=>setSrc('yahoo');
    try{ const a=await api('/api/active'); if(a.running){ JOB=a.running.job_id; setRunButtons(true); pollJob(); } }catch(e){}
  }catch(e){
    if(String(e && e.name)==='AbortError') showErr('El servidor tarda demasiado. Espera y recarga.');
    else showErr('No se pudo cargar: '+e.message);
  }
}
async function setSrc(s){
  window.SRC=s;
  document.getElementById('pillW').classList.toggle('on',s==='weltrade');
  document.getElementById('pillY').classList.toggle('on',s==='yahoo');
  document.getElementById('invBox').innerHTML='<p class=mut>Cargando...</p>';
  try{ const iv=await fetchT('/api/inventory?src='+s,60); INV=iv.inventory||[]; }catch(e){ INV=[]; }
  drawInv();
}
function drawInv(){
  const q=(document.getElementById('qSym').value||'').toLowerCase();
  const rows=INV.filter(r=>!q||r.symbol.toLowerCase().includes(q));
  let h="<table><tr><th>Simbodo</th><th>TF</th><th>Velas</th><th>Desde</th><th>Hasta</th></tr>";
  for(const r of rows.slice(0,400)) h+="<tr><td>"+r.symbol+"</td><td>"+r.timeframe+"</td><td>"+r.rows+"</td><td>"+(r.from||'').slice(0,16)+"</td><td>"+(r.to||'').slice(0,16)+"</td></tr>";
  document.getElementById('invBox').innerHTML=h+"</table><p class=mut>"+rows.length+" registros.</p>";
}
function drawStrats(){
  const box=document.getElementById('stratBox'); box.innerHTML='';
  Object.keys(META).forEach(k=>{
    const m=META[k], d=document.createElement('div'); d.className='strat';
    const names={entry:'Entrada',exit:'Salida',atr_period:'ATR',sl_mult:'Tope xATR',fast:'Rapida',slow:'Lenta',entry_fast:'Entrada',mid:'Media',sessions:'Sesiones',ema:'EMA salida'};
    const chips=Object.entries(m.params||{}).map(([k,v])=>{const val=Array.isArray(v)?v.map(x=>Array.isArray(x)?x.join('-'):x).join(' + '):v;return "<span class='chip'>"+(names[k]||k)+": <b>"+val+"</b></span>";}).join('')+"<span class='chip'>"+(m.riesgo||'')+"</span><span class='chip'>1 posicion</span>";
    d.innerHTML="<h3>"+m.label+"</h3><div class='params'>"+chips+"</div><p class='d'>"+m.desc+"</p><details class='rules'><summary>Ver reglas exactas</summary><ul>"+(m.rules||[]).map(r=>"<li>"+r+"</li>").join('')+"</ul></details><p class='d'>Corre en <b>todos los simbodos x estas temporalidades: "+(m.tfs||[]).join(', ')+"</b>, de uno en uno.</p><p class='d'>Weltrade: spread y lote minimo/maximo reales de MT5. Yahoo: sin spread ni minimos. Comision 0.</p><div class='toolbar'><select id='src-"+k+"'><option value='weltrade'>Weltrade (Indices)</option><option value='yahoo'>Yahoo (forex/oro/BTC)</option></select><select id='cap-"+k+"'><option value='10'>Capital $10</option><option value='20'>Capital $20</option><option value='50' selected>Capital $50</option></select><button class='run' id='go-"+k+"'>Correr en todo</button></div><div class='mut' id='st-"+k+"'></div>";
    box.appendChild(d);
    d.querySelector('#go-'+k).onclick=()=>runJob(k);
  });
}
function setRunButtons(off){ document.querySelectorAll('#stratBox .run').forEach(b=>b.disabled=off); }
function goView(v){ document.querySelectorAll('nav button').forEach(x=>x.classList.remove('on')); const b=document.querySelector("nav button[data-v='"+v+"']"); if(b) b.classList.add('on'); document.querySelectorAll('.view').forEach(x=>x.classList.remove('on')); document.getElementById('v-'+v).classList.add('on'); }
function elapsed(s){ if(!s) return ''; const m=Math.floor((Date.now()/1000-s)/60); return m<1?'menos de 1 min':m+' min'; }
async function runJob(mode){
  clearErr();
  try{
    const cap=document.querySelector('#cap-'+mode).value;
    const src=document.querySelector('#src-'+mode).value;
    setRunButtons(true);
    document.getElementById('job').textContent='Iniciando trabajo...';
    const r=await api('/api/run-turtle?tf=ALL&mode='+mode+'&balance='+cap+'&src='+src,{method:'POST'});
    JOB=r.job_id; goView('job'); pollJob();
  }catch(e){ setRunButtons(false); showErr('No se pudo iniciar: '+e.message); }
}
async function pollJob(){
  try{
    const j=await api('/api/job/'+JOB);
    const pc=j.total?Math.round(j.done/j.total*100):0;
    document.getElementById('pbar').style.width=pc+'%';
    const eta=(function(){ if(!j.started||!j.done||!j.total) return ''; const el=Date.now()/1000-j.started; const rest=el/j.done*(j.total-j.done); const m=Math.round(rest/60); return m<1?' - faltan segundos':' - faltan ~'+m+' min'; })();
    document.getElementById('job').textContent='CORRIENDO - '+j.done+'/'+j.total+' ('+pc+'%) - '+j.status+(j.current?' - procesando: '+j.current:'')+eta;
    const ok=j.results.filter(x=>!x.error&&x.net>=0).length;
    let h="<table><tr><th>Simbodo</th><th>TF</th><th>Estrategia</th><th>Neto $</th><th>PF</th><th>DD%</th></tr>";
    for(const x of j.results.slice(-12).reverse()){
      if(x.error) h+="<tr><td>"+x.symbol+"</td><td colspan='5' class='p'>"+x.error+"</td></tr>";
      else if(x.note) h+="<tr><td>"+x.symbol+"</td><td>"+x.tf+"</td><td>"+(window.LBL[x.strategy]||x.strategy)+"</td><td colspan='3' class='mut'>Sin operaciones</td></tr>";
      else h+="<tr><td>"+x.symbol+"</td><td>"+x.tf+"</td><td>"+(window.LBL[x.strategy]||x.strategy)+"</td><td class='"+(x.net>=0?'g':'p')+"'>"+x.net+"</td><td>"+x.pf+"</td><td>"+x.dd+"</td></tr>";
    }
    document.getElementById('jobRes').innerHTML=h+"</table><p class='mut'>"+ok+" ganadores en este trabajo.</p>";
    document.getElementById('btnCancel').style.display = (j.status==='corriendo') ? '' : 'none';
    if(j.status==='terminado'){ setRunButtons(false); document.getElementById('pbar').style.width='100%'; boot(); }
    else if(j.status==='cancelado'){ setRunButtons(false); document.getElementById('job').textContent+=' - cancelado.'; boot(); }
    else if(j.status.startsWith('error')){ setRunButtons(false); showErr('El trabajo fallo: '+j.status); boot(); }
    else setTimeout(pollJob,3000);
  }catch(e){ showErr('Se perdio contacto: '+e.message); setTimeout(pollJob,8000); }
}
function lbl(k){ return (window.LBL&&window.LBL[k])||k; }
async function cancelJob(){
  if(!JOB) return;
  try{ const r=await api('/api/job/'+JOB+'/cancel',{method:'POST'}); document.getElementById('job').textContent='Cancelando '+r.job_id+'...'; }catch(e){ showErr('No se pudo cancelar: '+e.message); }
}
let SORTK='net', SORTD=-1;
function drawTable(){
  const fs=document.getElementById('fStrat'), curS=fs.value;
  fs.innerHTML='<option value="">Todas las estrategias</option>'+[...new Set(ALL.map(r=>r.strategy))].map(x=>'<option value="'+x+'">'+lbl(x)+'</option>').join('');
  if(curS) fs.value=curS;
  const fR=document.getElementById('fRes').value;
  const q=(document.getElementById('qAll').value||'').toLowerCase();
  let rows=ALL.filter(r=>{
    if(fs.value&&r.strategy!==fs.value) return false;
    if(fR&&(fR==='G'?r.net<0:r.net>=0)) return false;
    if(q){ const hay=(r.bt_id+' '+lbl(r.strategy)+' '+r.strategy+' '+r.symbol+' '+r.timeframe+' '+(r.src||'')).toLowerCase(); if(!hay.includes(q)) return false; }
    return true;
  });
  const isNum=k=>(k==='net'||k==='pf'||k==='dd'||k==='trades'||k==='wr');
  const getV=k=>isNum(k)?(x=>(+x[k]||0)):(x=>((x[k]||'').toString()));
  rows=rows.slice().sort((a,b)=>{ const va=getV(a), vb=getV(b); return (va>vb?1:va<vb?-1:0)*SORTD; });
  window._rows=rows;
  if(!ALL.length){ document.getElementById('resBox').innerHTML="<p class='mut'>Sin pruebas aun. Corre una estrategia.</p>"; return; }
  if(!rows.length){ document.getElementById('resBox').innerHTML="<p class='mut'>Sin resultados para esos filtros.</p>"; return; }
  const TH=(k,t)=>"<th onclick=\"sortBy('"+k+"')\" style='cursor:pointer'>"+t+(SORTK===k?(SORTD>0?' ^':' v'):'')+"</th>";
  let h="<table><tr><th>ID</th>"+TH('strategy','Estrategia')+TH('symbol','Simbodo')+TH('src','Fuente')+TH('timeframe','TF')+"<th>Capital</th>"+TH('net','Neto $')+TH('pf','PF')+TH('dd','DD%')+TH('trades','Ops')+TH('wr','WR%')+"<th></th></tr>";
  for(const r of rows.slice(0,150)){
    const c=r.net>=0?'g':'p';
    h+="<tr><td>"+r.bt_id+"</td><td>"+lbl(r.strategy)+"</td><td>"+r.symbol+"</td><td>"+(r.src==='yahoo'?'Yahoo':'Weltrade')+"</td><td>"+r.timeframe+"</td><td>$"+r.capital+"</td><td class='"+c+"'>"+r.net+"</td><td>"+r.pf+"</td><td>"+r.dd+"%</td><td>"+r.trades+"</td><td>"+r.wr+"%</td><td><button class='ghost' onclick=\"detail('"+r.bt_id+"')\">Detalle</button></td></tr>";
  }
  document.getElementById('resBox').innerHTML=h+"</table><p class='mut'>Mostrando "+Math.min(150,rows.length)+" de "+rows.length+".</p>";
}
function sortBy(k){ if(SORTK===k){SORTD*=-1;}else{SORTK=k;SORTD=-1;} drawTable(); }
['qAll','fStrat','fRes'].forEach(id=>{const el=document.getElementById(id); if(el) el.addEventListener('input',drawTable);});
document.getElementById('btnCsv').onclick=()=>{
  const rows=window._rows||[];
  if(!rows.length){ showErr('No hay filas.'); return; }
  const cols=['bt_id','strategy','symbol','timeframe','capital','net','pf','dd','trades','wr'];
  const csv=[cols.join(';')].concat(rows.map(r=>cols.map(c=>r[c]).join(';'))).join('\\n');
  const a=document.createElement('a'); a.href=URL.createObjectURL(new Blob(["\\ufeff"+csv],{type:'text/csv'})); a.download='turtlelab_resultados.csv'; a.click();
};
document.getElementById('btnDel').onclick=async ()=>{
  if(!ALL.length){ showErr('No hay pruebas.'); return; }
  if(!confirm('Eliminar las '+ALL.length+' pruebas? No se puede deshacer.')) return;
  clearErr();
  try{ const r=await api('/api/results/delete',{method:'POST'}); document.getElementById('resBox').innerHTML="<p class='mut'>Eliminadas "+r.deleted+" pruebas.</p>"; boot(); }catch(e){ showErr(e.message); }
};
async function detail(bt){
  clearErr();
  try{
    const d=await api('/api/backtest/'+bt); const m=d.metrics;
    const kv=(k,v)=>"<div><b>"+v+"</b><span>"+k+"</span></div>";
    let h="<div class='drawer'><h3>"+bt+" - "+lbl(d.config.strategy)+" - "+d.config.symbol+" "+d.config.timeframe+"</h3>";
    h+="<img src='/api/equity/"+bt+".svg' style='max-width:100%;border-radius:8px;margin:10px 0'>";
    h+="<div class='kv'>"+kv('Neto $',m.net_profit)+kv('PF',m.profit_factor)+kv('DD $',m.max_drawdown)+kv('DD %',m.max_drawdown_pct)+kv('Ops',m.total)+kv('WR %',m.win_rate)+"</div>";
    h+="<div class='scrollx'><table><tr><th>#</th><th>Dir</th><th>Entrada</th><th>Salida</th><th>Lote</th><th>PnL $</th><th>Motivo</th></tr>";
    d.trades.slice(0,100).forEach((t,ix)=>{ h+="<tr><td>"+(ix+1)+"</td><td>"+t.direction+"</td><td>"+(t.ts_entry||'').slice(0,16)+" @ "+t.entry+"</td><td>"+(t.ts_exit||'').slice(0,16)+" @ "+t.exit+"</td><td>"+t.qty+"</td><td class='"+(t.pnl>=0?'g':'p')+"'>"+t.pnl+"</td><td>"+t.reason+"</td></tr>"; });
    document.getElementById('detail').innerHTML=h+"</table></div><p class='mut'>Mostrando "+Math.min(100,d.trades.length)+" de "+d.trades.length+" ops.</p></div>";
    document.getElementById('detail').scrollIntoView();
  }catch(e){ showErr('No se pudo abrir: '+e.message); }
}
function fillMc(){
  const sel=document.getElementById('mcBt');
  sel.innerHTML=ALL.map(r=>"<option value='"+r.bt_id+"'>"+r.bt_id+" - "+lbl(r.strategy)+" "+r.symbol+" "+r.timeframe+"</option>").join('');
  if(!ALL.length) sel.innerHTML="<option value=''>Sin pruebas</option>";
}
document.getElementById('btnMc').onclick=async ()=>{
  clearErr();
  const bt=document.getElementById('mcBt').value;
  if(!bt){ showErr('No hay pruebas.'); return; }
  const sims=document.getElementById('mcSims').value, seed=document.getElementById('mcSeed').value;
  document.getElementById('mcOut').innerHTML='<div class="skel"></div>';
  try{
    const mc=await api('/api/montecarlo',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({bt_id:bt,sims:+sims,seed:+seed})});
    const P=mc.percentiles||{};
    const row=(k,label)=>{const o=P[k]||{};return "<tr><td>"+label+"</td><td>"+o.P5+"</td><td>"+o.P25+"</td><td>"+o.P50+"</td><td>"+o.P75+"</td><td>"+o.P95+"</td></tr>";};
    document.getElementById('mcOut').innerHTML="<div class='kv'><div><b>"+(mc.p_profit*100).toFixed(1)+"%</b><span>prob. beneficio</span></div><div><b>"+(mc.p_loss*100).toFixed(1)+"%</b><span>prob. perdida</span></div><div><b>"+(mc.p_dd20*100).toFixed(1)+"%</b><span>prob. DD>20%</span></div><div><b>"+mc.final_balance.median+"</b><span>balance mediano</span></div></div><table><tr><th>Metrica</th><th>P5</th><th>P25</th><th>P50</th><th>P75</th><th>P95</th></tr>"+row('net_profit','Neto $')+row('max_drawdown_pct','DD max %')+row('profit_factor','PF')+"</table><p class='mut'>"+mc.n_sims+" sims - semilla "+mc.seed+" - "+mc.method+"</p>";
  }catch(e){ document.getElementById('mcOut').innerHTML=''; showErr('Monte Carlo fallo: '+e.message); }
};
boot();
</script></body></html>"""

ICONS = {}

def quick_counts(root="data/weltrade"):
    files, syms = 0, set()
    try:
        for sym in os.listdir(root):
            d = os.path.join(root, sym)
            if not os.path.isdir(d):
                continue
            syms.add(sym)
            for f in os.listdir(d):
                if f.endswith(".csv.gz"):
                    files += 1
    except Exception:
        pass
    return files, syms

def find_live_panel(ports=(8080, 8081, 8082, 8090)):
    import urllib.request
    import json as _json
    for cand in ports:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{cand}/api/status", timeout=2) as r:
                data = _json.loads(r.read().decode())
                if isinstance(data, dict) and "files" in data and "results" in data:
                    return cand
        except Exception:
            continue
    return None

def low_priority():
    try:
        import ctypes
        BELOW_NORMAL = 0x00004000
        ctypes.windll.kernel32.SetPriorityClass(
            ctypes.windll.kernel32.GetCurrentProcess(), BELOW_NORMAL)
    except Exception:
        pass

_RESULTS_CACHE = {"data": None, "expires": 0}

def _guess_src(symbol, tf):
    import os
    for root in ("data/weltrade", "data/yahoo"):
        if os.path.exists(os.path.join(root, symbol or "", (tf or "") + ".csv.gz")):
            return "yahoo" if "yahoo" in root else "weltrade"
    return "weltrade"


_RESULTS_INDEX_FILE = os.path.join("results", "_index.json")

def _rebuild_results_index():
    """Reconstruye el indice de resultados desde disco (lento, solo si es necesario)."""
    out = []
    root = "results"
    if not os.path.isdir(root):
        return out
    for d in sorted(os.listdir(root)):
        p = os.path.join(root, d)
        if not (d.startswith("BT-") and os.path.isdir(p)):
            continue
        try:
            cfg = json.load(open(os.path.join(p, "config.json"), encoding="utf-8"))
            met = json.load(open(os.path.join(p, "metrics.json"), encoding="utf-8"))
            out.append({"bt_id": d, "src": _guess_src(cfg.get("symbol"), cfg.get("timeframe")),
                        "strategy": cfg.get("strategy"),
                        "symbol": cfg.get("symbol"), "timeframe": cfg.get("timeframe"),
                        "net": met.get("net_profit"), "pf": met.get("profit_factor"),
                        "dd": met.get("max_drawdown_pct"), "dd_cap": met.get("max_drawdown"),
                        "trades": met.get("total"), "wr": met.get("win_rate"),
                        "capital": met.get("capital"), "from": cfg.get("from"),
                        "to": cfg.get("to"),
                        "mws": met.get("max_win_streak"), "mws_amt": met.get("max_win_streak_amt"),
                        "mls": met.get("max_loss_streak"), "mls_amt": met.get("max_loss_streak_amt")})
        except Exception:
            continue
    # Guardar indice en disco para carga rapida la proxima vez
    try:
        os.makedirs(os.path.dirname(_RESULTS_INDEX_FILE), exist_ok=True)
        tmp = _RESULTS_INDEX_FILE + ".tmp"
        json.dump(out, open(tmp, "w", encoding="utf-8"), default=str)
        os.replace(tmp, _RESULTS_INDEX_FILE)
    except Exception:
        pass
    return out

def list_results(force=False):
    import time as _t
    now = _t.time()
    # 1. Cache en memoria (TTL 5 min)
    if not force and _RESULTS_CACHE["data"] is not None and now < _RESULTS_CACHE["expires"]:
        return _RESULTS_CACHE["data"]
    # 2. Indice persistente en disco (carga instantanea)
    if not force and os.path.exists(_RESULTS_INDEX_FILE):
        try:
            # Verificar si el indice esta actualizado (comparar mtime del directorio results)
            idx_mtime = os.path.getmtime(_RESULTS_INDEX_FILE)
            dir_mtime = os.path.getmtime("results")
            if idx_mtime >= dir_mtime:
                data = json.load(open(_RESULTS_INDEX_FILE, encoding="utf-8"))
                _RESULTS_CACHE["data"] = data
                _RESULTS_CACHE["expires"] = now + 300
                return data
        except Exception:
            pass
    # 3. Reconstruir indice (lento, solo si no hay cache ni indice valido)
    data = _rebuild_results_index()
    _RESULTS_CACHE["data"] = data
    _RESULTS_CACHE["expires"] = now + 300
    return data


def run_turtle_job(job_id, symbols, tfs, balance=0, mode="turtle", root="data/weltrade"):
    from bt.data_manager import load_bars, symbol_info, contract_size
    from bt.execution import ExecConfig
    from bt.backtest import run_backtest
    from bt.reports import save_report
    import hashlib, pandas as pd, gc, traceback
    job = TURTLE_JOBS[job_id]
    from bt.strategies import STRATEGY_META
    meta = STRATEGY_META.get(mode, list(STRATEGY_META.values())[0])
    variants = meta["variants"]
    if not balance:
        balance = meta["balance"]
    allowed = meta.get("tfs") or tfs
    tfs = [t for t in tfs if t in allowed]
    jobs_list = [(s, tf, vk, vp) for s in symbols for tf in tfs for vk, vp in variants]
    srcname = "yahoo" if str(root).endswith("yahoo") else "weltrade"
    job["total"] = len(jobs_list)
    try:
        for s, tf, vk, vp in jobs_list:
            if job.get("status") == "cancelado":
                break
            job["current"] = "%s %s %s" % (s, tf, vk)
            try:
                df = load_bars(s, tf, root)
            except Exception as e:
                job["results"].append({"symbol": s, "tf": tf, "strategy": vk, "src": srcname, "error": str(e)[:100]})
                job["done"] += 1
                continue
            try:
                dh = hashlib.sha256(pd.util.hash_pandas_object(df, index=False).values.tobytes()).hexdigest()[:16]
                info = symbol_info(s, root)
                _spr = info.get("point_price", 0.0) or 0.0
                cfg = ExecConfig(initial_balance=balance, risk_pct=1.0,
                                 min_lot=info.get("volume_min", 0.01) or 0.01,
                                 max_lot=info.get("volume_max", 100.0) or 100.0,
                                 lot_step=info.get("volume_step", 0.01) or 0.01,
                                 contract_size=contract_size(info),
                                 spread=_spr, slippage=_spr / 2.0)
                r = run_backtest(df, vk, vp, cfg, s, tf, dh, save=True)
                if r.get("empty"):
                    job["results"].append({"symbol": s, "tf": tf, "strategy": vk, "src": srcname, "note": "sin operaciones"})
                else:
                    save_report(r, os.path.join("results", r["bt_id"]))
                    m = r["metrics"]
                    job["results"].append({"symbol": s, "tf": tf, "strategy": vk, "src": srcname,
                                           "bt_id": r["bt_id"], "net": m["net_profit"],
                                           "pf": m["profit_factor"], "dd": m["max_drawdown_pct"],
                                           "trades": m["total"]})
            except Exception as e:
                job["results"].append({"symbol": s, "tf": tf, "strategy": vk, "src": srcname, "error": str(e)[:150]})
            finally:
                df = None
                gc.collect()
            job["done"] += 1
            if len(job["results"]) > 300:
                job["results"] = job["results"][-300:]
    except Exception as e:
        job["status"] = "error: " + str(e)[:200]
        traceback.print_exc()
        return
    job["status"] = "terminado"
    try:
        _RESULTS_CACHE["data"] = None
        _RESULTS_CACHE["expires"] = 0
        if os.path.exists(_RESULTS_INDEX_FILE):
            os.remove(_RESULTS_INDEX_FILE)
    except Exception:
        pass

def inventory(root="data/weltrade"):
    from bt.data_manager import inventory as inv
    try:
        return inv(root=root)
    except Exception:
        return []

def strat_meta():
    from bt.strategies import STRATEGY_META
    return STRATEGY_META

class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        b = json.dumps(obj, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path in ("/", "/index.html"):
            b = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
        elif u.path == "/api/status":
            files, syms = quick_counts()
            yfiles, ysyms = quick_counts(root="data/yahoo")
            self._json({"files": files, "symbols": syms,
                        "results": list_results(),
                        "sources": {"weltrade": {"files": files, "symbols": syms},
                                    "yahoo": {"files": yfiles, "symbols": ysyms}}})
        elif u.path == "/api/inventory":
            from urllib.parse import parse_qs as _pq
            _src = (_pq(urlparse(self.path).query).get("src", ["weltrade"])[0] or "weltrade")
            _root = "data/yahoo" if _src == "yahoo" else "data/weltrade"
            self._json({"inventory": inventory(root=_root), "src": _src})
        elif u.path == "/api/strategies":
            from bt.strategies import get_strategy
            out = {}
            for mode, m in strat_meta().items():
                try:
                    _s, defaults = get_strategy(m["variants"][0][0])
                    params = {**defaults, **m["variants"][0][1]}
                except Exception:
                    params = {}
                out[mode] = {**m, "params": params}
            self._json(out)
        elif u.path.startswith("/api/job/"):
            jid = u.path.split("/")[-1]
            j = TURTLE_JOBS.get(jid, {"status": "no existe"})
            self._json({"job_id": jid, "status": j["status"], "done": j.get("done", 0),
                        "total": j.get("total", 0), "results": j.get("results", [])[-20:],
                        "mode": j.get("mode"), "tfs": j.get("tfs"), "balance": j.get("balance"),
                        "started": j.get("started"), "current": j.get("current", ""),
                        "src": j.get("src", "weltrade")})
        elif u.path == "/api/active":
            running = None
            for _jid, _j in TURTLE_JOBS.items():
                if _j.get("status") == "corriendo":
                    running = {"job_id": _jid, "done": _j.get("done", 0),
                               "total": _j.get("total", 0), "mode": _j.get("mode"),
                               "tfs": _j.get("tfs"), "balance": _j.get("balance"),
                               "started": _j.get("started"),
                               "src": _j.get("src", "weltrade")}
            self._json({"running": running})
        elif u.path.startswith("/api/backtest/"):
            bt = u.path.split("/")[-1]
            try:
                cfg = json.load(open(os.path.join("results", bt, "config.json"), encoding="utf-8"))
                met = json.load(open(os.path.join("results", bt, "metrics.json"), encoding="utf-8"))
                import pandas as pd
                tr = pd.read_csv(os.path.join("results", bt, "trades.csv")).head(500).to_dict("records")
                eq = pd.read_csv(os.path.join("results", bt, "equity.csv"))["equity"].to_numpy(float)
                if len(eq) > 600:
                    eq = eq[:: max(1, len(eq) // 600)]
                self._json({"bt_id": bt, "config": cfg, "metrics": met, "trades": tr,
                            "equity": [round(float(x), 2) for x in eq]})
            except Exception as e:
                self._json({"error": str(e)[:150]}, 404)
        elif u.path.startswith("/api/equity/") and u.path.endswith(".svg"):
            bt = u.path.split("/")[-1][:-4]
            svg = equity_svg(bt)
            if not svg:
                self.send_response(404); self.end_headers(); return
            b = svg.encode()
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
        elif u.path.startswith("/results/"):
            p = os.path.normpath(u.path.lstrip("/"))
            if ".." in p or not os.path.exists(p):
                self.send_response(404); self.end_headers(); return
            ctype = "text/html"
            if p.endswith(".json"):
                ctype = "application/json"
            elif p.endswith(".csv"):
                ctype = "text/csv"
            b = open(p, "rb").read()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
        else:
            self.send_response(404); self.end_headers()

    def do_POST(self):
        u = urlparse(self.path)
        if u.path == "/api/run-turtle":
            import time
            from urllib.parse import parse_qs
            q = parse_qs(urlparse(self.path).query)
            tf = (q.get("tf", ["ALL"])[0] or "ALL").upper()
            mode = (q.get("mode", ["turtle"])[0] or "turtle").lower()
            src = (q.get("src", ["weltrade"])[0] or "weltrade").lower()
            root = "data/yahoo" if src == "yahoo" else "data/weltrade"
            from bt.data_manager import inventory as inv
            _inv = inv(root=root)
            if tf == "ALL":
                tfs = sorted(set(i["timeframe"] for i in _inv),
                             key=["M1", "M3", "M5", "M15", "M30", "H1", "H4", "D1"].index)
            else:
                tfs = [tf]
            try:
                bal = float(q.get("balance", [0])[0] or 0)
            except Exception:
                bal = 0
            syms = sorted(set(i["symbol"] for i in _inv))
            for _jid, _j in TURTLE_JOBS.items():
                if _j.get("status") == "corriendo":
                    self._json({"error": "Ya hay un trabajo corriendo (" + _jid + "). Espera a que termine."}, 409)
                    return
            jid = f"job-{int(time.time())}"
            TURTLE_JOBS[jid] = {"status": "corriendo", "done": 0, "total": 0, "results": [],
                                "mode": mode, "tfs": tfs, "balance": bal, "src": src,
                                "started": int(time.time())}
            th = threading.Thread(target=run_turtle_job,
                                  args=(jid, syms, tfs, bal, mode, root), daemon=True)
            th.start()
            self._json({"job_id": jid})
        elif u.path == "/api/results/delete":
            import shutil
            for _jid, _j in TURTLE_JOBS.items():
                if _j.get("status") == "corriendo":
                    self._json({"error": "Hay un trabajo corriendo. Cancelalo primero."}, 409)
                    break
            else:
                n = 0
                for d in os.listdir("results"):
                    p = os.path.join("results", d)
                    if d.startswith("BT-") and os.path.isdir(p):
                        shutil.rmtree(p, ignore_errors=True)
                        n += 1
                try:
                    open(os.path.join("results", "_counter.txt"), "w").write("0")
                except Exception:
                    pass
                _RESULTS_CACHE["data"] = None
                _RESULTS_CACHE["expires"] = 0
                self._json({"deleted": n})
        elif u.path == "/api/rerun":
            from urllib.parse import parse_qs
            from bt.execution import ExecConfig
            from bt.backtest import run_backtest
            from bt.reports import save_report
            from bt.data_manager import load_bars
            import hashlib
            import pandas as pd
            q = parse_qs(urlparse(self.path).query)
            src = (q.get("bt", [""])[0] or "")
            try:
                cfg = json.load(open(os.path.join("results", src, "config.json"), encoding="utf-8"))
                df = load_bars(cfg["symbol"], cfg["timeframe"])
                e = cfg.get("exec", {})
                exc = ExecConfig(initial_balance=e.get("initial_balance", 50.0),
                                 lot=e.get("lot", 0.0), risk_pct=e.get("risk_pct", 1.0),
                                 min_lot=e.get("min_lot", 0.01), max_lot=e.get("max_lot", 100.0),
                                 lot_step=e.get("lot_step", 0.01),
                                 contract_size=e.get("contract_size", 1.0),
                                 spread=e.get("spread", 0.0), commission=e.get("commission", 0.0),
                                 slippage=e.get("slippage", 0.0),
                                 max_positions=e.get("max_positions", 1),
                                 allow_long=e.get("allow_long", True),
                                 allow_short=e.get("allow_short", True),
                                 entry_mode=e.get("entry_mode", "close"))
                dh = hashlib.sha256(pd.util.hash_pandas_object(df, index=False).values.tobytes()).hexdigest()[:16]
                r = run_backtest(df, cfg["strategy"], cfg.get("params", {}), exc,
                                 cfg["symbol"], cfg["timeframe"], dh, save=True)
                if r.get("empty"):
                    self._json({"empty": True, "src": src})
                else:
                    save_report(r, os.path.join("results", r["bt_id"]))
                    _RESULTS_CACHE["data"] = None
                    _RESULTS_CACHE["expires"] = 0
                    self._json({"bt_id": r["bt_id"], "src": src,
                                "net": r["metrics"]["net_profit"]})
            except Exception as ex:
                self._json({"error": str(ex)[:200]}, 404)
        elif u.path.startswith("/api/job/") and u.path.endswith("/cancel"):
            jid = u.path.split("/")[-2]
            j = TURTLE_JOBS.get(jid)
            if j and j.get("status") == "corriendo":
                j["status"] = "cancelado"
                self._json({"job_id": jid, "status": "cancelado"})
            else:
                self._json({"error": "no hay trabajo corriendo con ese ID"}, 404)
        elif u.path == "/api/montecarlo":
            import pandas as pd
            from bt.montecarlo import run_montecarlo
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0) or b"{}")
            except Exception:
                body = {}
            bt = body.get("bt_id", "")
            sims = min(int(body.get("sims", 500)), 5000)
            seed = int(body.get("seed", 12345))
            try:
                trades = pd.read_csv(os.path.join("results", bt, "trades.csv")).to_dict("records")
                met = json.load(open(os.path.join("results", bt, "metrics.json"), encoding="utf-8"))
                mc = run_montecarlo(
                    [{"pnl": float(t.get("pnl", 0)), "direction": t.get("direction", "LONG")} for t in trades],
                    float(met.get("capital", 50.0)), sims, seed)
                mc_id = f"{bt}-MC{seed}-{sims}"
                with open(os.path.join("results", bt, f"montecarlo_{sims}_{seed}.json"), "w") as f:
                    json.dump({"mc_id": mc_id, "bt_id": bt, **mc}, f, indent=2, default=str)
                self._json({"mc_id": mc_id, "bt_id": bt, **mc})
            except Exception as e:
                self._json({"error": str(e)[:200]}, 404)
        else:
            self.send_response(404); self.end_headers()

if __name__ == "__main__":
    import socketserver
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print("[TurtleLab] arrancando...")
    port = PORT
    srv = None
    for cand in (PORT, 8081, 8082, 8090):
        try:
            srv = socketserver.ThreadingTCPServer(("127.0.0.1", cand), H, bind_and_activate=False)
            srv.allow_reuse_address = True
            srv.server_bind()
            srv.server_activate()
            port = cand
            break
        except OSError:
            continue
    if srv is None:
        live = find_live_panel()
        if live:
            print(f"Puertos ocupados. Panel vivo en {live}.")
            raise SystemExit(0)
        print("ERROR: no se pudo abrir ningun puerto.")
        raise SystemExit(1)
    try:
        open("panel.pid", "w").write(str(os.getpid()))
    except Exception:
        pass
    print(f"TurtleLab en http://localhost:{port}")
    srv.serve_forever()
