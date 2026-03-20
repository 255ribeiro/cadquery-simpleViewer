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
    _is_edge,
    _is_wire,
    _point_to_xyz,
    _sample_edge,
    _sample_wire,
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
def vec():
    return cq.Vector(1.0, 2.0, 3.0)


@pytest.fixture
def straight_edge():
    return cq.Edge.makeLine(cq.Vector(0, 0, 0), cq.Vector(5, 0, 0))


@pytest.fixture
def arc_edge():
    return cq.Edge.makeCircle(radius=3.0)


@pytest.fixture
def rect_wire():
    return cq.Wire.makeRect(4.0, 2.0)


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

def test_is_point_list():
    assert _is_point([1.0, 2.0, 3.0]) == True

def test_is_point_tuple():
    assert _is_point((1, 2, 3)) == True

def test_is_point_wrong_length():
    assert _is_point([1.0, 2.0]) == False

def test_is_point_wrong_type():
    assert _is_point("abc") == False

def test_is_point_workplane(box):
    assert _is_point(box) == False


# ── _is_edge / _is_wire ───────────────────────────────────────────────────────

def test_is_edge_with_edge(straight_edge):
    assert _is_edge(straight_edge) == True

def test_is_edge_with_wire(rect_wire):
    assert _is_edge(rect_wire) == False

def test_is_edge_with_vector():
    assert _is_edge(cq.Vector(1, 2, 3)) == False

def test_is_wire_with_wire(rect_wire):
    assert _is_wire(rect_wire) == True

def test_is_wire_with_edge(straight_edge):
    assert _is_wire(straight_edge) == False

def test_is_wire_with_workplane(box):
    assert _is_wire(box) == False


# ── _point_to_xyz ─────────────────────────────────────────────────────────────

def test_point_to_xyz_vector():
    x, y, z = _point_to_xyz(cq.Vector(1.0, 2.0, 3.0))
    assert (x, y, z) == (1.0, 2.0, 3.0)

def test_point_to_xyz_list():
    x, y, z = _point_to_xyz([4.0, 5.0, 6.0])
    assert (x, y, z) == (4.0, 5.0, 6.0)

def test_point_to_xyz_returns_floats():
    x, y, z = _point_to_xyz([1, 2, 3])
    assert isinstance(x, float)


# ── _sample_edge ─────────────────────────────────────────────────────────────

def test_sample_edge_returns_correct_count(straight_edge):
    x, y, z = _sample_edge(straight_edge, 10)
    assert len(x) == 11   # n+1 points for n samples
    assert len(y) == 11
    assert len(z) == 11

def test_sample_edge_straight_endpoints(straight_edge):
    x, y, z = _sample_edge(straight_edge, 5)
    assert abs(x[0] - 0.0) < 1e-6
    assert abs(x[-1] - 5.0) < 1e-6

def test_sample_edge_arc_stays_on_circle(arc_edge):
    x, y, z = _sample_edge(arc_edge, 36)
    for i in range(len(x)):
        r = (x[i] ** 2 + y[i] ** 2) ** 0.5
        assert abs(r - 3.0) < 1e-4


# ── _sample_wire ─────────────────────────────────────────────────────────────

def test_sample_wire_returns_lists(rect_wire):
    x, y, z = _sample_wire(rect_wire, 10)
    assert isinstance(x, list)
    assert isinstance(y, list)
    assert isinstance(z, list)

def test_sample_wire_contains_none_separators(rect_wire):
    x, y, z = _sample_wire(rect_wire, 10)
    assert None in x

def test_sample_wire_has_coordinates(rect_wire):
    x, y, z = _sample_wire(rect_wire, 10)
    non_none = [v for v in x if v is not None]
    assert len(non_none) > 0


# ── _build_traces — edges and wires ──────────────────────────────────────────

def test_build_traces_edge_produces_scatter3d(straight_edge):
    traces, *_ = _build_traces([straight_edge], None, None, 1.0, 0.1, None, None)
    assert isinstance(traces[0], go.Scatter3d)

def test_build_traces_edge_mode_is_lines(straight_edge):
    traces, *_ = _build_traces([straight_edge], None, None, 1.0, 0.1, None, None)
    assert traces[0].mode == "lines"

def test_build_traces_wire_produces_scatter3d(rect_wire):
    traces, *_ = _build_traces([rect_wire], None, None, 1.0, 0.1, None, None)
    assert isinstance(traces[0], go.Scatter3d)

def test_build_traces_edge_name(straight_edge):
    traces, *_ = _build_traces([straight_edge], ["Edge A"], None, 1.0, 0.1, None, None)
    assert traces[0].name == "Edge A"

