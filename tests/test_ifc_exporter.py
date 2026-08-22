import pytest

ifcopenshell = pytest.importorskip("ifcopenshell", exc_type=ImportError)
cq = pytest.importorskip("cadquery")
b3d = pytest.importorskip("build123d")

from cadquery_simpleviewer.ifc_exporter import (
    resolve_ifc_export_config, resolve_ifc_config, export_ifc_proxy,
)


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
def straight_edge():
    return cq.Edge.makeLine(cq.Vector(0, 0, 0), cq.Vector(5, 0, 0))


def _open(path):
    return ifcopenshell.open(str(path))


# ── resolve_ifc_export_config ────────────────────────────────────────────────

def test_resolve_ifc_export_config_false_disables():
    assert resolve_ifc_export_config(False) is None

def test_resolve_ifc_export_config_none_is_default_on():
    assert resolve_ifc_export_config(None) == {"filename": "model.ifc", "unit": "M"}

def test_resolve_ifc_export_config_dict_merges_with_default():
    cfg = resolve_ifc_export_config({"filename": "custom.ifc"})
    assert cfg == {"filename": "custom.ifc", "unit": "M"}

def test_resolve_ifc_export_config_empty_dict_uses_defaults():
    assert resolve_ifc_export_config({}) == {"filename": "model.ifc", "unit": "M"}

def test_resolve_ifc_export_config_unit_override():
    cfg = resolve_ifc_export_config({"unit": "MM"})
    assert cfg["unit"] == "MM"

def test_resolve_ifc_export_config_invalid_unit_raises():
    with pytest.raises(ValueError, match="Unsupported export unit"):
        resolve_ifc_export_config({"unit": "IN"})


# ── resolve_ifc_config ────────────────────────────────────────────────────────

def test_resolve_ifc_config_none_defaults_to_ifc4():
    assert resolve_ifc_config(None) == {"schema": "IFC4"}

def test_resolve_ifc_config_empty_dict_uses_default():
    assert resolve_ifc_config({}) == {"schema": "IFC4"}

def test_resolve_ifc_config_schema_override():
    assert resolve_ifc_config({"schema": "IFC2X3"}) == {"schema": "IFC2X3"}


# ── export_ifc_proxy — basic structure ───────────────────────────────────────

def test_export_ifc_single_cadquery_solid(tmp_path, cq_box):
    target = tmp_path / "box.ifc"
    result = export_ifc_proxy(cq_box, str(target))
    assert result == str(target)
    assert target.exists()
    assert target.stat().st_size > 0

def test_export_ifc_single_build123d_solid(tmp_path, b3d_box):
    target = tmp_path / "box.ifc"
    export_ifc_proxy(b3d_box, str(target))
    assert target.exists()
    assert target.stat().st_size > 0

def test_export_ifc_creates_missing_directories(tmp_path, cq_box):
    target = tmp_path / "nested" / "dir" / "box.ifc"
    export_ifc_proxy(cq_box, str(target))
    assert target.exists()

def test_export_ifc_no_solids_raises(tmp_path, straight_edge):
    target = tmp_path / "edge.ifc"
    with pytest.raises(ValueError, match="No solid"):
        export_ifc_proxy(straight_edge, str(target))

def test_export_ifc_invalid_unit_raises(tmp_path, cq_box):
    target = tmp_path / "box.ifc"
    with pytest.raises(ValueError, match="Unsupported export unit"):
        export_ifc_proxy(cq_box, str(target), unit="IN")

def test_export_ifc_skips_non_solid_items(tmp_path, cq_box, straight_edge):
    target = tmp_path / "box_and_edge.ifc"
    export_ifc_proxy([cq_box, straight_edge], str(target))
    model = _open(target)
    assert len(model.by_type("IfcBuildingElementProxy")) == 1


# ── export_ifc_proxy — mixed kernel (divergence from export_step) ───────────

def test_export_ifc_mixed_libraries_does_not_raise(tmp_path, cq_box, b3d_box):
    target = tmp_path / "mixed.ifc"
    export_ifc_proxy([cq_box, b3d_box], str(target))
    model = _open(target)
    assert len(model.by_type("IfcBuildingElementProxy")) == 2


# ── export_ifc_proxy — spatial hierarchy validity ────────────────────────────

def test_export_ifc_has_minimal_spatial_hierarchy(tmp_path, cq_box):
    target = tmp_path / "box.ifc"
    export_ifc_proxy(cq_box, str(target))
    model = _open(target)
    assert len(model.by_type("IfcProject")) == 1
    assert len(model.by_type("IfcSite")) == 1
    assert len(model.by_type("IfcBuilding")) == 1
    assert len(model.by_type("IfcBuildingStorey")) == 1

