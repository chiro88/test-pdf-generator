"""D3 validation: frozen fixture promotion (promote_keep_cases.py / promote.py).

This is the focused D3 check requested in the handoff; the full D6 pytest trio
(test_rtm_factory_generation / test_rtm_frozen_fixtures /
test_rtm_detector_compare_contract) is intentionally NOT built here.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FACTORY_DIR = ROOT / "picker_cmc_v1" / "tests" / "fixtures" / "rtm_factory"
sys.path.insert(0, str(FACTORY_DIR))

from rtm_factory.promote import PromotionError, parse_index_decisions, promote  # noqa: E402

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _build_gallery(root: Path, decisions: dict[str, str]) -> Path:
    """Create a minimal fake gallery: MANIFEST.json + index.md + case dirs."""
    gallery = root / "rtm_gallery"
    gallery.mkdir()
    cases = []
    rows = [
        "| case_id | thumbnail | axis tags | realism 1-5 | keep/drop | critique |",
        "|---|---|---|---|---|---|",
    ]
    for cid, decision in decisions.items():
        cdir = gallery / cid
        cdir.mkdir()
        (cdir / f"{cid}.pdf").write_bytes(b"%PDF-1.7\n%mock\n")
        (cdir / f"{cid}.truth.json").write_text(json.dumps({"case_id": cid, "pages": []}), encoding="utf-8")
        (cdir / f"{cid}.notes.md").write_text(f"notes for {cid}\n", encoding="utf-8")
        (cdir / f"{cid}.p01.png").write_bytes(PNG_MAGIC + b"\x00")
        cases.append({
            "case_id": cid,
            "axes": {"demo": cid},
            "realistic": True,
            "pdf": f"{cid}/{cid}.pdf",
            "truth": f"{cid}/{cid}.truth.json",
            "preview": f"{cid}/{cid}.p01.png",
            "page_count": 1,
            "coverage_tags": [f"demo:{cid}"],
        })
        rows.append(f"| `{cid}` | ![]({cid}/{cid}.p01.png) | demo={cid} |  | {decision} |  |")
    (gallery / "MANIFEST.json").write_text(
        json.dumps({"schema_version": "rtm-gallery-v0", "coordinate_unit": "pdf_pt",
                    "coordinate_origin": "top-left", "cases": cases}, indent=2),
        encoding="utf-8",
    )
    (gallery / "index.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return gallery


def test_parse_index_decisions_skips_header_and_separator() -> None:
    text = (
        "| case_id | thumbnail | axis tags | realism 1-5 | keep/drop | critique |\n"
        "|---|---|---|---|---|---|\n"
        "| `a` | x | t |  | keep |  |\n"
        "| `b` | x | t |  | drop |  |\n"
    )
    d = parse_index_decisions(text)
    assert d == {"a": "keep", "b": "drop"}


def test_promote_keeps_only_keep_rows(tmp_path: Path) -> None:
    # keep 2, drop 1, blank 1
    gallery = _build_gallery(tmp_path, {"k1": "keep", "k2": "KEEP", "d1": "drop", "b1": ""})
    out = tmp_path / "rtm_frozen"
    result = promote(gallery, out)

    assert sorted(result["selected"]) == ["k1", "k2"]
    assert sorted(result["dropped"]) == ["b1", "d1"]
    assert result["selection_source"] == "index.md"
    # only the 2 keep dirs copied
    assert {p.name for p in out.iterdir() if p.is_dir()} == {"k1", "k2"}
    for cid in ("k1", "k2"):
        assert (out / cid / f"{cid}.pdf").exists()
        assert (out / cid / f"{cid}.truth.json").exists()
        assert (out / cid / f"{cid}.notes.md").exists()
        assert (out / cid / f"{cid}.p01.png").read_bytes().startswith(PNG_MAGIC)

    manifest = json.loads((out / "MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "rtm-frozen-v0"
    assert manifest["source_gallery_schema_version"] == "rtm-gallery-v0"
    assert manifest["promotion"]["selected_count"] == 2
    assert manifest["promotion"]["dropped_count"] == 2
    assert manifest["promotion"]["selection_source"] == "index.md"
    assert len(manifest["cases"]) == 2
    assert (out / "index.md").exists()
    # gallery must be untouched (still has all 4 cases)
    gal_manifest = json.loads((gallery / "MANIFEST.json").read_text(encoding="utf-8"))
    assert len(gal_manifest["cases"]) == 4


def test_existing_output_fails_without_force(tmp_path: Path) -> None:
    gallery = _build_gallery(tmp_path, {"k1": "keep", "d1": "drop"})
    out = tmp_path / "rtm_frozen"
    promote(gallery, out)
    with pytest.raises(PromotionError):
        promote(gallery, out)  # exists, no force
    # --force regenerates
    result = promote(gallery, out, force=True)
    assert result["selected"] == ["k1"]


def test_empty_selection_fails_unless_allowed(tmp_path: Path) -> None:
    gallery = _build_gallery(tmp_path, {"b1": "", "d1": "drop"})
    out = tmp_path / "rtm_frozen"
    with pytest.raises(PromotionError):
        promote(gallery, out)
    result = promote(gallery, out, allow_empty=True)
    assert result["selected"] == []
    manifest = json.loads((out / "MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["promotion"]["selected_count"] == 0


def test_cli_keep_override(tmp_path: Path) -> None:
    gallery = _build_gallery(tmp_path, {"k1": "", "k2": "", "k3": ""})  # nothing kept in index
    out = tmp_path / "rtm_frozen"
    result = promote(gallery, out, keep_override=["k1", "k3"])
    assert sorted(result["selected"]) == ["k1", "k3"]
    assert result["selection_source"] == "cli"
    with pytest.raises(PromotionError):
        promote(gallery, tmp_path / "other", keep_override=["nope"])  # unknown id