def test_build_traces_edge_default_name(straight_edge):
    traces, *_ = _build_traces([straight_edge], None, None, 1.0, 0.1, None, None)
    assert traces[0].name == "Object 1"

def test_build_traces_custom_lines_display(straight_edge):
    ld = dict(color="blue", width=4, mode="lines+markers")
    traces, *_ = _build_traces([straight_edge], None, None, 1.0, 0.1, None, ld)
    assert traces[0].line.color == "blue"
    assert traces[0].line.width == 4
    assert traces[0].mode == "lines+markers"

def test_build_traces_edge_contributes_to_bbox(straight_edge):
    traces, all_x, all_y, all_z = _build_traces(
        [straight_edge], None, None, 1.0, 0.1, None, None
    )
    assert max(all_x) >= 5.0

def test_build_traces_mixed_solid_edge_wire(box, straight_edge, rect_wire):
    traces, *_ = _build_traces(
        [box, straight_edge, rect_wire], None, None, 1.0, 0.1, None, None
    )
    assert len(traces) == 3
    assert isinstance(traces[0], go.Mesh3d)
    assert isinstance(traces[1], go.Scatter3d)
    assert isinstance(traces[2], go.Scatter3d)

def test_build_traces_mesh_color_index_skips_edges(box, straight_edge, cylinder):
    """Edge and wire objects must not consume mesh color palette slots."""
    traces, *_ = _build_traces(
        [box, straight_edge, cylinder], None, None, 1.0, 0.1, None, None
    )
    mesh_colors = [t.color for t in traces if isinstance(t, go.Mesh3d)]
    assert mesh_colors[0] != mesh_colors[1]


# ── _axis_style ──────────────────────────────────────────────────────────────

def test_axis_style_visible():
    s = _axis_style(True)
    assert s["showbackground"] == True
    assert s["showticklabels"] == True
    assert s["showgrid"] == True

def test_axis_style_hidden():
    s = _axis_style(False)
    assert s["showbackground"] == False
    assert s["showticklabels"] == False
    assert s["showgrid"] == False


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

def test_axes_invalid_raises():
    with pytest.raises(ValueError):
        _axes_from_string("w")


# ── _equal_ranges ────────────────────────────────────────────────────────────

def test_equal_ranges_all_spans_equal():
    x_r, y_r, z_r = _equal_ranges(-1, 1, -2, 2, -3, 3, padding=0)
    spans = [r[1] - r[0] for r in [x_r, y_r, z_r]]
    assert abs(spans[0] - spans[1]) < 1e-9
    assert abs(spans[1] - spans[2]) < 1e-9

def test_equal_ranges_single_point_nonzero():
    x_r, y_r, z_r = _equal_ranges(1, 1, 2, 2, 3, 3, padding=0)
    assert x_r[1] - x_r[0] > 0


# ── _expand_for_plane ────────────────────────────────────────────────────────

def test_expand_for_plane_grows_xy():
    x_r, y_r, z_r = _expand_for_plane([-1, 1], [-1, 1], [-1, 1],
                                        plane_size=50, z_level=0)
    assert x_r[1] - x_r[0] >= 100

def test_expand_for_plane_includes_z_level():
    x_r, y_r, z_r = _expand_for_plane([-1, 1], [-1, 1], [0, 5],
                                        plane_size=2, z_level=-3)
    assert z_r[0] <= -3


# ── show — general ────────────────────────────────────────────────────────────

def test_show_runs_with_mesh(box):
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
        show(box)

def test_show_runs_with_edge(straight_edge):
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
        show(straight_edge)

def test_show_runs_with_wire(rect_wire):
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
        show(rect_wire)

def test_show_runs_with_arc(arc_edge):
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
        show(arc_edge)

def test_show_runs_with_vector(vec):
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
        show(vec)

def test_show_runs_mixed_all_types(box, straight_edge, rect_wire, vec):
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
        show([box, straight_edge, rect_wire, vec])

def test_show_lines_display_accepted(straight_edge):
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
        show(straight_edge, lines_display=dict(color="blue", width=3, samples=20))

def test_show_invalid_axes_raises(box):
    with pytest.raises(ValueError):
        with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
            show(box, visible_axes="w")


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

def test_camera_two_buttons(box):
    assert len(_capture_fig(box).layout.updatemenus[3].buttons) == 2

def test_camera_labels(box):
    labels = [b.label for b in _capture_fig(box).layout.updatemenus[3].buttons]
    assert "Perspective"  in labels
    assert "Orthographic" in labels


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
