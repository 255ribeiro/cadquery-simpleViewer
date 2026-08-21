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
    assert resolve_export_config(None) == {"filename": "model.step"}

def test_resolve_export_config_dict_merges_with_default():
    cfg = resolve_export_config({"filename": "custom.step"})
    assert cfg == {"filename": "custom.step"}

def test_resolve_export_config_empty_dict_uses_default_filename():
    assert resolve_export_config({}) == {"filename": "model.step"}


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
