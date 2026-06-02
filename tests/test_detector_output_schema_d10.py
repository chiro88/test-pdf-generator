"""D10 contract tests: detector-output-v0 schema validator.

These are CONTRACT tests (structural validity), not detector correctness.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "picker_cmc_v1"))

from detector_output import writer  # noqa: E402
from detector_output.validator import DetectorOutputError, validate_manifest, validate_or_raise  # noqa: E402


def _valid_manifest():
    fig = writer.figure("3-4", "Synthetic", [72, 180, 540, 198], [72, 210, 540, 320], [72, 170, 540, 330],
                        title_position="above", title_body_gap_lines=1)
    tbl = writer.table("3-1", "Synthetic", "tbl_003_001", [72, 360, 540, 378], [72, 390, 540, 480],
                       [72, 352, 540, 488])
    hdr = writer.common_region("header", [48, 18, 564, 54], "Header")
    pg = writer.page(1, common_regions=[hdr], figures=[fig], tables=[tbl])
    return writer.build_manifest([writer.case("c1", "c1/c1.pdf", [pg])])


def test_valid_manifest_passes():
    assert validate_manifest(_valid_manifest()) == []
    validate_or_raise(_valid_manifest())  # no raise


def test_wrong_schema_version_fails():
    m = _valid_manifest(); m["schema_version"] = "wrong"
    assert any("schema_version" in e for e in validate_manifest(m))
    with pytest.raises(DetectorOutputError):
        validate_or_raise(m)


def test_coordinate_origin_must_be_top_left():
    m = _valid_manifest(); m["coordinate_origin"] = "bottom-left"
    assert any("coordinate_origin" in e for e in validate_manifest(m))


def test_coordinate_unit_must_be_pdf_pt():
    m = _valid_manifest(); m["coordinate_unit"] = "px"
    assert any("coordinate_unit" in e for e in validate_manifest(m))


def test_missing_producer_fails():
    m = _valid_manifest(); del m["producer"]
    assert any("producer" in e for e in validate_manifest(m))


def test_missing_figure_region_fails():
    m = _valid_manifest()
    del m["cases"][0]["pages"][0]["figures"][0]["body_region"]
    assert any("body_region" in e for e in validate_manifest(m))


def test_bad_figure_title_position_fails():
    m = _valid_manifest()
    m["cases"][0]["pages"][0]["figures"][0]["title_position"] = "sideways"
    assert any("title_position" in e for e in validate_manifest(m))


def test_missing_table_group_fails():
    m = _valid_manifest()
    del m["cases"][0]["pages"][0]["tables"][0]["table_group_id"]
    assert any("table_group_id" in e for e in validate_manifest(m))


def test_writer_refuses_invalid_manifest(tmp_path):
    m = _valid_manifest(); m["coordinate_origin"] = "bottom-left"
    with pytest.raises(DetectorOutputError):
        writer.write_manifest(tmp_path / "d.json", m)
