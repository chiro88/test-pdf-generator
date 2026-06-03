"use strict";
// picker_cmc read-only viewer (D23). No editing/save/ruler.
const SCALE = 1.5;
const state = { run: null, page: 1, selected: null, hidden: new Set() };

async function getJSON(url) { const r = await fetch(url); return r.json(); }

async function boot() {
  state.run = await getJSON("/api/run");
  if (!state.run.ok) { document.getElementById("run-meta").textContent = "failed to load run"; return; }
  document.getElementById("run-meta").textContent =
    `pdf: ${state.run.source_pdf}\npages: ${state.run.page_count}\n` +
    `coords: ${state.run.coordinate_unit} / ${state.run.coordinate_origin}`;
  await buildTrees();
  wireToolbar();
  showPage(1);
}

async function buildTrees() {
  const figs = [], tbls = [], comm = [];
  for (let p = 1; p <= state.run.page_count; p++) {
    const po = await getJSON(`/api/page/${p}/objects`);
    (po.figures || []).forEach(o => figs.push(o));
    (po.tables || []).forEach(o => tbls.push(o));
    (po.common_regions || []).forEach(o => comm.push(o));
  }
  fillTree("tree-figures", figs, o => `FIG ${o.index} — ${o.title || ""}`);
  fillTree("tree-tables", tbls, o => `TBL ${o.index} — ${o.title || ""}`);
  fillTree("tree-common", comm, o => `${(o.kind || "?").toUpperCase()} ${o.text ? "· " + o.text.slice(0, 18) : ""}`);
}

function pageOf(objectId) { const m = objectId.match(/page(\d+)$/); return m ? +m[1] : 1; }

function fillTree(ulId, objs, label) {
  const ul = document.getElementById(ulId);
  ul.innerHTML = "";
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
  const page = pageOf(oid);
  if (page !== state.page) await showPage(page);
  else drawOverlays();
  document.querySelectorAll("#tree li").forEach(li =>
    li.classList.toggle("selected", li.dataset.oid === oid));
}

async function showPage(page) {
  state.page = page;
  document.getElementById("page-label").textContent = `page ${page} / ${state.run.page_count}`;
  const img = document.getElementById("page-img");
  await new Promise(res => { img.onload = res; img.onerror = res; img.src = `/api/page/${page}/png?scale=${SCALE}`; });
  await drawOverlays();
}

async function drawOverlays() {
  const ov = await getJSON(`/api/page/${state.page}/overlays`);
  const box = document.getElementById("overlays");
  box.innerHTML = "";
  (ov.overlays || []).forEach(o => {
    const kind = o.kind || "";
    if (state.hidden.has(kind)) return;
    const [x0, y0, x1, y1] = o.bbox;
    const d = document.createElement("div");
    d.className = `ov ${kind}` + (o.object_id === state.selected ? " selected" : "");
    d.style.left = (x0 * SCALE) + "px"; d.style.top = (y0 * SCALE) + "px";
    d.style.width = ((x1 - x0) * SCALE) + "px"; d.style.height = ((y1 - y0) * SCALE) + "px";
    if (o.region === "body_region" || o.region === "bbox") {
      const lbl = document.createElement("span"); lbl.className = "lbl";
      lbl.textContent = o.object_id.replace(/:page\d+$/, "");
      d.appendChild(lbl);
    }
    d.onclick = () => selectObject(o.object_id);
    box.appendChild(d);
  });
}

function wireToolbar() {
  document.querySelectorAll('#toolbar input[data-kind]').forEach(cb => {
    cb.onchange = () => { if (cb.checked) state.hidden.delete(cb.dataset.kind); else state.hidden.add(cb.dataset.kind); drawOverlays(); };
  });
  document.getElementById("toggle-all").onclick = () => {
    const boxes = document.querySelectorAll('#toolbar input[data-kind]');
    const anyOn = [...boxes].some(b => b.checked);
    boxes.forEach(b => { b.checked = !anyOn; b.checked ? state.hidden.delete(b.dataset.kind) : state.hidden.add(b.dataset.kind); });
    drawOverlays();
  };
  document.getElementById("prev").onclick = () => { if (state.page > 1) showPage(state.page - 1); };
  document.getElementById("next").onclick = () => { if (state.page < state.run.page_count) showPage(state.page + 1); };
}

boot();
