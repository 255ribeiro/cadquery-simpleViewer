import cadquery as cq
import plotly.graph_objects as go
import pytest
from unittest.mock import patch

from cadquery_simpleviewer.viewer import (
    _build_traces,
    _bounding_box,
    _axes_from_string,
    _axis_style,
    _equal_ranges,
    _expand_for_plane,
    _geometry_center_normalized,
    show,
)


# ── fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def box():
    return cq.Workplane("XY").box(5, 3, 2)


@pytest.fixture
def cylinder():
    return cq.Workplane("XY").cylinder(6, 1)


@pytest.fixture
def two_objects(box, cylinder):
    return [box, cylinder]


def _capture_fig(obj, **kwargs):
    captured = {}

    def fake_show(self):
        captured["fig"] = self

    with patch("cadquery_simpleviewer.viewer.go.Figure.show", fake_show):
        show(obj, **kwargs)

    return captured["fig"]


# ── _axis_style ──────────────────────────────────────────────────────────────

def test_axis_style_visible():
    s = _axis_style(True)
    assert s["showbackground"] == True
    assert s["showticklabels"] == True
    assert s["showgrid"] == True
    assert "rgb" in s["backgroundcolor"]
    assert s["gridcolor"] == "white"


def test_axis_style_hidden():
    s = _axis_style(False)
    assert s["showbackground"] == False
    assert s["showticklabels"] == False
    assert s["showgrid"] == False
    assert s["showspikes"] == False


# ── _axes_from_string ────────────────────────────────────────────────────────

def test_axes_none_hides_all():
    assert _axes_from_string(None) == (False, False, False)

def test_axes_xyz():
    assert _axes_from_string("xyz") == (True, True, True)

def test_axes_x():
    assert _axes_from_string("x") == (True, False, False)

def test_axes_y():
    assert _axes_from_string("y") == (False, True, False)

def test_axes_z():
    assert _axes_from_string("z") == (False, False, True)

def test_axes_xy():
    assert _axes_from_string("xy") == (True, True, False)

def test_axes_xz():
    assert _axes_from_string("xz") == (True, False, True)

def test_axes_yz():
    assert _axes_from_string("yz") == (False, True, True)

def test_axes_invalid_raises():
    with pytest.raises(ValueError):
        _axes_from_string("w")


# ── _equal_ranges ────────────────────────────────────────────────────────────

def test_equal_ranges_all_spans_equal():
    x_r, y_r, z_r = _equal_ranges(-1, 1, -2, 2, -3, 3, padding=0)
    spans = [r[1] - r[0] for r in [x_r, y_r, z_r]]
    assert abs(spans[0] - spans[1]) < 1e-9
    assert abs(spans[1] - spans[2]) < 1e-9

def test_equal_ranges_largest_span_dominates():
    x_r, y_r, z_r = _equal_ranges(-5, 5, -1, 1, -1, 1, padding=0)
    for r in [x_r, y_r, z_r]:
        assert abs((r[1] - r[0]) - 10.0) < 1e-9

def test_equal_ranges_centered():
    x_r, y_r, z_r = _equal_ranges(0, 4, 0, 4, 0, 4, padding=0)
    for r in [x_r, y_r, z_r]:
        assert abs((r[0] + r[1]) / 2 - 2.0) < 1e-9


# ── _expand_for_plane ────────────────────────────────────────────────────────

def test_expand_for_plane_grows_xy():
    x_r, y_r, z_r = _expand_for_plane([-1, 1], [-1, 1], [-1, 1],
                                        plane_size=50, z_level=0)
    assert x_r[1] - x_r[0] >= 100
    assert y_r[1] - y_r[0] >= 100

def test_expand_for_plane_includes_z_level():
    x_r, y_r, z_r = _expand_for_plane([-1, 1], [-1, 1], [0, 5],
                                        plane_size=2, z_level=-3)
    assert z_r[0] <= -3

def test_expand_for_plane_keeps_equal_spans():
    x_r, y_r, z_r = _expand_for_plane([-1, 1], [-1, 1], [-1, 1],
                                        plane_size=20, z_level=0)
    spans = [r[1] - r[0] for r in [x_r, y_r, z_r]]
    assert abs(spans[0] - spans[1]) < 1e-9
    assert abs(spans[1] - spans[2]) < 1e-9

