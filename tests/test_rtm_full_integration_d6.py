"""D6 full integration gates: RTM factory workflow end-to-end in pytest.

Builds the real gallery once (module fixture) and drives promotion, compare,
and overlay against it. This validates the *factory/promotion/compare/overlay*
pipeline as a reproducible gate — it is NOT a detector correctness test.
"""
from __future__ import annotations

import copy
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FACTORY_DIR = ROOT / "picker_cmc_v1" / "tests" / "fixtures" / "rtm_factory"
sys.path.insert(0, str(FACTORY_DIR))

from rtm_factory.cli import generate_gallery, main  # noqa: E402
from rtm_factory.promote import promote  # noqa: E402

pytestmark = pytest.mark.rtm_integration

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
PERTURB_CASE = "core_figure_caption_bottom"


@pytest.fixture(scope="module")
def gallery(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("rtm_d6") / "rtm_gallery"
    generate_gallery(out)
    return out


def _synth_detected(gallery_root: Path) -> dict:
    manifest = json.loads((gallery_root / "MANIFEST.json").read_text(encoding="utf-8"))
    cases = []
    for entry in manifest["cases"]:
        cid = entry["case_id"]
        truth = json.loads((gallery_root / cid / f"{cid}.truth.json").read_text(encoding="utf-8"))
        pages = [{
            "page": p["page"],
            "common_regions": [{k: r[k] for k in ("kind", "bbox", "text") if k in r} for r in p["common_regions"]],
            "figures": p["figures"], "tables": p["tables"],
        } for p in truth["pages"]]
        cases.append({"case_id": cid, "pages": pages})
    return {"schema_version": "detector-output-v0", "coordinate_unit": "pdf_pt",
            "coordinate_origin": "top-left", "cases": cases}


def _write(path: Path, obj) -> Path:
    path.write_text(json.dumps(obj), encoding="utf-8")
    return path


def _perturb(det: dict, fn) -> dict:
    out = copy.deepcopy(det)
    for c in out["cases"]:
        if c["case_id"] == PERTURB_CASE:
            fn(c)
    return out


# 1. Full gallery generation gate --------------------------------------------
@pytest.mark.slow
def test_full_gallery_generation_gate(gallery):
    manifest = json.loads((gallery / "MANIFEST.json").read_text(encoding="utf-8"))
    assert (gallery / "index.md").exists()
    assert 30 <= len(manifest["cases"]) <= 50
    cov = manifest["coverage_summary"]
    assert cov["missing"] == [] and cov["below_min"] == []
    assert manifest["generation"]["seed"] == 1234
    report = json.loads((gallery / "SELF_CHECK_REPORT.json").read_text(encoding="utf-8"))
    assert report["text_overlap"]["failures"] == []
    for entry in manifest["cases"][:5]:
        cid = entry["case_id"]
        assert (gallery / cid / f"{cid}.pdf").exists()
        assert (gallery / cid / f"{cid}.truth.json").exists()
        assert (gallery / cid / f"{cid}.notes.md").exists()
        assert (gallery / cid / f"{cid}.p01.png").read_bytes().startswith(PNG_MAGIC)


# 2. Promotion integration gate ----------------------------------------------
def test_promotion_gate(gallery, tmp_path):
    work = tmp_path / "rtm_gallery"
    shutil.copytree(gallery, work)
    manifest = json.loads((work / "MANIFEST.json").read_text(encoding="utf-8"))
    keep_ids = [c["case_id"] for c in manifest["cases"][:3]]
    # mark keep in the index.md keep/drop column (5th data cell)
    lines = (work / "index.md").read_text(encoding="utf-8").splitlines()
    out_lines = []
    for line in lines:
        if line.startswith("|") and any(f"`{cid}`" in line for cid in keep_ids):
            cells = line.split("|")
            if len(cells) >= 7:
                cells[5] = " keep "
            line = "|".join(cells)
        out_lines.append(line)
    (work / "index.md").write_text("\n".join(out_lines) + "\n", encoding="utf-8")

    frozen = tmp_path / "rtm_frozen"
    result = promote(work, frozen)
    assert sorted(result["selected"]) == sorted(keep_ids)
    assert {p.name for p in frozen.iterdir() if p.is_dir()} == set(keep_ids)
    fm = json.loads((frozen / "MANIFEST.json").read_text(encoding="utf-8"))
    assert fm["promotion"]["selected_count"] == len(keep_ids)
    assert fm["promotion"]["dropped_count"] == len(manifest["cases"]) - len(keep_ids)
    # gallery copy untouched (still full)
    assert len(json.loads((work / "MANIFEST.json").read_text())["cases"]) == len(manifest["cases"])


# 3. Compare integration gate ------------------------------------------------
def test_compare_gate(gallery, tmp_path):
    det = _synth_detected(gallery)
    perfect = _write(tmp_path / "perfect.json", det)
    assert main(["compare", "--truth-root", str(gallery), "--detected", str(perfect),
                 "--out", str(tmp_path / "c_ok"), "--json"]) == 0

    def shift(c):
        for r in ("caption_region", "body_region"):
            c["pages"][0]["figures"][0][r][1] += 30
            c["pages"][0]["figures"][0][r][3] += 30
    bad = _write(tmp_path / "bad.json", _perturb(det, shift))
    assert main(["compare", "--truth-root", str(gallery), "--detected", str(bad),
                 "--out", str(tmp_path / "c_bad"), "--json"]) == 1

    missing = _write(tmp_path / "missing.json", _perturb(det, lambda c: c["pages"][0].__setitem__("figures", [])))
    assert main(["compare", "--truth-root", str(gallery), "--detected", str(missing),
                 "--out", str(tmp_path / "c_miss"), "--json"]) == 1

    def add_extra(c):
        extra = copy.deepcopy(c["pages"][0]["figures"][0]); extra["index"] = "9.9"
        c["pages"][0]["figures"].append(extra)
    extra = _write(tmp_path / "extra.json", _perturb(det, add_extra))
    assert main(["compare", "--truth-root", str(gallery), "--detected", str(extra),
                 "--out", str(tmp_path / "c_extra"), "--json"]) == 1
    assert main(["compare", "--truth-root", str(gallery), "--detected", str(extra),
                 "--out", str(tmp_path / "c_extra2"), "--allow-extra", "--json"]) == 0


# 4. Overlay integration gate ------------------------------------------------
def test_overlay_gate(gallery, tmp_path):
    det = _synth_detected(gallery)

    def shift(c):
        c["pages"][0]["figures"][0]["caption_region"][1] += 30
        c["pages"][0]["figures"][0]["caption_region"][3] += 30
    bad = _write(tmp_path / "bad.json", _perturb(det, shift))
    cmp_out = tmp_path / "cmp"
    main(["compare", "--truth-root", str(gallery), "--detected", str(bad), "--out", str(cmp_out), "--json"])

    ov = tmp_path / "ov"
    code = main(["overlay", "--truth-root", str(gallery), "--detected", str(bad),
                 "--compare-report", str(cmp_out / "compare_report.json"), "--out", str(ov), "--json"])
    assert code == 0
    manifest = json.loads((ov / "overlay_manifest.json").read_text(encoding="utf-8"))
    assert (ov / "index.md").exists()
    pages = [(c["case_id"], p["page"]) for c in manifest["cases"] for p in c["pages"]]
    assert pages == [(PERTURB_CASE, 1)]  # failures-only → only the failed page
    page = manifest["cases"][0]["pages"][0]
    assert (ov / page["overlay_png"]).read_bytes().startswith(PNG_MAGIC)
    assert page["failures_drawn"] > 0
