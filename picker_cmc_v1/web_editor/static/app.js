"use strict";
// picker_cmc editor (D24): view + bbox edit/resize + ruler + save/save-as.
const SCALE = 1.5;
const FIG_TBL = ["caption_region", "body_region", "context_region"];
const state = { run: null, page: 1, selected: null, region: null, mode: "view",
                hidden: new Set(), dirty: false, ruler: [] };

const $ = (id) => document.getElementById(id);
async function getJSON(u) { return (await fetch(u)).json(); }
async function postJSON(u, body) {
  const r = await fetch(u, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  return r.json();
}

async function boot() {
  wireSetupPanel();
  await refreshRuns();
  const health = await getJSON("/api/health");
  if (!health.has_run) { $("run-meta").textContent = "no run open — use the setup panel to create or open one"; wireToolbar(); return; }
  await openCurrentRun();
}

async function openCurrentRun() {
  state.run = await getJSON("/api/run");
  if (!state.run.ok) { $("run-meta").textContent = "failed to load run"; return; }
  $("run-meta").textContent =
    `run: ${state.run.run_id}\npdf: ${state.run.source_pdf}\npages: ${state.run.page_count}\ncoords: ${state.run.coordinate_unit} / ${state.run.coordinate_origin}`;
  await buildTrees(); wireToolbar(); await refreshDirty(); showPage(1);
}

// ---- D26 setup panel / run launcher ----
function setupMsg(text, ok) { const m = $("setup-msg"); m.textContent = text; m.className = "setup-msg " + (ok ? "ok" : "err"); }

async function refreshRuns() {
  const r = await getJSON("/api/runs"); const ul = $("runs-list"); ul.innerHTML = "";
  (r.runs || []).forEach(run => {
    const li = document.createElement("li");
    li.textContent = `${run.run_id} (${run.page_count}p)`;
    li.onclick = async () => { await getJSON(`/api/run/${encodeURIComponent(run.run_id)}`); await openCurrentRun(); };
    ul.appendChild(li);
  });
}

function wireSetupPanel() {
  $("dl-template").onclick = async () => { $("setup-yaml").value = await (await fetch("/api/setup/template")).text(); setupMsg("template loaded — fill CHANGE_ME values", true); };
  $("setup-validate").onclick = async () => {
    const res = await postJSON("/api/setup/validate", { setup_yaml: $("setup-yaml").value });
    res.ok ? setupMsg("setup is valid ✓", true) : setupMsg(`${res.error_code}: ${res.error}${res.field ? " (" + res.field + ")" : ""}`, false);
  };
  $("setup-run").onclick = async () => {
    setupMsg("running detector…", true);
    const res = await postJSON("/api/setup/run", { setup_yaml: $("setup-yaml").value });
    if (!res.ok) { setupMsg(`${res.error_code}: ${res.error}${res.field ? " (" + res.field + ")" : ""}`, false); return; }
    setupMsg(`run ${res.run_id} created (${res.page_count}p) — opening…`, true);
    await refreshRuns(); await openCurrentRun(); $("setup-panel").open = false;
  };
  $("runs-refresh").onclick = refreshRuns;
}

async function buildTrees() {
  const f = [], t = [], c = [];
  for (let p = 1; p <= state.run.page_count; p++) {
    const po = await getJSON(`/api/page/${p}/objects`);
    (po.figures || []).forEach(o => f.push(o));
    (po.tables || []).forEach(o => t.push(o));
    (po.common_regions || []).forEach(o => c.push(o));
  }
  fillTree("tree-figures", f, o => `FIG ${o.index} — ${o.title || ""}`);
  fillTree("tree-tables", t, o => `TBL ${o.index} — ${o.title || ""}`);
  fillTree("tree-common", c, o => `${(o.kind || "?").toUpperCase()} ${o.text ? "· " + o.text.slice(0, 18) : ""}`);
}
const pageOf = (oid) => { const m = oid.match(/page(\d+)$/); return m ? +m[1] : 1; };
const isCommon = (oid) => oid.startsWith("common:");

function fillTree(ulId, objs, label) {
  const ul = $(ulId); ul.innerHTML = "";
  objs.forEach(o => {
    const li = document.createElement("li");
    li.dataset.oid = o.object_id;
    li.innerHTML = `${label(o)} <span class="pg">p${pageOf(o.object_id)}</span>`;
    li.onclick = () => selectObject(o.object_id);
    ul.appendChild(li);
  });
}

async function selectObject(oid) {
  state.selected = oid;
  const rs = $("region-select"); rs.innerHTML = "";
  (isCommon(oid) ? ["bbox"] : FIG_TBL).forEach(r => {
    const op = document.createElement("option"); op.value = r; op.textContent = r; rs.appendChild(op);
  });
  state.region = isCommon(oid) ? "bbox" : "body_region";
  rs.value = state.region;
  if (pageOf(oid) !== state.page) await showPage(pageOf(oid)); else drawOverlays();
  document.querySelectorAll("#tree li").forEach(li => li.classList.toggle("selected", li.dataset.oid === oid));
}

async function showPage(page) {
  state.page = page;
  $("page-label").textContent = `page ${page} / ${state.run.page_count}`;
  const img = $("page-img");
  await new Promise(res => { img.onload = res; img.onerror = res; img.src = `/api/page/${page}/png?scale=${SCALE}`; });
  drawOverlays();
}

async function drawOverlays() {
  const ov = await getJSON(`/api/page/${state.page}/overlays`);
  const box = $("overlays"); box.innerHTML = "";
  (ov.overlays || []).forEach(o => {
    if (state.hidden.has(o.kind || "")) return;
    const sel = o.object_id === state.selected && o.region === state.region;
    if (sel && state.mode === "edit") return;  // editable box drawn separately
    box.appendChild(staticBox(o, o.object_id === state.selected));
  });
  if (state.mode === "edit" && state.selected) await drawEditable();
  drawRuler();
}

function px(v) { return v * SCALE; }
function pt(v) { return v / SCALE; }

function staticBox(o, selected) {
  const [x0, y0, x1, y1] = o.bbox;
  const d = document.createElement("div");
  d.className = `ov ${o.kind || ""}` + (selected ? " selected" : "");
  d.style.cssText = `left:${px(x0)}px;top:${px(y0)}px;width:${px(x1 - x0)}px;height:${px(y1 - y0)}px`;
  if (o.region === "body_region" || o.region === "bbox") {
    const l = document.createElement("span"); l.className = "lbl";
    l.textContent = o.object_id.replace(/:page\d+$/, ""); d.appendChild(l);
  }
  d.onclick = () => selectObject(o.object_id);
  return d;
}

async function drawEditable() {
  const obj = await getJSON(`/api/object/${encodeURIComponent(state.selected)}`);
  const bbox = obj.object[state.region]; if (!bbox) return;
  const [x0, y0, x1, y1] = bbox;
  const box = $("overlays");
  const e = document.createElement("div");
  e.className = "ov editing";
  e.style.cssText = `left:${px(x0)}px;top:${px(y0)}px;width:${px(x1 - x0)}px;height:${px(y1 - y0)}px`;
  const cur = bbox.slice();
  ["nw", "ne", "sw", "se", "n", "s", "e", "w"].forEach(h => {
    const hd = document.createElement("div"); hd.className = `handle ${h}`;
    hd.onmousedown = (ev) => startDrag(ev, cur, e, h);
    e.appendChild(hd);
  });
  e.onmousedown = (ev) => { if (ev.target === e) startDrag(ev, cur, e, "move"); };
  box.appendChild(e);
  showCoords(cur);
}

function startDrag(ev, cur, el, mode) {
  ev.preventDefault(); ev.stopPropagation();
  const sx = ev.clientX, sy = ev.clientY, orig = cur.slice();
  function mv(e) {
    const dx = pt(e.clientX - sx), dy = pt(e.clientY - sy);
    let [x0, y0, x1, y1] = orig;
    if (mode === "move") { x0 += dx; x1 += dx; y0 += dy; y1 += dy; }
    if (mode.includes("w")) x0 += dx;
    if (mode.includes("e")) x1 += dx;
    if (mode.includes("n")) y0 += dy;
    if (mode.includes("s")) y1 += dy;
    cur[0] = x0; cur[1] = y0; cur[2] = x1; cur[3] = y1;
    el.style.cssText = `left:${px(Math.min(x0, x1))}px;top:${px(Math.min(y0, y1))}px;width:${px(Math.abs(x1 - x0))}px;height:${px(Math.abs(y1 - y0))}px`;
    showCoords(cur);
  }
  async function up() {
    document.removeEventListener("mousemove", mv); document.removeEventListener("mouseup", up);
    const bbox = [Math.min(cur[0], cur[2]), Math.min(cur[1], cur[3]), Math.max(cur[0], cur[2]), Math.max(cur[1], cur[3])]
      .map(v => Math.round(v * 100) / 100);
    const res = await postJSON("/api/edit/bbox", { object_id: state.selected, region: state.region, bbox });
    if (!res.ok) { alert(`${res.error_code}: ${res.message}`); }
    else { state.dirty = true; updateDirty(true); }
    drawOverlays();
  }
  document.addEventListener("mousemove", mv); document.addEventListener("mouseup", up);
}

function showCoords(b) {
  $("readout").textContent =
    `${state.region}: [${b.map(v => Math.round(v * 10) / 10).join(", ")}]  (PDF pt, top-left)`;
}

// ---- ruler (client-side only) ----
function stageClickToPt(ev) {
  const r = $("page-stage").getBoundingClientRect();
  return [pt(ev.clientX - r.left), pt(ev.clientY - r.top)];
}
function onStageClick(ev) {
  if (state.mode !== "ruler") return;
  if (state.ruler.length >= 2) state.ruler = [];
  state.ruler.push(stageClickToPt(ev));
  if (state.ruler.length === 2) {
    const [s, e] = state.ruler, dx = e[0] - s[0], dy = e[1] - s[1];
    $("readout").textContent =
      `ruler  start [${s.map(n => n.toFixed(1)).join(", ")}]  end [${e.map(n => n.toFixed(1)).join(", ")}]  ` +
      `dx ${dx.toFixed(1)}  dy ${dy.toFixed(1)}  dist ${Math.hypot(dx, dy).toFixed(1)}`;
  }
  drawOverlays();
}
function drawRuler() {
  if (state.mode !== "ruler") return;
  const box = $("overlays");
  state.ruler.forEach(p => {
    const m = document.createElement("div"); m.className = "ruler-pt";
    m.style.cssText = `left:${px(p[0]) - 3}px;top:${px(p[1]) - 3}px`; box.appendChild(m);
  });
}

// ---- save ----
async function refreshDirty() { const s = await getJSON("/api/edit-state"); updateDirty(s.dirty); }
function updateDirty(d) {
  state.dirty = d;
  const b = $("dirty-badge");
  b.textContent = d ? "unsaved" : "saved";
  b.className = d ? "dirty" : "clean";
}

function setMode(m) {
  state.mode = m;
  ["view", "edit", "ruler"].forEach(x => $("mode-" + x).classList.toggle("active", x === m));
  $("page-stage").style.cursor = m === "ruler" ? "crosshair" : "default";
  if (m !== "ruler") state.ruler = [];
  drawOverlays();
}

function wireToolbar() {
  document.querySelectorAll('#toolbar input[data-kind]').forEach(cb => {
    cb.onchange = () => { cb.checked ? state.hidden.delete(cb.dataset.kind) : state.hidden.add(cb.dataset.kind); drawOverlays(); };
  });
  $("toggle-all").onclick = () => {
    const bs = document.querySelectorAll('#toolbar input[data-kind]');
    const anyOn = [...bs].some(b => b.checked);
    bs.forEach(b => { b.checked = !anyOn; b.checked ? state.hidden.delete(b.dataset.kind) : state.hidden.add(b.dataset.kind); });
    drawOverlays();
  };
  $("mode-view").onclick = () => setMode("view");
  $("mode-edit").onclick = () => setMode("edit");
  $("mode-ruler").onclick = () => setMode("ruler");
  $("region-select").onchange = (e) => { state.region = e.target.value; drawOverlays(); };
  $("prev").onclick = () => { if (state.page > 1) showPage(state.page - 1); };
  $("next").onclick = () => { if (state.page < state.run.page_count) showPage(state.page + 1); };
  $("page-stage").onclick = onStageClick;
  $("save").onclick = async () => {
    const r = await postJSON("/api/save", {}); if (r.ok) updateDirty(false); else alert(`${r.error_code}: ${r.message}`);
  };
  $("save-as").onclick = async () => {
    const path = prompt("Save As (relative to run dir):", "versions/edit_1.json"); if (!path) return;
    const r = await postJSON("/api/save-as", { path }); if (r.ok) updateDirty(false); else alert(`${r.error_code}: ${r.message}`);
  };
  $("export-pkg").onclick = async () => {
    const r = await postJSON("/api/export/downstream", {});
    alert(r.ok ? `downstream package: ${r.objects} objects, ${r.crops} crops\n${r.package_manifest}` : `${r.error_code}: ${r.error}`);
  };
}

boot();
