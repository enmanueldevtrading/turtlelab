/* TurtleLab — panel de backtesting (sin dependencias). */
"use strict";

const TF_ORDER = ["M1", "M3", "M5", "M15", "M30", "H1", "H4", "D1"];
const S = {
  results: [], inv: [], meta: {}, plugins: null, job: null,
  src: "weltrade", sortK: "net", sortD: -1, tfs: {}, rows: [],
  scan: null,
};

/* ---------- utilidades ---------- */
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g,
  (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const num = (v, d = 2) => (v == null || v === "" || isNaN(+v) ? "–" : (+v).toFixed(d));
const lbl = (k) => (S.meta[k] && S.meta[k].label) || k;

function toast(msg, kind) {
  const el = document.createElement("div");
  el.className = "toast" + (kind ? " " + kind : "");
  el.innerHTML = msg;
  $("toasts").appendChild(el);
  setTimeout(() => { el.style.opacity = "0"; el.style.transform = "translateY(8px)"; }, 4400);
  setTimeout(() => el.remove(), 5000);
}

async function api(path, opt) {
  const r = await fetch(path, opt);
  if (!r.ok) {
    let detail = "";
    try { const j = await r.json(); detail = j.error || j.message || ""; } catch (_) {}
    throw new Error(detail || ("HTTP " + r.status + " en " + path));
  }
  return r.json();
}

function fundClass(status) {
  if (status === "APTO") return "fund-ok";
  if (status === "NO APTO") return "fund-no";
  if (!status) return "";
  return "fund-mid";
}
function fundTag(f) {
  const st = (f && (f.status || f.fund_status)) || "";
  if (!st) return '<span class="mut">—</span>';
  const dd = f.max_dd != null ? f.max_dd : f.fund_dd;
  return '<span class="fund-tag ' + fundClass(st) + '">' + esc(st) +
    (dd != null ? " · " + num(dd, 1) + "%" : "") + "</span>";
}

/* ---------- navegación ---------- */
document.querySelectorAll("#nav button").forEach((b) => {
  b.onclick = () => goView(b.dataset.v);
});
function goView(v) {
  document.querySelectorAll("#nav button").forEach((x) => x.classList.toggle("on", x.dataset.v === v));
  document.querySelectorAll(".view").forEach((x) => x.classList.toggle("on", x.id === "v-" + v));
  if (v === "fondeo") renderFunding();
}

/* ---------- arranque ---------- */
async function boot() {
  try {
    const [st, meta] = await Promise.all([api("/api/status"), api("/api/strategies")]);
    S.results = st.results || [];
    S.meta = meta || {};
    renderStatus(st);
    renderStrategies();
    renderPlugins();
    renderResults();
    renderFunding();
    renderMcSelect();
    $("sBt").textContent = S.results.length;
    await loadInventory(S.src);
    initMt5();
    const act = await api("/api/active");
    if (act.running) { S.job = act.running.job_id; pollJob(); }
  } catch (e) {
    window.__bootErr = (e && e.message) || String(e);
    toast("No se pudo cargar el panel: " + esc(e.message), "err");
  }
}

function renderStatus(st) {
  const w = (st.sources && st.sources.weltrade) || { files: 0, symbols: 0 };
  const y = (st.sources && st.sources.yahoo) || { files: 0, symbols: 0 };
  const empty = !w.files && !y.files;
  $("dataEmpty").hidden = !empty;
  $("dataBody").hidden = empty;
  const h = $("hstatus");
  if (empty) {
    h.className = "hstatus warn";
    h.innerHTML = "sin datos · <b>0</b> velas";
    return;
  }
  $("sFiles").textContent = w.files;
  $("sSym").textContent = w.symbols;
  $("sSrc").textContent = "Weltrade: " + w.files + " archivos / " + w.symbols +
    " símbolos · Yahoo: " + y.files + " archivos / " + y.symbols + " símbolos";
  h.className = "hstatus";
  h.innerHTML = "<b>" + w.symbols + "</b> símbolos · <b>" + w.files + "</b> archivos";
}

/* ---------- datos ---------- */
async function loadInventory(src) {
  S.src = src;
  $("pillW").classList.toggle("on", src === "weltrade");
  $("pillY").classList.toggle("on", src === "yahoo");
  $("invBox").innerHTML = '<div class="skel"></div><div class="skel"></div>';
  try {
    const iv = await api("/api/inventory?src=" + src);
    S.inv = iv.inventory || [];
  } catch (e) {
    S.inv = [];
    toast("Inventario no disponible: " + esc(e.message), "err");
  }
  try {
    const c = await api("/api/costs?src=" + src);
    S.costs = c.costs || {};
  } catch (e) {
    S.costs = {};
  }
  renderInventory();
}

function costLine(sym) {
  const c = (S.costs || {})[sym];
  if (!c) return "";
  if (c.fallback || !c.spread_pt) {
    return '<span class="cost mut">costes: sin datos de MT5 para este par</span>';
  }
  const spr = "spread " + c.spread_pt + " pt" +
    (c.spread_price ? " (" + num(c.spread_price, 2) + ")" : "");
  const swL = c.swap_long != null ? num(c.swap_long, 2) : "—";
  const swS = c.swap_short != null ? num(c.swap_short, 2) : "—";
  return '<span class="cost">' + esc(spr) + " · swap L " + esc(String(swL)) +
    " / C " + esc(String(swS)) + (c.currency ? " " + esc(c.currency) : "") + "</span>";
}

// Familia del par: "SwitchX 1800" -> "SwitchX", "FX Vol 20" -> "FX Vol".
function pairFamily(sym) {
  const t = String(sym || "").trim();
  const m = t.match(/^(.*?)[\s_-]+\d+$/);
  return (m ? m[1] : t).trim();
}

function renderInventory() {
  if ($("invTitle")) {
    $("invTitle").textContent = "Datos de " +
      (S.src === "yahoo" ? "Yahoo" : "Weltrade") + " por par";
  }
  const q = ($("qSym").value || "").toLowerCase();
  if (!S.inv.length) {
    $("invCount").textContent = "0 pares";
    $("invBox").innerHTML = '<p class="mut">Sin archivos para esta fuente. Usa <b>Importar desde MT5</b> ' +
      'arriba, o restaura un paquete con <code>python scripts/data_pack.py unpack archivo.zip</code>.</p>';
    return;
  }
  const order = ["M1", "M3", "M5", "M15", "M30", "H1", "H4", "D1"];
  const pairs = new Map();
  for (const r of S.inv) {
    if (q && !String(r.symbol || "").toLowerCase().includes(q)) continue;
    if (!pairs.has(r.symbol)) pairs.set(r.symbol, []);
    pairs.get(r.symbol).push(r);
  }
  const names = [...pairs.keys()].sort((a, b) => a.localeCompare(b, "es"));
  $("invCount").textContent = names.length + " pares de " + S.inv.length + " archivos";
  if (!names.length) {
    $("invBox").innerHTML = '<p class="mut">Ningún par coincide con "' + esc(q) + '".</p>';
    return;
  }
  const fams = new Map();
  for (const n of names) {
    const f = pairFamily(n);
    if (!fams.has(f)) fams.set(f, []);
    fams.get(f).push(n);
  }
  const srcLabel = S.src === "yahoo" ? "Yahoo" : "Weltrade";
  const badge = S.src === "yahoo" ? "yh" : "wl";
  let h = "";
  for (const fam of [...fams.keys()].sort((a, b) => a.localeCompare(b, "es"))) {
    const list = fams.get(fam);
    h += '<div class="famhead">' + esc(fam) + ' <span class="mut">' + list.length +
      (list.length === 1 ? " par" : " pares") + '</span></div><div class="pairgrid">';
    for (const name of list) {
      const rows = pairs.get(name).slice().sort((a, b) =>
        order.indexOf(a.timeframe) - order.indexOf(b.timeframe));
      const total = rows.reduce((a, r) => a + (+r.rows || 0), 0);
      h += '<div class="pair"><div class="pair-head"><b>' + esc(name) + '</b>' +
        '<span class="badge ' + badge + '">' + srcLabel + '</span>' +
        '<span class="mut">' + rows.length + " TF · " + total.toLocaleString("es-ES") +
        ' velas</span></div>' + costLine(name) + '<div class="tfgrid">';
      for (const r of rows) {
        h += '<div class="tftile"><div class="tfrow"><b>' + esc(r.timeframe) + "</b><span>" +
          (+r.rows || 0).toLocaleString("es-ES") + "</span></div><em>" +
          esc(String(r.from || "").slice(0, 10)) + " → " + esc(String(r.to || "").slice(0, 10)) +
          "</em></div>";
      }
      h += "</div></div>";
    }
    h += "</div>";
  }
  $("invBox").innerHTML = h;
}
$("qSym").addEventListener("input", renderInventory);
$("pillW").onclick = () => loadInventory("weltrade");
$("pillY").onclick = () => loadInventory("yahoo");
$("btnRecheck").onclick = () => boot();

/* ---------- importar desde MT5 ---------- */
S.mt5 = { status: null, symbols: [], sel: new Set(), q: "", bars: 50000, mode: "bars",
          days: 1, job: null, timer: null };

function mt5Selected() {
  return [...S.mt5.sel];
}
function mt5Tfs() {
  return [...document.querySelectorAll("#mt5Tfs .pill.on")].map((b) => b.dataset.tf);
}
function mt5Count() {
  const n = S.mt5.sel.size;
  $("mt5Sel").textContent = n + (n === 1 ? " elegido" : " elegidos");
  const tfs = mt5Tfs();
  $("mt5TfSel").textContent = tfs.length === 8 ? "· todas" : "· " + tfs.join(" ");
  const mode = S.mt5.mode;
  const files = mode === "bars" ? n * tfs.length : n;
  const mb = mode === "bars"
    ? (files * S.mt5.bars * 12) / 1e6
    : (n * S.mt5.days * 45000 * 30) / 1e6;
  $("mt5Estimate").textContent = n
    ? files.toLocaleString("es-ES") + " archivo(s) · espacio aproximado " +
      (mb < 1 ? mb.toFixed(2) : mb.toFixed(1)) + " MB"
    : "Elige al menos un par.";
  $("mt5Go").disabled = !n || (mode === "bars" && !tfs.length);
}

function renderMt5Symbols() {
  const q = (S.mt5.q || "").toLowerCase();
  const list = S.mt5.symbols.filter((s) => !q || s.toLowerCase().includes(q));
  if (!list.length) {
    $("mt5Syms").innerHTML = '<p class="mut">' + (S.mt5.symbols.length
      ? "Ningún par coincide." : "No hay lista de símbolos. Conecta MT5 para verlos.") + "</p>";
    return;
  }
  let h = "";
  for (const sym of list) {
    const on = S.mt5.sel.has(sym) ? " on" : "";
    h += '<button type="button" class="symchip' + on + '" data-sym="' + esc(sym) + '">' +
      esc(sym) + "</button>";
  }
  $("mt5Syms").innerHTML = h;
}

async function initMt5() {
  const st = await api("/api/mt5/status").catch(() => ({ available: false, reason: "sin respuesta" }));
  S.mt5.status = st;
  const chip = $("mt5State");
  const grid = $("mt5Grid");
  const off = $("mt5Offline");

  if (!st.available) {
    // Sin MT5 no hay pares que elegir: se explica el motivo, no se rellena con nada.
    chip.className = "chip warn";
    chip.textContent = "MT5 no conectado";
    chip.title = st.reason || "";
    if (off) off.hidden = false;
    if (grid) grid.hidden = true;
    const msg = $("mt5OfflineMsg");
    if (msg) {
      msg.innerHTML = esc(st.reason || "sin detalle") +
        (st.hint ? "<br>" + esc(st.hint) : "");
    }
    if ($("mt5Syms")) $("mt5Syms").innerHTML = "";
    S.mt5.symbols = [];
    return;
  }

  chip.className = "chip ok";
  chip.textContent = "MT5 conectado" + (st.server ? " · " + st.server : "") +
    (st.login ? " · cuenta " + st.login : "");
  if (off) off.hidden = true;
  if (grid) grid.hidden = false;

  const r = await api("/api/mt5/symbols").catch(() => ({ symbols: [] }));
  S.mt5.symbols = r.symbols || [];
  if (!$("mt5Go").dataset.wired) {
    $("mt5Go").dataset.wired = "1";
    bootMt5Controls();
  }
  if (!S.mt5.sel.size) {
    const local = new Set((S.inv || []).map((x) => x.symbol));
    S.mt5.sel = new Set(S.mt5.symbols.filter((x) => local.has(x)));
  }
  renderMt5Symbols();
  mt5Count();
}

function bootMt5Controls() {
  if ($("mt5Retry")) $("mt5Retry").onclick = () => initMt5();

  $("mt5q").addEventListener("input", () => { S.mt5.q = $("mt5q").value; renderMt5Symbols(); });
  $("mt5Syms").addEventListener("click", (ev) => {
    const b = ev.target.closest(".symchip");
    if (!b) return;
    const sym = b.dataset.sym;
    if (S.mt5.sel.has(sym)) { S.mt5.sel.delete(sym); b.classList.remove("on"); }
    else { S.mt5.sel.add(sym); b.classList.add("on"); }
    mt5Count();
  });
  $("mt5All").onclick = () => {
    S.mt5.sel = new Set(S.mt5.symbols);
    renderMt5Symbols(); mt5Count();
  };
  $("mt5None").onclick = () => {
    S.mt5.sel = new Set();
    renderMt5Symbols(); mt5Count();
  };
  $("mt5Mine").onclick = () => {
    const local = new Set((S.inv || []).map((x) => x.symbol));
    S.mt5.sel = new Set(S.mt5.symbols.filter((x) => local.has(x)));
    renderMt5Symbols(); mt5Count();
  };
  $("mt5Tfs").addEventListener("click", (ev) => {
    const b = ev.target.closest(".pill");
    if (!b) return;
    b.classList.toggle("on");
    mt5Count();
  });
  document.querySelectorAll("#mt5Bars .pill").forEach((b) => {
    b.onclick = () => {
      document.querySelectorAll("#mt5Bars .pill").forEach((x) => x.classList.remove("on"));
      b.classList.add("on");
      S.mt5.bars = +b.dataset.bars;
      mt5Count();
    };
  });
  $("mt5Mode").addEventListener("click", (ev) => {
    const b = ev.target.closest(".pill");
    if (!b) return;
    document.querySelectorAll("#mt5Mode .pill").forEach((x) => x.classList.remove("on"));
    b.classList.add("on");
    S.mt5.mode = b.dataset.mode;
    $("mt5TickBox").hidden = S.mt5.mode !== "ticks";
    $("mt5BookBox").hidden = S.mt5.mode !== "book";
    $("mt5Bars").hidden = S.mt5.mode !== "bars";
    $("mt5Tfs").hidden = S.mt5.mode !== "bars";
    mt5Count();
  });
  $("mt5Days").addEventListener("click", (ev) => {
    const b = ev.target.closest(".pill");
    if (!b) return;
    document.querySelectorAll("#mt5Days .pill").forEach((x) => x.classList.remove("on"));
    b.classList.add("on");
    S.mt5.days = +b.dataset.days;
    mt5Count();
  });
  $("mt5Go").onclick = startMt5;
  $("mt5Cancel").onclick = async () => {
    if (!S.mt5.job) return;
    await api("/api/mt5/cancel", { method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job: S.mt5.job }) }).catch(() => {});
    toast("Cancelando descarga…");
  };
}

