import re

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
# Neither CadQuery nor build123d's geometry kernel enforces a unit — a
# modeled dimension of 5 is just the number 5 until export declares what it
# means. This project's modeling convention treats that number as already
# being in the target unit (e.g. a slider/box value of 10 means 10 real
# meters), so export_step() must declare the requested unit *without*
# rescaling the coordinates. These tests check both halves of that
# contract: the raw CARTESIAN_POINT values in the file are untouched
# (still "5", not "0.005"), and re-importing via CadQuery's unit-aware STEP
# importer confirms the file really does declare "5 <unit>" — e.g. a "5"
# exported as meters round-trips to 5000 in CadQuery's own mm-based working
# units (5 real meters), not 5 (which would mean the file was mislabeled
# and actually describes a 5mm object).

def _imported_xlen(step_path):
    imported = cq.importers.importStep(str(step_path))
    return imported.val().BoundingBox().xlen

def _cartesian_point_values(step_path):
    """All raw numeric values written into CARTESIAN_POINT entities."""
    content = step_path.read_text()
    return [
        float(v)
        for line in content.splitlines() if "CARTESIAN_POINT" in line
        for v in re.findall(r"-?\d+\.?\d*(?:E[+-]?\d+)?", line.split("(", 2)[-1])
    ]

def test_export_step_cadquery_meters_default_keeps_raw_values(tmp_path, cq_box):
    target = tmp_path / "box.step"
    export_step(cq_box, str(target))  # default unit — "M"
    # cq_box is 5 wide -> half-extent 2.5, unscaled (not 0.0025)
    assert 2.5 in _cartesian_point_values(target)

def test_export_step_cadquery_meters_default_declares_5_meters(tmp_path, cq_box):
    target = tmp_path / "box.step"
    export_step(cq_box, str(target))  # default unit — "M"
    # cq_box modeled with raw value 5 -> declared as 5 meters -> re-imports
    # as 5000 in CadQuery's own mm-based working units (5 real meters).
    assert _imported_xlen(target) == pytest.approx(5000.0)

def test_export_step_cadquery_millimeters_keeps_raw_values_and_scale(tmp_path, cq_box):
    target = tmp_path / "box.step"
    export_step(cq_box, str(target), unit="MM")
    assert _imported_xlen(target) == pytest.approx(5.0)  # unchanged, as before this feature

def test_export_step_build123d_meters_default_keeps_raw_values(tmp_path, b3d_box):
    target = tmp_path / "box.step"
    export_step(b3d_box, str(target))  # default unit — "M"
    # b3d_box is a 4-wide cube -> half-extent 2.0, unscaled (not 0.002)
    assert 2.0 in _cartesian_point_values(target)

def test_export_step_build123d_meters_default_declares_4_meters(tmp_path, b3d_box):
    target = tmp_path / "box.step"
    export_step(b3d_box, str(target))  # default unit — "M"
    # b3d_box modeled with raw value 4 -> declared as 4 meters -> re-imports
    # as 4000 in CadQuery's own mm-based working units (4 real meters).
    assert _imported_xlen(target) == pytest.approx(4000.0)

def test_export_step_build123d_millimeters_keeps_raw_values_and_scale(tmp_path, b3d_box):
    target = tmp_path / "box.step"
    export_step(b3d_box, str(target), unit="MM")
    assert _imported_xlen(target) == pytest.approx(4.0)  # unchanged, as before this feature

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