def test_plane_size_respected_in_figure(box):
    fig = _capture_fig(box, z=0, plane_size=100)
    x_span = fig.layout.scene.xaxis.range[1] - fig.layout.scene.xaxis.range[0]
    assert x_span >= 200


# ── _geometry_center_normalized ──────────────────────────────────────────────

def test_geometry_center_normalized_at_center_of_range():
    """
    When geometry fills the full range, the normalized center must be 0,0,0.
    """
    geom_bbox  = (-5, 5, -5, 5, -5, 5)
    final_ranges = ([-5, 5], [-5, 5], [-5, 5])
    center = _geometry_center_normalized(geom_bbox, final_ranges)
    assert abs(center["x"]) < 1e-9
    assert abs(center["y"]) < 1e-9
    assert abs(center["z"]) < 1e-9


def test_geometry_center_normalized_offset():
    """
    When geometry is at the bottom of an expanded range (e.g. plane added),
    the normalized center must be negative (below scene center).
    """
    # Geometry goes from 0 to 2 in z, but range expanded to -10..10 for plane
    geom_bbox   = (-1, 1, -1, 1, 0, 2)
    final_ranges = ([-10, 10], [-10, 10], [-10, 10])
    center = _geometry_center_normalized(geom_bbox, final_ranges)
    # geom z center = 1.0, range = -10..10, normalized = 2*(1-(-10))/20 - 1 = 0.1
    assert abs(center["z"] - 0.1) < 1e-9


def test_camera_center_looks_at_geometry_not_plane(box):
    """
    With a large base plane, the camera center z coordinate must be > 0
    (pointing above the plane, at the geometry), not at scene center z=0.
    """
    fig = _capture_fig(box, z=-20, plane_size=200)
    cz = fig.layout.scene.camera.center.z
    # Scene is expanded downward for the plane, so geometry center is above
    # the scene midpoint — camera.center.z must be positive
    assert cz > 0


def test_camera_buttons_point_at_geometry(box):
    """Every camera button must include a center that points at the geometry."""
    fig = _capture_fig(box, z=-10, plane_size=100)
    for button in fig.layout.updatemenus[3].buttons:
        cam = button.args[0]["scene.camera"]
        assert "center" in cam


# ── _build_traces ────────────────────────────────────────────────────────────

def test_build_traces_single(box):
    traces = _build_traces(box, None, None, 1.0, 0.1)
    assert len(traces) == 1
    assert isinstance(traces[0], go.Mesh3d)

def test_build_traces_list(two_objects):
    assert len(_build_traces(two_objects, None, None, 1.0, 0.1)) == 2

def test_build_traces_names(two_objects):
    traces = _build_traces(two_objects, ["Box", "Cylinder"], None, 1.0, 0.1)
    assert traces[0].name == "Box"
    assert traces[1].name == "Cylinder"

def test_build_traces_default_names(two_objects):
    traces = _build_traces(two_objects, None, None, 1.0, 0.1)
    assert traces[0].name == "Object 1"
    assert traces[1].name == "Object 2"

def test_build_traces_color(box):
    assert _build_traces(box, None, ["red"], 1.0, 0.1)[0].color == "red"

def test_build_traces_opacity(box):
    assert _build_traces(box, None, None, 0.5, 0.1)[0].opacity == 0.5

def test_build_traces_geometry(box):
    trace = _build_traces(box, None, None, 1.0, 0.1)[0]
    assert len(trace.x) > 0 and len(trace.i) > 0


# ── _bounding_box ────────────────────────────────────────────────────────────

def test_bounding_box_valid(box):
    traces = _build_traces(box, None, None, 1.0, 0.1)
    xmin, xmax, ymin, ymax, zmin, zmax = _bounding_box(traces)
    assert xmin < xmax and ymin < ymax and zmin < zmax