async function startMt5() {
  if (!S.mt5.status || !S.mt5.status.available) {
    toast("MT5 no está disponible: " + ((S.mt5.status && S.mt5.status.reason) || "sin conexión"), "err");
    return;
  }
  const body = { symbols: mt5Selected(), tfs: mt5Tfs(), bars: S.mt5.bars,
                 mode: S.mt5.mode, tick_days: S.mt5.days };
  if (!body.symbols.length) return toast("Elige al menos un par.", "err");
  $("mt5Go").disabled = true;
  $("mt5Cancel").hidden = false;
  $("mt5Bar").style.width = "0%";
  $("mt5Log").textContent = "Preparando descarga…";
  try {
    const r = await api("/api/mt5/import", { method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (r.error) throw new Error(r.error);
    S.mt5.job = r.job;
    pollMt5();
  } catch (e) {
    toast("No se pudo empezar: " + esc(e.message), "err");
    $("mt5Go").disabled = false;
    $("mt5Cancel").hidden = true;
  }
}

function pollMt5() {
  clearTimeout(S.mt5.timer);
  const tick = async () => {
    if (!S.mt5.job) return;
    let j;
    try { j = await api("/api/mt5/job/" + encodeURIComponent(S.mt5.job)); }
    catch (e) { S.mt5.timer = setTimeout(tick, 3000); return; }
    if (j.error) {
      $("mt5Log").textContent = j.error;
      S.mt5.job = null;
      $("mt5Go").disabled = false;
      $("mt5Cancel").hidden = true;
      return;
    }
    const pct = j.total ? Math.round(100 * j.done / j.total) : 0;
    $("mt5Bar").style.width = pct + "%";
    const lines = (j.log_tail || []).map((x) => {
        const name = x.tf === "TICKS" ? x.symbol + " · ticks"
        : x.tf === "LIBRO" ? x.symbol + " · libro" : x.symbol + " · " + x.tf;
      if (x.ok) {
        return '<span class="ok">✓</span> ' + esc(name) + " · " +
          (+x.new || 0).toLocaleString("es-ES") +
          (x.tf === "TICKS" ? " ticks" : x.tf === "LIBRO" ? " niveles" : " velas nuevas") +
          (x.rows ? ' <span class="mut">(total ' + (+x.rows).toLocaleString("es-ES") + ")</span>" : "");
      }
      return '<span class="bad">✕</span> ' + esc(name) + " · " + esc(x.note || "sin datos");
    });
    $("mt5Log").innerHTML = "<b>" + j.done + "/" + j.total + "</b> · " + esc(j.current || "") +
      (lines.length ? "<br>" + lines.join("<br>") : "");
    if (j.status === "hecho" || j.status === "cancelado") {
      S.mt5.job = null;
      $("mt5Go").disabled = false;
      $("mt5Cancel").hidden = true;
      toast(j.status === "hecho"
        ? "Descarga terminada: " + (+j.saved_rows || 0).toLocaleString("es-ES") + " datos nuevos."
        : "Descarga cancelada.", j.fail_count ? "warn" : "ok");
      await loadInventory(S.src);
      boot();
      return;
    }
    S.mt5.timer = setTimeout(tick, 1500);
  };
  tick();
}

/* ---------- datos sueltos ---------- */
$("btnScan").onclick = async () => {
  $("importBox").innerHTML = '<div class="skel"></div><div class="skel"></div>';
  $("btnScan").disabled = true;
  try {
    S.scan = await api("/api/import-scan");
    renderScan();
  } catch (e) {
    $("importBox").innerHTML = '<p class="mut">No se pudo escanear: ' + esc(e.message) + "</p>";
  } finally { $("btnScan").disabled = false; }
};

function renderScan() {
  const items = (S.scan && S.scan.items) || [];
  $("btnImport").disabled = !(S.scan && S.scan.pending);
  if (!items.length) {
    $("importBox").innerHTML = '<p class="mut">No hay velas fuera de <code>data/</code>.</p>';
    return;
  }
  let h = "<table><thead><tr><th>Archivo</th><th>Símbolo</th><th>TF</th><th>Filas</th>" +
    "<th>Nuevas</th><th>Acción</th></tr></thead><tbody>";
  for (const it of items) {
    const act = String(it.action || "");
    const cls = act.startsWith("omitir") || act.startsWith("duplicado") ? "mut" : "";
    h += "<tr><td>" + esc(it.path) + "</td><td>" + esc(it.symbol) + "</td><td>" +
      esc(it.timeframe) + "</td><td>" + (it.rows || 0) + "</td><td>" +
      (it.new_rows || 0) + "</td><td class='" + cls + "'>" + esc(act) + "</td></tr>";
  }
  $("importBox").innerHTML = h + "</tbody></table><p class='mut'>" +
    (S.scan.pending ? S.scan.pending + " archivo(s) pendientes · " +
      (S.scan.total_new_rows || 0) + " velas nuevas" : "Nada pendiente: ya está todo importado.") + "</p>";
}

$("btnImport").onclick = async () => {
  if (!confirm("¿Fusionar los datos detectados en data/weltrade? No se sobrescribe nada.")) return;
  $("btnImport").disabled = true;
  try {
    const rep = await api("/api/import-run", { method: "POST" });
    toast("Importados " + rep.imported.length + " archivos.", "ok");
    S.scan = await api("/api/import-scan");
    renderScan();
    boot();
  } catch (e) {
    toast("Importación falló: " + esc(e.message), "err");
    $("btnImport").disabled = false;
  }
};

/* ---------- estrategias ---------- */
function sortedMeta() {
  return Object.entries(S.meta).sort((a, b) =>
    (a[1].order || 100) - (b[1].order || 100) ||
    String(a[1].label).localeCompare(String(b[1].label)));
}

function renderStrategies() {
  const box = $("stratGrid");
  const q = ($("stratQ").value || "").toLowerCase();
  const items = sortedMeta().filter(([k, m]) =>
    !q || (m.label + " " + k + " " + (m.desc || "")).toLowerCase().includes(q));
  if (!items.length) { box.innerHTML = '<p class="mut">Ninguna estrategia coincide.</p>'; return; }
  box.innerHTML = "";
  for (const [key, m] of items) {
    const sel = S.tfs[key] || new Set(m.tfs || TF_ORDER);
    const tfs = (m.tfs || TF_ORDER).map((tf) =>
      '<button class="tf' + (sel.has(tf) ? " on" : "") + '" data-tf="' + tf + '">' + tf + "</button>").join("");
    const chips = Object.entries(m.params || {}).map(([k, v]) => {
      const val = Array.isArray(v)
        ? v.map((x) => (Array.isArray(x) ? x.join("–") : x)).join(" + ")
        : v;
      return '<span class="chip">' + esc(k) + ": <b>" + esc(val) + "</b></span>";
    }).join("");
    const caps = [10, 20, 50, 100, 6000];
    const el = document.createElement("article");
    el.className = "strat";
    el.dataset.key = key;
    el.innerHTML =
      '<h3>' + esc(m.label) + '<span class="badge">' + esc(m.plugin || "core") + "</span></h3>" +
      '<div class="chips">' + chips +
        '<span class="chip">' + esc(m.riesgo || "riesgo del preset") + "</span></div>" +
      '<p class="desc">' + esc(m.desc) + "</p>" +
      '<ul class="rules-list">' +
        (m.rules || []).map((r) => "<li>" + esc(r) + "</li>").join("") + "</ul>" +
      '<div class="tfs" data-role="tfs">' + tfs + "</div>" +
      '<div class="row">' +
        '<select data-role="src"><option value="weltrade">Weltrade</option><option value="yahoo">Yahoo</option></select>' +
        '<select data-role="cap">' +
          caps.map((c) => '<option value="' + c + '"' +
            (c === Math.round(m.balance || 50) ? " selected" : "") + ">$" +
            c.toLocaleString("es-ES") + "</option>").join("") +
        "</select>" +
        '<select data-role="limit"><option value="0">Todos los símbolos</option>' +
          '<option value="1">1 símbolo</option><option value="3">3 símbolos</option>' +
          '<option value="10">10 símbolos</option></select>' +
        '<button class="run" data-role="go">Correr</button>' +
      "</div>";
    el.querySelectorAll(".tf").forEach((b) => {
      b.onclick = () => {
        const set = S.tfs[key] || new Set(m.tfs || TF_ORDER);
        if (set.has(b.dataset.tf)) set.delete(b.dataset.tf); else set.add(b.dataset.tf);
        if (!set.size) set.add(b.dataset.tf);
        S.tfs[key] = set;
        b.classList.toggle("on", set.has(b.dataset.tf));
      };
    });
    el.querySelector('[data-role="go"]').onclick = () => runJob(key, el);
    box.appendChild(el);
  }
}
$("stratQ").addEventListener("input", renderStrategies);

async function runJob(key, card) {
  const m = S.meta[key] || {};
  const set = S.tfs[key] || new Set(m.tfs || TF_ORDER);
  const tfs = (m.tfs || TF_ORDER).filter((t) => set.has(t));
  const src = card.querySelector('[data-role="src"]').value;
  const cap = card.querySelector('[data-role="cap"]').value;
  const limit = card.querySelector('[data-role="limit"]').value;
  const q = "?mode=" + encodeURIComponent(key) + "&balance=" + cap + "&src=" + src +
    "&tfs=" + encodeURIComponent(tfs.join(",")) + "&limit=" + limit;
  document.querySelectorAll(".strat .run").forEach((b) => (b.disabled = true));
  try {
    const r = await api("/api/run-turtle" + q, { method: "POST" });
    S.job = r.job_id;
    $("job").textContent = "Iniciando " + lbl(key) + "…";
    $("jobRes").innerHTML = "";
    $("pbar").style.width = "0%";
    goView("trabajo");
    pollJob();
  } catch (e) {
    document.querySelectorAll(".strat .run").forEach((b) => (b.disabled = false));
    toast("No se pudo iniciar: " + esc(e.message), "err");
  }
}

/* ---------- trabajo ---------- */
async function pollJob() {
  if (!S.job) return;
  try {
    const j = await api("/api/job/" + S.job);
    renderJob(j);
    if (j.status === "corriendo") setTimeout(pollJob, 1500);
    else {
      document.querySelectorAll(".strat .run").forEach((b) => (b.disabled = false));
      $("btnCancel").hidden = true;
      if (j.status === "terminado") {
        $("pbar").style.width = "100%";
        toast("Trabajo terminado: " + (j.done || 0) + " pruebas", "ok");
        boot();
      } else if (String(j.status).indexOf("error") === 0) {
        toast("El trabajo falló: " + esc(j.status), "err");
      }
    }
  } catch (e) {
    setTimeout(pollJob, 4000);
  }
}

function renderJob(j) {
  const pc = j.total ? Math.round((j.done / j.total) * 100) : 0;
  $("pbar").style.width = pc + "%";
  const st = j.status === "corriendo" ? "CORRIENDO" : String(j.status).toUpperCase();
  $("job").innerHTML = "<b>" + st + "</b> · " + j.done + "/" + j.total + " (" + pc + "%)" +
    (j.current ? ' · <span class="mut">' + esc(j.current) + "</span>" : "");
  $("btnCancel").hidden = j.status !== "corriendo";
  const eta = (() => {
    if (!j.started || !j.done || !j.total || j.status !== "corriendo") return "";
    const el = Date.now() / 1000 - j.started;
    const rest = (el / j.done) * (j.total - j.done);
    if (!isFinite(rest) || rest <= 0) return "";
    return rest < 60 ? "faltan ~" + Math.round(rest) + " s" : "faltan ~" + Math.round(rest / 60) + " min";
  })();
  $("jobEta").textContent = eta;
  const rows = (j.results || []).slice().reverse();
  let h = "<table><thead><tr><th>Símbolo</th><th>TF</th><th>Estrategia</th><th>Neto $</th>" +
    "<th>PF</th><th>DD%</th><th>Fondeo</th></tr></thead><tbody>";
  for (const x of rows.slice(0, 14)) {
    if (x.error) {
      h += "<tr><td>" + esc(x.symbol) + "</td><td colspan='6' class='p'>" + esc(x.error) + "</td></tr>";
    } else if (x.note) {
      h += "<tr><td>" + esc(x.symbol) + "</td><td>" + esc(x.tf) + "</td><td>" + esc(lbl(x.strategy)) +
        "</td><td colspan='4' class='mut'>sin operaciones</td></tr>";
    } else {
      h += "<tr><td>" + esc(x.symbol) + "</td><td>" + esc(x.tf) + "</td><td>" + esc(lbl(x.strategy)) +
        '</td><td class="' + (+x.net >= 0 ? "g" : "p") + '">' + num(x.net) + "</td><td>" +
        num(x.pf) + "</td><td>" + num(x.dd) + "</td><td>" + fundTag(x) + "</td></tr>";
    }
  }
  const wins = (j.results || []).filter((x) => !x.error && +x.net >= 0).length;
  $("jobRes").innerHTML = h + "</tbody></table><p class='mut'>" + wins +
    " con neto ≥ 0 en este trabajo.</p>";
}
$("btnCancel").onclick = async () => {
  if (!S.job) return;
  try { await api("/api/job/" + S.job + "/cancel", { method: "POST" }); toast("Cancelando…"); }
  catch (e) { toast("No se pudo cancelar: " + esc(e.message), "err"); }
};

/* ---------- pruebas guardadas ---------- */
function renderResults() {
  const fs = $("fStrat"), cur = fs.value;
  fs.innerHTML = '<option value="">Todas las estrategias</option>' +
    [...new Set(S.results.map((r) => r.strategy))].map((k) =>
      '<option value="' + esc(k) + '">' + esc(lbl(k)) + "</option>").join("");
  if (cur) fs.value = cur;
  const fR = $("fRes").value;
  const fF = $("fFund").value;
  const q = ($("qAll").value || "").toLowerCase();
  let rows = S.results.filter((r) => {
    if (fs.value && r.strategy !== fs.value) return false;
    if (fR && (fR === "G" ? +r.net < 0 : +r.net >= 0)) return false;
    if (fF) {
      const st = r.fund_status || "";
      if (fF === "sin-dato" ? !!st : st !== fF) return false;
    }
    if (q) {
      const hay = [r.bt_id, lbl(r.strategy), r.strategy, r.symbol, r.timeframe, r.src]
        .join(" ").toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
  const isNum = (k) => ["net", "pf", "dd", "trades", "wr", "capital",
                        "fund_dd", "fund_daily", "fund_net_pct"].includes(k);
  rows.sort((a, b) => {
    const va = isNum(S.sortK) ? +a[S.sortK] || 0 : String(a[S.sortK] || "");
    const vb = isNum(S.sortK) ? +b[S.sortK] || 0 : String(b[S.sortK] || "");
    return (va > vb ? 1 : va < vb ? -1 : 0) * S.sortD;
  });
  S.rows = rows;
  if (!S.results.length) {
    $("resBox").innerHTML = '<p class="mut">Sin pruebas aún. Corre una estrategia desde la vista <b>Estrategias</b>.</p>';
    return;
  }
  if (!rows.length) {
    $("resBox").innerHTML = '<p class="mut">Sin resultados para esos filtros.</p>';
    return;
  }
  const TH = (k, t) => '<th class="sort" data-k="' + k + '">' + t +
    (S.sortK === k ? (S.sortD > 0 ? " ↑" : " ↓") : "") + "</th>";
  let h = "<table><thead><tr><th>ID</th>" + TH("strategy", "Estrategia") + TH("symbol", "Símbolo") +
    TH("timeframe", "TF") + TH("capital", "Capital") + TH("net", "Neto $") + TH("pf", "PF") +
    TH("dd", "DD%") + TH("fund_daily", "DD día %") + TH("trades", "Ops") +
    "<th>Fondeo</th><th></th></tr></thead><tbody>";
  for (const r of rows.slice(0, 200)) {
    h += "<tr><td>" + esc(r.bt_id) + "</td><td>" + esc(lbl(r.strategy)) + "</td><td>" +
      esc(r.symbol) + "</td><td>" + esc(r.timeframe) + "</td><td>$" + num(r.capital, 0) +
      '</td><td class="' + (+r.net >= 0 ? "g" : "p") + '">' + num(r.net) + "</td><td>" +
      num(r.pf) + "</td><td>" + num(r.dd) + "</td><td>" + num(r.fund_daily, 1) + "</td><td>" +
      (r.trades || 0) + "</td><td>" + fundTag(r) + "</td>" +
      "<td><button class='ghost' data-bt='" + esc(r.bt_id) + "'>Detalle</button></td></tr>";
  }
  $("resBox").innerHTML = h + "</tbody></table><p class='mut'>Mostrando " +
    Math.min(200, rows.length) + " de " + rows.length + ".</p>";
  $("resBox").querySelectorAll("th.sort").forEach((th) => {
    th.onclick = () => {
      const k = th.dataset.k;
      if (S.sortK === k) S.sortD *= -1; else { S.sortK = k; S.sortD = -1; }
      renderResults();
    };
  });
  $("resBox").querySelectorAll("[data-bt]").forEach((b) => {
    b.onclick = () => showDetail(b.dataset.bt);
  });
}
["qAll", "fStrat", "fRes", "fFund"].forEach((id) => $(id).addEventListener("input", renderResults));

$("btnCsv").onclick = () => {
  if (!S.rows.length) return toast("No hay filas que exportar.", "err");
  const cols = ["bt_id", "strategy", "symbol", "timeframe", "capital", "net", "pf", "dd",
                "trades", "wr", "fund_status", "fund_dd", "fund_daily", "fund_net_pct"];
  const csv = [cols.join(";")].concat(S.rows.map((r) => cols.map((c) => r[c]).join(";"))).join("\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" }));
  a.download = "turtlelab_resultados.csv";
  a.click();
  toast("CSV exportado (" + S.rows.length + " filas).", "ok");
};

$("btnDel").onclick = async () => {
  if (!S.results.length) return toast("No hay pruebas guardadas.", "err");
  if (!confirm("¿Eliminar las " + S.results.length + " pruebas guardadas? No se puede deshacer.")) return;
  try {
    const r = await api("/api/results/delete", { method: "POST" });
    toast("Eliminadas " + r.deleted + " pruebas.", "ok");
    $("detail").innerHTML = "";
    boot();
  } catch (e) { toast(esc(e.message), "err"); }
};

async function showDetail(bt) {
  try {
    const d = await api("/api/backtest/" + encodeURIComponent(bt));
    const m = d.metrics || {};
    const f = d.funding || {};
    const kv = (k, v) => "<div><b>" + v + "</b><span>" + k + "</span></div>";
    let h = '<div class="drawer"><h3>' + esc(bt) + " · " + esc(lbl(d.config.strategy)) + " · " +
      esc(d.config.symbol) + " " + esc(d.config.timeframe) + "</h3>";
    h += "<div class='kv'>" + kv("Neto $", num(m.net_profit)) + kv("PF", num(m.profit_factor)) +
      kv("DD $", num(m.max_drawdown)) + kv("DD %", num(m.max_drawdown_pct)) +
      kv("Ops", m.total || 0) + kv("WR %", num(m.win_rate, 1)) + "</div>";
    h += '<img src="/api/equity/' + encodeURIComponent(bt) + '.svg" alt="curva de capital" ' +
      "style='max-width:100%;border-radius:12px;margin:12px 0;background:#0a1120'>";
    if (f && f.status) {
      const pct = (v, lim) => Math.max(0, Math.min(100, (v / (lim || 1)) * 100));
      const usedDD = pct(f.max_dd, f.max_dd_pct);
      const usedDay = pct(f.max_daily_dd, f.daily_dd_pct);
      const usedTgt = Math.max(0, Math.min(100, (Math.max(0, f.net_pct) / (f.target_pct || 1)) * 100));
      const cls = (u) => (u >= 100 ? "bad" : u >= 70 ? "warn" : "");
      h += '<div class="rules-card"><h4>Cuenta de fondeo · $' +
        (f.account || 6000).toLocaleString("es-ES") + "</h4>" +
        '<div class="row" style="margin-bottom:10px">' + fundTag(f) +
        '<span class="mut">' + (f.target_hit
          ? "objetivo alcanzado " + esc(f.target_date || "")
          : "objetivo no alcanzado") +
        (f.breach ? " · brecha: " + esc(f.breach) + " " + esc(f.breach_date || "") : "") + "</span></div>" +
        '<div class="gauge"><div class="lab"><span>DD total</span><b>' + num(f.max_dd, 2) +
        "% / " + num(f.max_dd_pct, 0) + "%</b></div><div class='track'><i class='" +
        cls(usedDD) + "' style='width:" + usedDD + "%'></i></div></div>" +
        '<div class="gauge"><div class="lab"><span>DD diario</span><b>' + num(f.max_daily_dd, 2) +
        "% / " + num(f.daily_dd_pct, 0) + "%</b></div><div class='track'><i class='" +
        cls(usedDay) + "' style='width:" + usedDay + "%'></i></div></div>" +
        '<div class="gauge"><div class="lab"><span>Objetivo neto</span><b>' + num(f.net_pct, 2) +
        "% / " + num(f.target_pct, 0) + "%</b></div><div class='track'><i class='" +
        cls(usedTgt) + "' style='width:" + usedTgt + "%'></i></div></div>" +
        '<p class="mut">Colchón DD: $' + num(f.buffer_dd) + " · Colchón diario: $" +
        num(f.buffer_daily) + " · Días operados: " + (f.days_traded || 0) + "</p></div>";
    }
    h += "<div class='scrollx'><table><thead><tr><th>#</th><th>Dir</th><th>Entrada</th>" +
      "<th>Salida</th><th>Lote</th><th>PnL $</th><th>Motivo</th></tr></thead><tbody>";
    for (const [i, t] of (d.trades || []).slice(0, 100).entries()) {
      h += "<tr><td>" + (i + 1) + "</td><td>" + esc(t.direction) + "</td><td>" +
        esc(String(t.ts_entry || "").slice(0, 16)) + " @ " + esc(t.entry) + "</td><td>" +
        esc(String(t.ts_exit || "").slice(0, 16)) + " @ " + esc(t.exit) + "</td><td>" +
        esc(t.qty) + "</td><td class='" + (+t.pnl >= 0 ? "g" : "p") + "'>" + num(t.pnl) +
        "</td><td>" + esc(t.reason) + "</td></tr>";
    }
    h += "</tbody></table></div><p class='mut mt8'>Mostrando " +
      Math.min(100, (d.trades || []).length) + " de " + (d.trades || []).length + " operaciones.</p></div>";
    $("detail").innerHTML = h;
    $("detail").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (e) {
    toast("No se pudo abrir el detalle: " + esc(e.message), "err");
  }
}

/* ---------- fondeo ---------- */
function renderFunding() {
  if (!$("fundBox")) return;
  const f = $("fundFilter").value;
  const key = $("fundSort").value || "fund_dd";
  // Solo pruebas con veredicto de fondeo: el resto no aporta a esta vista.
  const rows = S.results.filter((r) => r.fund_status && (!f || r.fund_status === f));
  const withFund = rows.filter((r) => r.fund_status);
  const aptos = S.results.filter((r) => r.fund_status === "APTO").length;
  $("fundCount").textContent = S.results.length
    ? aptos + " APTO de " + S.results.length + " pruebas · " + withFund.length + " con datos de fondeo"
    : "Sin pruebas todavía.";
  if (!rows.length) {
    $("fundBox").innerHTML = S.results.length
      ? '<p class="mut">Sin pruebas con esos filtros.</p>'
      : '<p class="mut">Aún no hay pruebas guardadas. Corre una estrategia desde la vista <b>Estrategias</b> y aquí aparecerá su veredicto de fondeo.</p>';
    return;
  }
  rows.sort((a, b) => {
    const va = a[key] == null ? 1e9 : +a[key];
    const vb = b[key] == null ? 1e9 : +b[key];
    if (key === "fund_net_pct") return vb - va;
    return va - vb;
  });
  let h = "<table><thead><tr><th>ID</th><th>Estrategia</th><th>Símbolo</th><th>TF</th>" +
    "<th>Cuenta</th><th>DD total %</th><th>DD día %</th><th>Neto %</th><th>Objetivo</th>" +
    "<th>Estado</th></tr></thead><tbody>";
  for (const r of rows.slice(0, 200)) {
    h += "<tr><td>" + esc(r.bt_id) + "</td><td>" + esc(lbl(r.strategy)) + "</td><td>" +
      esc(r.symbol) + "</td><td>" + esc(r.timeframe) + "</td><td>$" +
      num(r.fund_account || r.capital, 0) + "</td><td>" + num(r.fund_dd, 2) + "</td><td>" +
      num(r.fund_daily, 2) + "</td><td>" + num(r.fund_net_pct, 2) + "</td><td>" +
      (r.fund_target ? "sí" : "no") + "</td><td>" + fundTag(r) + "</td></tr>";
  }
  $("fundBox").innerHTML = h + "</tbody></table>";
}
["fundFilter", "fundSort"].forEach((id) => $(id).addEventListener("change", renderFunding));

/* ---------- Monte Carlo ---------- */
function renderMcSelect() {
  const sel = $("mcBt");
  sel.innerHTML = S.results.length
    ? S.results.map((r) => "<option value='" + esc(r.bt_id) + "'>" + esc(r.bt_id) + " · " +
        esc(lbl(r.strategy)) + " " + esc(r.symbol) + " " + esc(r.timeframe) + "</option>").join("")
    : "<option value=''>Sin pruebas</option>";
}
$("btnMc").onclick = async () => {
  const bt = $("mcBt").value;
  if (!bt) return toast("No hay pruebas para simular.", "err");
  const sims = +$("mcSims").value, seed = +$("mcSeed").value || 12345;
  $("mcOut").innerHTML = '<div class="skel"></div>';
  try {
    const mc = await api("/api/montecarlo", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bt_id: bt, sims: sims, seed: seed }),
    });
    const P = mc.percentiles || {};
    const row = (k, t) => {
      const o = P[k] || {};
      return "<tr><td>" + t + "</td><td>" + num(o.P5) + "</td><td>" + num(o.P25) +
        "</td><td>" + num(o.P50) + "</td><td>" + num(o.P75) + "</td><td>" + num(o.P95) + "</td></tr>";
    };
    $("mcOut").innerHTML =
      "<div class='kv'>" +
      "<div><b>" + (100 * (mc.p_profit || 0)).toFixed(1) + "%</b><span>prob. beneficio</span></div>" +
      "<div><b>" + (100 * (mc.p_loss || 0)).toFixed(1) + "%</b><span>prob. pérdida</span></div>" +
      "<div><b>" + (100 * (mc.p_dd20 || 0)).toFixed(1) + "%</b><span>prob. DD &gt; 20%</span></div>" +
      "<div><b>" + num(mc.final_balance && mc.final_balance.median) + "</b><span>balance mediano</span></div></div>" +
      "<div class='scrollx'><table><thead><tr><th>Métrica</th><th>P5</th><th>P25</th><th>P50</th>" +
      "<th>P75</th><th>P95</th></tr></thead><tbody>" +
      row("net_profit", "Neto $") + row("max_drawdown_pct", "DD máx %") +
      row("profit_factor", "PF") + "</tbody></table></div>" +
      "<p class='mut mt8'>" + mc.n_sims + " simulaciones · semilla " + mc.seed +
      " · método " + esc(mc.method) + "</p>";
  } catch (e) {
    $("mcOut").innerHTML = "";
    toast("Monte Carlo falló: " + esc(e.message), "err");
  }
};

/* ---------- plugins ---------- */
$("btnPlugins").onclick = () => {
  $("pluginCard").scrollIntoView({ behavior: "smooth", block: "center" });
  renderPlugins();
};
$("btnReload").onclick = async () => {
  try {
    S.plugins = await api("/api/reload-plugins", { method: "POST" });
    renderPlugins();
    S.meta = await api("/api/strategies");
    renderStrategies();
    toast("Plugins recargados: " + S.plugins.count + " estrategias.", "ok");
  } catch (e) { toast("No se pudo recargar: " + esc(e.message), "err"); }
};
async function renderPlugins() {
  if (!S.plugins) {
    try { S.plugins = await api("/api/plugins"); }
    catch (e) { $("pluginList").innerHTML = '<p class="mut">No disponible.</p>'; return; }
  }
  const list = S.plugins.plugins || [];
  $("pluginList").innerHTML = list.length ? list.map((p) =>
    '<div class="plugin' + (p.ok ? "" : " err") + '"><span class="dot"></span><b>' +
    esc(p.file) + "</b><span class='mut'>" + (p.ok ? p.presets + " preset(s)" : "error") + "</span>" +
    (p.ok ? "" : '<span class="err">' + esc(p.error) + "</span>") + "</div>").join("")
    : '<p class="mut">Sin plugins cargados.</p>';
  if (S.plugins.errors && S.plugins.errors.length) {
    toast("Hay " + S.plugins.errors.length + " plugin(s) con error. Revisa la tarjeta Plugins.", "err");
  }
}

boot();