def test_export_ifc_proxies_contained_in_storey(tmp_path, cq_box, cq_box2):
    target = tmp_path / "boxes.ifc"
    export_ifc_proxy([cq_box, cq_box2], str(target))
    model = _open(target)
    storey = model.by_type("IfcBuildingStorey")[0]
    proxies = set(model.by_type("IfcBuildingElementProxy"))
    contained = set()
    for rel in model.by_type("IfcRelContainedInSpatialStructure"):
        assert rel.RelatingStructure == storey
        contained.update(rel.RelatedElements)
    assert contained == proxies

def test_export_ifc_no_extraneous_semantics(tmp_path, cq_box):
    target = tmp_path / "box.ifc"
    export_ifc_proxy(cq_box, str(target))
    model = _open(target)
    assert model.by_type("IfcPropertySet") == []
    assert model.by_type("IfcMaterial") == []
    assert model.by_type("IfcRelDefinesByType") == []


# ── export_ifc_proxy — naming ────────────────────────────────────────────────

def test_export_ifc_default_names(tmp_path, cq_box, cq_box2):
    target = tmp_path / "boxes.ifc"
    export_ifc_proxy([cq_box, cq_box2], str(target))
    model = _open(target)
    names = {p.Name for p in model.by_type("IfcBuildingElementProxy")}
    assert names == {"Object 1", "Object 2"}

def test_export_ifc_custom_names(tmp_path, cq_box, cq_box2):
    target = tmp_path / "boxes.ifc"
    export_ifc_proxy([cq_box, cq_box2], str(target), names=["Bracket", "Bolt"])
    model = _open(target)
    names = {p.Name for p in model.by_type("IfcBuildingElementProxy")}
    assert names == {"Bracket", "Bolt"}


# ── export_ifc_proxy — geometry round-trip ───────────────────────────────────

def test_export_ifc_geometry_vertex_count_matches_tessellation(tmp_path, cq_box):
    from cadquery_simpleviewer.adapters import cadquery_adapter

    tolerance, angular_tolerance = 0.01, 0.1
    x, y, z, *_ = cadquery_adapter.tessellate_solid(cq_box, tolerance, angular_tolerance)

    target = tmp_path / "box.ifc"
    export_ifc_proxy(
        cq_box, str(target),
        tessellation_tolerance=tolerance, angular_tolerance=angular_tolerance,
    )
    model = _open(target)
    mesh = model.by_type("IfcPolygonalFaceSet")[0]
    assert len(mesh.Coordinates.CoordList) == len(x)

def test_export_ifc_geometry_bbox_matches_tessellation(tmp_path, cq_box):
    from cadquery_simpleviewer.adapters import cadquery_adapter

    tolerance, angular_tolerance = 0.01, 0.1
    x, y, z, *_ = cadquery_adapter.tessellate_solid(cq_box, tolerance, angular_tolerance)

    target = tmp_path / "box.ifc"
    export_ifc_proxy(
        cq_box, str(target),
        tessellation_tolerance=tolerance, angular_tolerance=angular_tolerance,
    )
    model = _open(target)
    mesh = model.by_type("IfcPolygonalFaceSet")[0]
    coords = mesh.Coordinates.CoordList
    ifc_x = [c[0] for c in coords]
    ifc_y = [c[1] for c in coords]
    ifc_z = [c[2] for c in coords]

    assert min(ifc_x) == pytest.approx(min(x))
    assert max(ifc_x) == pytest.approx(max(x))
    assert min(ifc_y) == pytest.approx(min(y))
    assert max(ifc_y) == pytest.approx(max(y))
    assert min(ifc_z) == pytest.approx(min(z))
    assert max(ifc_z) == pytest.approx(max(z))

def test_export_ifc_unit_m_declares_metre_no_prefix(tmp_path, cq_box):
    target = tmp_path / "box.ifc"
    export_ifc_proxy(cq_box, str(target), unit="M")
    model = _open(target)
    length_units = [u for u in model.by_type("IfcSIUnit") if u.UnitType == "LENGTHUNIT"]
    assert len(length_units) == 1
    assert length_units[0].Prefix is None

def test_export_ifc_unit_mm_declares_milli_prefix(tmp_path, cq_box):
    target = tmp_path / "box.ifc"
    export_ifc_proxy(cq_box, str(target), unit="MM")
    model = _open(target)
    length_units = [u for u in model.by_type("IfcSIUnit") if u.UnitType == "LENGTHUNIT"]
    assert len(length_units) == 1
    assert length_units[0].Prefix == "MILLI"


# ── export_ifc_proxy — schema ────────────────────────────────────────────────

def test_export_ifc_default_schema_is_ifc4(tmp_path, cq_box):
    target = tmp_path / "box.ifc"
    export_ifc_proxy(cq_box, str(target))
    model = _open(target)
    assert model.schema == "IFC4"

def test_export_ifc_schema_override(tmp_path, cq_box):
    target = tmp_path / "box.ifc"
    export_ifc_proxy(cq_box, str(target), schema="IFC2X3")
    model = _open(target)
    assert model.schema == "IFC2X3"