def test_bounding_box_ignores_plane():
    from cadquery_simpleviewer.plane import _base_plane
    plane = _base_plane(size=100, color="white", opacity=1.0, z=0)
    obj = cq.Workplane("XY").box(2, 2, 2)
    traces = _build_traces(obj, None, None, 1.0, 0.1)
    traces.insert(0, plane)
    xmin, xmax, _, _, _, _ = _bounding_box(traces)
    assert xmax < 10


# ── show — general ────────────────────────────────────────────────────────────

def test_show_runs(box):
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
        show(box)

def test_show_with_plane(box):
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
        show(box, z=0)

def test_show_invalid_axes_raises(box):
    with pytest.raises(ValueError):
        with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
            show(box, visible_axes="w")


# ── show — visible_axes ───────────────────────────────────────────────────────

def test_none_axes_hides_all(box):
    fig = _capture_fig(box, visible_axes=None)
    assert fig.layout.scene.xaxis.showbackground == False
    assert fig.layout.scene.yaxis.showbackground == False
    assert fig.layout.scene.zaxis.showbackground == False
    assert fig.layout.scene.xaxis.showticklabels == False

def test_xyz_shows_all(box):
    fig = _capture_fig(box, visible_axes="xyz")
    assert fig.layout.scene.xaxis.showbackground == True
    assert fig.layout.scene.yaxis.showbackground == True
    assert fig.layout.scene.zaxis.showbackground == True

def test_yz_hides_x(box):
    assert _capture_fig(box, visible_axes="yz").layout.scene.xaxis.showbackground == False


# ── show — equal scale ───────────────────────────────────────────────────────

def test_aspectmode_is_manual(box):
    assert _capture_fig(box).layout.scene.aspectmode == "manual"

def test_aspectratio_1_1_1(box):
    r = _capture_fig(box).layout.scene.aspectratio
    assert r.x == 1 and r.y == 1 and r.z == 1

def test_equal_axis_ranges(box):
    scene = _capture_fig(box).layout.scene
    x_span = scene.xaxis.range[1] - scene.xaxis.range[0]
    y_span = scene.yaxis.range[1] - scene.yaxis.range[0]
    z_span = scene.zaxis.range[1] - scene.zaxis.range[0]
    assert abs(x_span - y_span) < 1e-9
    assert abs(y_span - z_span) < 1e-9


# ── show — updatemenus ───────────────────────────────────────────────────────

def test_four_updatemenus(box):
    assert len(_capture_fig(box).layout.updatemenus) == 4

def test_axis_menus_are_buttons(box):
    fig = _capture_fig(box)
    for i in range(3):
        assert fig.layout.updatemenus[i].type == "buttons"

def test_camera_menu_is_dropdown(box):
    assert _capture_fig(box).layout.updatemenus[3].type == "dropdown"

def test_axis_toggles_two_buttons(box):
    fig = _capture_fig(box)
    for i in range(3):
        assert len(fig.layout.updatemenus[i].buttons) == 2

def test_camera_two_buttons(box):
    assert len(_capture_fig(box).layout.updatemenus[3].buttons) == 2

def test_camera_labels(box):
    labels = [b.label for b in _capture_fig(box).layout.updatemenus[3].buttons]
    assert "Perspective"  in labels
    assert "Orthographic" in labels

def test_axis_on_filled_symbol(box):
    fig = _capture_fig(box)
    for i in range(3):
        assert "●" in fig.layout.updatemenus[i].buttons[0].label

def test_axis_off_hollow_symbol(box):
    fig = _capture_fig(box)
    for i in range(3):
        assert "○" in fig.layout.updatemenus[i].buttons[1].label


# ── show — camera restores aspect ────────────────────────────────────────────

def test_camera_buttons_restore_aspectmode(box):
    for button in _capture_fig(box).layout.updatemenus[3].buttons:
        assert button.args[0].get("scene.aspectmode") == "manual"

def test_camera_buttons_restore_aspectratio(box):
    for button in _capture_fig(box).layout.updatemenus[3].buttons:
        ratio = button.args[0].get("scene.aspectratio", {})
        assert ratio.get("x") == 1
        assert ratio.get("y") == 1
        assert ratio.get("z") == 1
