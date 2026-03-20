import cadquery as cq
import plotly.graph_objects as go
import pytest
from unittest.mock import patch

from cadquery_simpleviewer.viewer import (
    _build_traces,
    _axes_from_string,
    _axis_style,
    _equal_ranges,
    _expand_for_plane,
    _is_point,
    _point_to_xyz,
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


@pytest.fixture
def vec():
    return cq.Vector(1.0, 2.0, 3.0)


def _capture_fig(obj, **kwargs):
    captured = {}

    def fake_show(self):
        captured["fig"] = self

    with patch("cadquery_simpleviewer.viewer.go.Figure.show", fake_show):
        show(obj, **kwargs)

    return captured["fig"]


# ── _is_point ────────────────────────────────────────────────────────────────

def test_is_point_vector():
    assert _is_point(cq.Vector(1, 2, 3)) == True

def test_is_point_list_of_three():
    assert _is_point([1.0, 2.0, 3.0]) == True

def test_is_point_tuple_of_three():
    assert _is_point((1, 2, 3)) == True

def test_is_point_int_list():
    assert _is_point([0, 0, 0]) == True

def test_is_point_wrong_length():
    assert _is_point([1.0, 2.0]) == False

def test_is_point_wrong_type():
    assert _is_point("not a point") == False

def test_is_point_workplane(box):
    assert _is_point(box) == False


# ── _point_to_xyz ─────────────────────────────────────────────────────────────

def test_point_to_xyz_from_vector():
    x, y, z = _point_to_xyz(cq.Vector(1.0, 2.0, 3.0))
    assert (x, y, z) == (1.0, 2.0, 3.0)

def test_point_to_xyz_from_list():
    x, y, z = _point_to_xyz([4.0, 5.0, 6.0])
    assert (x, y, z) == (4.0, 5.0, 6.0)

def test_point_to_xyz_from_tuple():
    x, y, z = _point_to_xyz((7, 8, 9))
    assert (x, y, z) == (7.0, 8.0, 9.0)

def test_point_to_xyz_int_inputs():
    x, y, z = _point_to_xyz([1, 2, 3])
    assert isinstance(x, float)


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
    assert _axes_from_string("x")  == (True, False, False)

def test_axes_y():
    assert _axes_from_string("y")  == (False, True, False)

def test_axes_z():
    assert _axes_from_string("z")  == (False, False, True)

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

def test_equal_ranges_single_point_has_nonzero_range():
    """A single point (all spans=0) must still produce a nonzero range."""
    x_r, y_r, z_r = _equal_ranges(1, 1, 2, 2, 3, 3, padding=0)
    assert x_r[1] - x_r[0] > 0
    assert y_r[1] - y_r[0] > 0
    assert z_r[1] - z_r[0] > 0


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


# ── _build_traces — mesh objects ─────────────────────────────────────────────

def test_build_traces_single_mesh(box):
    traces, *_ = _build_traces(box, None, None, 1.0, 0.1, None)
    assert len(traces) == 1
    assert isinstance(traces[0], go.Mesh3d)

def test_build_traces_mesh_names(box):
    traces, *_ = _build_traces([box], ["Box"], None, 1.0, 0.1, None)
    assert traces[0].name == "Box"

def test_build_traces_mesh_default_names(box):
    traces, *_ = _build_traces([box], None, None, 1.0, 0.1, None)
    assert traces[0].name == "Object 1"

def test_build_traces_mesh_color(box):
    traces, *_ = _build_traces([box], None, ["navy"], 1.0, 0.1, None)
    assert traces[0].color == "navy"

def test_build_traces_mesh_opacity(box):
    traces, *_ = _build_traces([box], None, None, 0.5, 0.1, None)
    assert traces[0].opacity == 0.5

def test_build_traces_mesh_has_geometry(box):
    traces, *_ = _build_traces(box, None, None, 1.0, 0.1, None)
    assert len(traces[0].x) > 0 and len(traces[0].i) > 0


# ── _build_traces — point objects ─────────────────────────────────────────────

def test_build_traces_vector_produces_scatter3d(vec):
    traces, *_ = _build_traces([vec], None, None, 1.0, 0.1, None)
    assert isinstance(traces[0], go.Scatter3d)

def test_build_traces_list_point_produces_scatter3d():
    traces, *_ = _build_traces([[1, 2, 3]], None, None, 1.0, 0.1, None)
    assert isinstance(traces[0], go.Scatter3d)

def test_build_traces_point_mode_is_markers(vec):
    traces, *_ = _build_traces([vec], None, None, 1.0, 0.1, None)
    assert traces[0].mode == "markers"

def test_build_traces_point_coordinates(vec):
    traces, *_ = _build_traces([vec], None, None, 1.0, 0.1, None)
    t = traces[0]
    assert t.x[0] == vec.x
    assert t.y[0] == vec.y
    assert t.z[0] == vec.z

def test_build_traces_point_name(vec):
    traces, *_ = _build_traces([vec], ["P1"], None, 1.0, 0.1, None)
    assert traces[0].name == "P1"

def test_build_traces_custom_points_display(vec):
    pd = dict(size=10, color="blue", symbol="square")
    traces, *_ = _build_traces([vec], None, None, 1.0, 0.1, pd)
    marker = traces[0].marker
    assert marker.size == 10
    assert marker.color == "blue"
    assert marker.symbol == "square"

def test_build_traces_default_point_color_is_red(vec):
    traces, *_ = _build_traces([vec], None, None, 1.0, 0.1, None)
    assert traces[0].marker.color == "red"


# ── _build_traces — mixed objects ─────────────────────────────────────────────

def test_build_traces_mixed_types(box, vec):
    traces, all_x, all_y, all_z = _build_traces(
        [box, vec], None, None, 1.0, 0.1, None
    )
    assert len(traces) == 2
    assert isinstance(traces[0], go.Mesh3d)
    assert isinstance(traces[1], go.Scatter3d)

def test_build_traces_mixed_bounding_box_includes_points(box):
    far_point = cq.Vector(100, 100, 100)
    traces, all_x, all_y, all_z = _build_traces(
        [box, far_point], None, None, 1.0, 0.1, None
    )
    assert max(all_x) == 100.0
    assert max(all_y) == 100.0
    assert max(all_z) == 100.0

def test_build_traces_mesh_color_index_skips_points(box, cylinder, vec):
    """Point objects must not consume a slot in the mesh color palette."""
    traces, *_ = _build_traces(
        [box, vec, cylinder], None, None, 1.0, 0.1, None
    )
    mesh_colors = [t.color for t in traces if isinstance(t, go.Mesh3d)]
    # box gets color index 0, cylinder gets color index 1 — vec is skipped
    assert mesh_colors[0] != mesh_colors[1]


# ── show — general ────────────────────────────────────────────────────────────

def test_show_runs_with_mesh(box):
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
        show(box)

def test_show_runs_with_vector(vec):
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
        show(vec)

def test_show_runs_with_list_point():
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
        show([1.0, 2.0, 3.0])

def test_show_runs_mixed(box, vec):
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
        show([box, vec])

def test_show_with_plane(box):
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
        show(box, z=0)

def test_show_invalid_axes_raises(box):
    with pytest.raises(ValueError):
        with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
            show(box, visible_axes="w")

def test_show_points_display_accepted(vec):
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
        show(vec, points_display=dict(size=10, color="blue"))


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

def test_camera_is_dropdown(box):
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
    for b in _capture_fig(box).layout.updatemenus[3].buttons:
        assert b.args[0].get("scene.aspectmode") == "manual"

def test_camera_buttons_restore_aspectratio(box):
    for b in _capture_fig(box).layout.updatemenus[3].buttons:
        ratio = b.args[0].get("scene.aspectratio", {})
        assert ratio.get("x") == 1
        assert ratio.get("y") == 1
        assert ratio.get("z") == 1


# ── show — axis visibility ───────────────────────────────────────────────────

def test_none_axes_hides_all(box):
    fig = _capture_fig(box, visible_axes=None)
    assert fig.layout.scene.xaxis.showbackground == False
    assert fig.layout.scene.yaxis.showbackground == False
    assert fig.layout.scene.zaxis.showbackground == False

def test_xyz_shows_all(box):
    fig = _capture_fig(box, visible_axes="xyz")
    assert fig.layout.scene.xaxis.showbackground == True
    assert fig.layout.scene.yaxis.showbackground == True
    assert fig.layout.scene.zaxis.showbackground == True

def test_yz_hides_x(box):
    assert _capture_fig(box, visible_axes="yz").layout.scene.xaxis.showbackground == False
