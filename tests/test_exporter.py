import pytest

cq = pytest.importorskip("cadquery")
b3d = pytest.importorskip("build123d")

from cadquery_simpleviewer.exporter import resolve_export_config, export_step


# ── fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def cq_box():
    return cq.Workplane("XY").box(5, 3, 2)


@pytest.fixture
def cq_box2():
    return cq.Workplane("XY").box(2, 2, 2)


@pytest.fixture
def b3d_box():
    with b3d.BuildPart() as bp:
        b3d.Box(4, 4, 4)
    return bp.part


@pytest.fixture
def b3d_box2():
    with b3d.BuildPart() as bp:
        b3d.Box(1, 1, 1)
    return bp.part


@pytest.fixture
def straight_edge():
    return cq.Edge.makeLine(cq.Vector(0, 0, 0), cq.Vector(5, 0, 0))


# ── resolve_export_config ───────────────────────────────────────────────────

def test_resolve_export_config_false_disables():
    assert resolve_export_config(False) is None

def test_resolve_export_config_none_is_default_on():
    assert resolve_export_config(None) == {"filename": "model.step", "unit": "M"}

def test_resolve_export_config_dict_merges_with_default():
    cfg = resolve_export_config({"filename": "custom.step"})
    assert cfg == {"filename": "custom.step", "unit": "M"}

def test_resolve_export_config_empty_dict_uses_defaults():
    assert resolve_export_config({}) == {"filename": "model.step", "unit": "M"}

def test_resolve_export_config_unit_override():
    cfg = resolve_export_config({"unit": "MM"})
    assert cfg["unit"] == "MM"

def test_resolve_export_config_invalid_unit_raises():
    with pytest.raises(ValueError, match="Unsupported export unit"):
        resolve_export_config({"unit": "IN"})


# ── export_step — cadquery ───────────────────────────────────────────────────

def test_export_step_single_cadquery_solid(tmp_path, cq_box):
    target = tmp_path / "box.step"
    result = export_step(cq_box, str(target))
    assert result == str(target)
    assert target.exists()
    assert target.stat().st_size > 0

def test_export_step_multiple_cadquery_solids_combined(tmp_path, cq_box, cq_box2):
    target = tmp_path / "boxes.step"
    export_step([cq_box, cq_box2], str(target))
    assert target.exists()


# ── export_step — build123d ──────────────────────────────────────────────────

def test_export_step_single_build123d_solid(tmp_path, b3d_box):
    target = tmp_path / "box.step"
    export_step(b3d_box, str(target))
    assert target.exists()
    assert target.stat().st_size > 0

def test_export_step_multiple_build123d_solids_combined(tmp_path, b3d_box, b3d_box2):
    target = tmp_path / "boxes.step"
    export_step([b3d_box, b3d_box2], str(target))
    assert target.exists()


# ── export_step — edge cases ─────────────────────────────────────────────────

def test_export_step_mixed_libraries_raises(tmp_path, cq_box, b3d_box):
    target = tmp_path / "mixed.step"
    with pytest.raises(ValueError, match="mix"):
        export_step([cq_box, b3d_box], str(target))

def test_export_step_no_solids_raises(tmp_path, straight_edge):
    target = tmp_path / "edge.step"
    with pytest.raises(ValueError, match="No solid"):
        export_step(straight_edge, str(target))

def test_export_step_creates_missing_directories(tmp_path, cq_box):
    target = tmp_path / "nested" / "dir" / "box.step"
    export_step(cq_box, str(target))
    assert target.exists()

def test_export_step_skips_non_solid_items(tmp_path, cq_box, straight_edge):
    target = tmp_path / "box_and_edge.step"
    export_step([cq_box, straight_edge], str(target))
    assert target.exists()

def test_export_step_invalid_unit_raises(tmp_path, cq_box):
    target = tmp_path / "box.step"
    with pytest.raises(ValueError, match="Unsupported export unit"):
        export_step(cq_box, str(target), unit="IN")


# ── export_step — unit correctness ───────────────────────────────────────────
#
# CadQuery and build123d both always represent geometry internally in
# millimeters. A STEP file is only correct if its declared header unit and
# its raw coordinate magnitudes agree on the model's true physical size —
# get that wrong (as build123d's own export_step(unit=...) does — see
# _export_b3d()'s docstring in exporter.py) and lenient viewers still open
# the file (just at the wrong scale) while stricter ones (e.g. Revit) can
# reject it outright. These tests round-trip through CadQuery's STEP
# importer, which is unit-aware, to verify the exported file's declared
# size actually matches the original model — not just that a file exists.

def _imported_xlen(step_path):
    imported = cq.importers.importStep(str(step_path))
    return imported.val().BoundingBox().xlen

def test_export_step_cadquery_meters_default_preserves_true_size(tmp_path, cq_box):
    target = tmp_path / "box.step"
    export_step(cq_box, str(target))  # default unit — "M"
    assert _imported_xlen(target) == pytest.approx(5.0)  # cq_box is 5mm x 3mm x 2mm

def test_export_step_cadquery_millimeters_preserves_true_size(tmp_path, cq_box):
    target = tmp_path / "box.step"
    export_step(cq_box, str(target), unit="MM")
    assert _imported_xlen(target) == pytest.approx(5.0)

def test_export_step_build123d_meters_default_preserves_true_size(tmp_path, b3d_box):
    target = tmp_path / "box.step"
    export_step(b3d_box, str(target))  # default unit — "M"
    assert _imported_xlen(target) == pytest.approx(4.0)  # b3d_box is 4mm cube

def test_export_step_build123d_millimeters_preserves_true_size(tmp_path, b3d_box):
    target = tmp_path / "box.step"
    export_step(b3d_box, str(target), unit="MM")
    assert _imported_xlen(target) == pytest.approx(4.0)

def test_export_step_cadquery_meters_header_declares_metre(tmp_path, cq_box):
    target = tmp_path / "box.step"
    export_step(cq_box, str(target))
    content = target.read_text()
    assert "SI_UNIT($,.METRE.)" in content
    assert "SI_UNIT(.MILLI.,.METRE.)" not in content

def test_export_step_build123d_meters_header_declares_metre(tmp_path, b3d_box):
    target = tmp_path / "box.step"
    export_step(b3d_box, str(target))
    content = target.read_text()
    assert "SI_UNIT($,.METRE.)" in content
    assert "SI_UNIT(.MILLI.,.METRE.)" not in content
