import math

import ipywidgets as widgets
import plotly.graph_objects as go
import pytest
from unittest.mock import patch

cq = pytest.importorskip("cadquery")
b3d = pytest.importorskip("build123d")

from cadquery_simpleviewer.viewer import (
    _build_traces,
    _axes_from_string,
    _axis_style,
    _equal_ranges,
    _expand_for_plane,
    _is_plain_point,
    _plain_point_to_xyz,
    show,
)
from cadquery_simpleviewer.adapters.cadquery_adapter import (
    is_point as _is_point,
    is_edge as _is_edge,
    is_wire as _is_wire,
    is_location as _is_location,
    point_to_xyz as _point_to_xyz,
    sample_edge as _sample_edge,
    sample_wire as _sample_wire,
    location_axes as _location_axes,
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
    return cq.Wire.makePolygon(
        [cq.Vector(-2, -1, 0), cq.Vector(2, -1, 0), cq.Vector(2, 1, 0), cq.Vector(-2, 1, 0)],
        close=True,
    )


def _capture_fig(obj, **kwargs):
    captured = {}
    kwargs.setdefault("export", False)
    kwargs.setdefault("export_ifc", False)

    def fake_show(self):
        captured["fig"] = self

    with patch("cadquery_simpleviewer.viewer.go.Figure.show", fake_show):
        show(obj, **kwargs)

    return captured["fig"]


# ── _is_point (cadquery adapter) ───────────────────────────────────────────────

def test_is_point_vector():
    assert _is_point(cq.Vector(1, 2, 3)) == True

def test_is_point_workplane(box):
    assert _is_point(box) == False


# ── _is_plain_point (library-agnostic, viewer.py) ──────────────────────────────

def test_is_plain_point_list():
    assert _is_plain_point([1.0, 2.0, 3.0]) == True

def test_is_plain_point_tuple():
    assert _is_plain_point((1, 2, 3)) == True

def test_is_plain_point_wrong_length():
    assert _is_plain_point([1.0, 2.0]) == False

def test_is_plain_point_wrong_type():
    assert _is_plain_point("abc") == False


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


# ── _is_location / _location_axes (cadquery adapter) ─────────────────────────

def test_is_location_with_plane():
    assert _is_location(cq.Plane(origin=(0, 0, 0))) == True

def test_is_location_with_location():
    assert _is_location(cq.Location((1, 2, 3))) == True

def test_is_location_with_workplane(box):
    assert _is_location(box) == False

def test_location_axes_from_plane():
    plane = cq.Plane(origin=(1, 2, 3), xDir=(1, 0, 0), normal=(0, 0, 1))
    origin, x_tip, y_tip, z_tip = _location_axes(plane, scale=1)
    assert origin == (1.0, 2.0, 3.0)
    assert x_tip == (2.0, 2.0, 3.0)

def test_location_axes_from_location():
    loc = cq.Location((0, 0, 0))
    origin, x_tip, y_tip, z_tip = _location_axes(loc, scale=1)
    assert origin == (0.0, 0.0, 0.0)
    assert x_tip == (1.0, 0.0, 0.0)
    assert z_tip == (0.0, 0.0, 1.0)


# ── _point_to_xyz (cadquery adapter) ────────────────────────────────────────────

def test_point_to_xyz_vector():
    x, y, z = _point_to_xyz(cq.Vector(1.0, 2.0, 3.0))
    assert (x, y, z) == (1.0, 2.0, 3.0)


# ── _plain_point_to_xyz (library-agnostic, viewer.py) ───────────────────────────

def test_plain_point_to_xyz_list():
    x, y, z = _plain_point_to_xyz([4.0, 5.0, 6.0])
    assert (x, y, z) == (4.0, 5.0, 6.0)

def test_plain_point_to_xyz_returns_floats():
    x, y, z = _plain_point_to_xyz([1, 2, 3])
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
    traces, all_x, all_y, all_z, _local_axis_indices = _build_traces(
        [straight_edge], None, None, 1.0, 0.1, None, None
    )
    assert max(all_x) >= 5.0

def test_build_traces_mixed_solid_edge_wire(box, straight_edge, rect_wire):
    """
    Each solid also gets an automatic 3-trace local-axis triad (see
    test_axes.py) immediately after its mesh trace.
    """
    traces, *_ = _build_traces(
        [box, straight_edge, rect_wire], None, None, 1.0, 0.1, None, None
    )
    assert len(traces) == 6
    assert isinstance(traces[0], go.Mesh3d)
    assert all(isinstance(t, go.Mesh3d) for t in traces[1:4])
    assert isinstance(traces[4], go.Scatter3d)
    assert isinstance(traces[5], go.Scatter3d)

def test_build_traces_mesh_color_index_skips_edges(box, straight_edge, cylinder):
    """Edge and wire objects must not consume mesh color palette slots."""
    traces, *_ = _build_traces(
        [box, straight_edge, cylinder], None, None, 1.0, 0.1, None, None
    )
    # Only the solids' own mesh traces carry a `name` — the automatic
    # local-axis triads don't, so this excludes them from the comparison.
    mesh_colors = [t.color for t in traces if isinstance(t, go.Mesh3d) and t.name]
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
        show(box, export=False)

def test_show_runs_with_edge(straight_edge):
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
        show(straight_edge, export=False)

def test_show_runs_with_wire(rect_wire):
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
        show(rect_wire, export=False)

def test_show_runs_with_arc(arc_edge):
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
        show(arc_edge, export=False)

def test_show_runs_with_vector(vec):
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
        show(vec, export=False)

def test_show_runs_mixed_all_types(box, straight_edge, rect_wire, vec):
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
        show([box, straight_edge, rect_wire, vec], export=False)

def test_show_runs_mixed_cadquery_and_build123d(box):
    with b3d.BuildPart() as bp:
        b3d.Box(4, 4, 4)
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
        show([box, bp.part], names=["CadQuery box", "build123d box"], export=False)

def test_show_lines_display_accepted(straight_edge):
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
        show(straight_edge, lines_display=dict(color="blue", width=3, samples=20), export=False)

def test_show_invalid_axes_raises(box):
    with pytest.raises(ValueError):
        with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
            show(box, visible_axes="w", export=False)


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

def test_seven_updatemenus(box):
    assert len(_capture_fig(box).layout.updatemenus) == 7

def test_axis_menus_are_buttons(box):
    fig = _capture_fig(box)
    for i in range(3):
        assert fig.layout.updatemenus[i].type == "buttons"

def test_camera_is_dropdown(box):
    assert _capture_fig(box).layout.updatemenus[5].type == "dropdown"

def test_camera_two_buttons(box):
    assert len(_capture_fig(box).layout.updatemenus[5].buttons) == 2

def test_camera_labels(box):
    labels = [b.label for b in _capture_fig(box).layout.updatemenus[5].buttons]
    assert "Perspective"  in labels
    assert "Orthographic" in labels


# ── show — camera restores aspect ────────────────────────────────────────────

def test_camera_buttons_restore_aspectmode(box):
    for b in _capture_fig(box).layout.updatemenus[5].buttons:
        assert b.args[0].get("scene.aspectmode") == "manual"

def test_camera_buttons_restore_aspectratio(box):
    for b in _capture_fig(box).layout.updatemenus[5].buttons:
        ratio = b.args[0].get("scene.aspectratio", {})
        assert ratio.get("x") == 1
        assert ratio.get("y") == 1
        assert ratio.get("z") == 1


# ── show — reset view button ─────────────────────────────────────────────────

def test_reset_view_is_button(box):
    assert _capture_fig(box).layout.updatemenus[6].type == "buttons"

def test_reset_view_label(box):
    labels = [b.label for b in _capture_fig(box).layout.updatemenus[6].buttons]
    assert "Reset View" in labels

def test_reset_view_restores_default_camera(box):
    button = _capture_fig(box).layout.updatemenus[6].buttons[0]
    camera = button.args[0]["scene.camera"]
    assert camera["eye"] == {"x": 1.5, "y": 1.5, "z": 1.5}
    assert camera["projection"]["type"] == "perspective"

def test_reset_view_restores_aspect(box):
    button = _capture_fig(box).layout.updatemenus[6].buttons[0]
    assert button.args[0]["scene.aspectmode"] == "manual"
    ratio = button.args[0]["scene.aspectratio"]
    assert ratio == {"x": 1, "y": 1, "z": 1}


# ── show — axis triads (Location/Plane objects, world/local toggles) ────────

@pytest.fixture
def cq_plane():
    return cq.Plane(origin=(1, 2, 3))


@pytest.fixture
def b3d_location():
    return b3d.Location((4, 5, 6))


def test_build_traces_location_produces_three_mesh3d(cq_plane):
    traces, *_ = _build_traces([cq_plane], None, None, 1.0, 0.1, None, None)
    assert len(traces) == 3
    assert all(isinstance(t, go.Mesh3d) for t in traces)

def test_build_traces_location_colors_are_distinct_light_rgb(cq_plane):
    traces, *_ = _build_traces([cq_plane], None, None, 1.0, 0.1, None, None)
    colors = [t.color for t in traces]
    assert colors != ["red", "green", "blue"]
    assert len(set(colors)) == 3

def test_build_traces_location_full_opacity(cq_plane):
    """
    Opacity must stay at 1.0 — semi-transparent Mesh3d traces can silently
    fail to render in some Plotly.js/WebGL renderers.
    """
    traces, *_ = _build_traces([cq_plane], None, None, 1.0, 0.1, None, None)
    assert all(t.opacity == 1.0 for t in traces)

def test_build_traces_location_reports_indices(cq_plane, straight_edge):
    traces, all_x, all_y, all_z, local_axis_indices = _build_traces(
        [straight_edge, cq_plane], None, None, 1.0, 0.1, None, None
    )
    assert local_axis_indices == [1, 2, 3]

def test_build_traces_location_scale_applied(cq_plane):
    traces, *_ = _build_traces(
        [cq_plane], None, None, 1.0, 0.1, None, None, axes_scale=10
    )
    x_trace = traces[0]
    assert max(x_trace.x) - x_trace.x[0] == 10

def test_build_traces_build123d_location_supported(b3d_location):
    traces, *_ = _build_traces([b3d_location], None, None, 1.0, 0.1, None, None)
    assert len(traces) == 3
    assert traces[0].x[0] == 4


# ── automatic per-solid local axis triad ────────────────────────────────────

def test_build_traces_solid_gets_automatic_local_axis(box):
    """No Location/Plane/Axis needs to be passed for a solid's own triad."""
    traces, *_, local_axis_indices = _build_traces(
        [box], None, None, 1.0, 0.1, None, None
    )
    assert len(traces) == 4
    assert isinstance(traces[0], go.Mesh3d) and traces[0].name is not None
    assert local_axis_indices == [1, 2, 3]
    assert all(isinstance(traces[i], go.Mesh3d) for i in local_axis_indices)

def test_build_traces_solid_local_axis_at_identity_location(box):
    """box() is untransformed, so its placement Location is identity."""
    traces, *_ = _build_traces([box], None, None, 1.0, 0.1, None, None, axes_scale=1)
    x_axis_trace = traces[1]
    assert x_axis_trace.x[0] == pytest.approx(0.0)
    assert x_axis_trace.y[0] == pytest.approx(0.0)
    assert x_axis_trace.z[0] == pytest.approx(0.0)

def test_build_traces_solid_local_axis_follows_workplane_origin():
    """A Workplane built at a non-origin origin= reports that as its Location."""
    offset_box = cq.Workplane("XY", origin=(6, 4, 0)).box(5, 3, 2)
    traces, *_ = _build_traces([offset_box], None, None, 1.0, 0.1, None, None, axes_scale=1)
    x_axis_trace = traces[1]
    assert x_axis_trace.x[0] == pytest.approx(6.0)
    assert x_axis_trace.y[0] == pytest.approx(4.0)
    assert x_axis_trace.z[0] == pytest.approx(0.0)

def test_build_traces_solid_local_axis_is_not_bbox_center():
    """
    .translate() bakes the move into the geometry itself rather than the
    shape's placement Location, so the automatic triad — which follows
    Location, not the bounding box — stays at the world origin even though
    the solid's bounding box has moved.
    """
    moved_box = cq.Workplane("XY").box(5, 3, 2).translate((6, 4, 0))
    traces, *_ = _build_traces([moved_box], None, None, 1.0, 0.1, None, None, axes_scale=1)
    x_axis_trace = traces[1]
    assert x_axis_trace.x[0] == pytest.approx(0.0)
    assert x_axis_trace.y[0] == pytest.approx(0.0)
    assert x_axis_trace.z[0] == pytest.approx(0.0)

def test_build_traces_solid_local_axis_follows_build123d_moved():
    """
    build123d's .moved() does populate the shape's placement Location
    (unlike CadQuery's .translate(), which bakes the move into the
    geometry) — the automatic triad must follow it.
    """
    moved_box = b3d.Box(5, 3, 2).moved(b3d.Location((6, 4, 0)))
    traces, *_ = _build_traces([moved_box], None, None, 1.0, 0.1, None, None, axes_scale=1)
    x_axis_trace = traces[1]
    assert x_axis_trace.x[0] == pytest.approx(6.0)
    assert x_axis_trace.y[0] == pytest.approx(4.0)
    assert x_axis_trace.z[0] == pytest.approx(0.0)

def test_build_traces_solid_local_axis_respects_visible_flag(box):
    traces, *_ = _build_traces(
        [box], None, None, 1.0, 0.1, None, None, local_axes_visible=True
    )
    assert all(t.visible is True for t in traces[1:4])

    traces, *_ = _build_traces(
        [box], None, None, 1.0, 0.1, None, None, local_axes_visible=False
    )
    assert all(t.visible is False for t in traces[1:4])

def test_build_traces_solid_local_axis_scale_normalized_to_solid_size(box):
    """
    box() is 5x3x2 (max span 5) — the arm length must be derived from that
    span, not a flat axes_scale, so it always pokes out past the solid
    regardless of how big or small it is.
    """
    traces, *_ = _build_traces([box], None, None, 1.0, 0.1, None, None, axes_scale=1)
    x_axis_trace = traces[1]
    # index 11 is the cylinder's top-cap *center* (see _cylinder_mesh in
    # axes.py) — the true tip; the last vertex is a rim point, offset from
    # the tip by the arm's radius, not the arm's own length.
    tip = (x_axis_trace.x[11], x_axis_trace.y[11], x_axis_trace.z[11])
    arm_length = math.dist((0, 0, 0), tip)
    assert arm_length == pytest.approx(5 * 0.75)

def test_build_traces_solid_local_axis_scale_is_a_multiplier(box):
    """axes_scale still works as a multiplier on top of the normalized base."""
    traces, *_ = _build_traces([box], None, None, 1.0, 0.1, None, None, axes_scale=2)
    x_axis_trace = traces[1]
    tip = (x_axis_trace.x[11], x_axis_trace.y[11], x_axis_trace.z[11])
    arm_length = math.dist((0, 0, 0), tip)
    assert arm_length == pytest.approx(5 * 0.75 * 2)

def test_build_traces_solid_and_its_local_axis_share_legendgroup(box):
    """
    So that hiding the solid via its Plotly legend entry hides its
    automatic axis triad along with it (see legend groupclick="togglegroup"
    in _build_figure).
    """
    traces, *_ = _build_traces([box], None, None, 1.0, 0.1, None, None)
    mesh_trace = traces[0]
    axis_traces = traces[1:4]
    assert mesh_trace.legendgroup is not None
    assert all(t.legendgroup == mesh_trace.legendgroup for t in axis_traces)

def test_build_traces_different_solids_get_different_legendgroups(box, cylinder):
    traces, *_ = _build_traces([box, cylinder], None, None, 1.0, 0.1, None, None)
    box_mesh, cylinder_mesh = traces[0], traces[4]
    assert box_mesh.legendgroup != cylinder_mesh.legendgroup

def test_show_runs_with_location(cq_plane):
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
        show([cq_plane], export=False)


def test_world_axis_traces_always_present(box):
    fig = _capture_fig(box)
    world_traces = [t for t in fig.data if getattr(t, "legendgroup", None) == "world_axes"]
    assert len(world_traces) == 3

def test_world_axes_hidden_by_default(box):
    fig = _capture_fig(box)
    world_traces = [t for t in fig.data if getattr(t, "legendgroup", None) == "world_axes"]
    assert all(t.visible is False for t in world_traces)

def test_world_axes_visible_when_requested(box):
    fig = _capture_fig(box, world_axes=True)
    world_traces = [t for t in fig.data if getattr(t, "legendgroup", None) == "world_axes"]
    assert all(t.visible in (True, None) for t in world_traces)

def test_local_axes_menu_label(cq_plane):
    fig = _capture_fig([cq_plane])
    labels = [b.label for b in fig.layout.updatemenus[3].buttons]
    assert any("Local Axes" in l for l in labels)

def test_origin_menu_label(box):
    fig = _capture_fig(box)
    labels = [b.label for b in fig.layout.updatemenus[4].buttons]
    assert any("Origin" in l for l in labels)

def test_origin_toggle_restyles_world_axis_indices(box):
    fig = _capture_fig(box)
    on_button = fig.layout.updatemenus[4].buttons[0]
    assert on_button.method == "restyle"
    assert on_button.args[0] == {"visible": True}

def test_local_axes_toggle_is_skip_when_nothing_to_toggle(straight_edge):
    """
    Plotly.restyle treats an *empty* trace-index list as "all traces",
    not "no traces" — with no solid and no explicit Location/Plane/Axis
    passed to show(), restyling with [] would hide the geometry along with
    the (nonexistent) axes. The button must use method="skip" instead.
    """
    fig = _capture_fig(straight_edge)
    for button in fig.layout.updatemenus[3].buttons:
        assert button.method == "skip"

def test_local_axes_toggle_is_restyle_for_a_plain_solid(box):
    """A solid gets its own automatic triad, with nothing else passed in."""
    fig = _capture_fig(box)
    for button in fig.layout.updatemenus[3].buttons:
        assert button.method == "restyle"
        assert button.args[1] != []

def test_local_axes_toggle_is_restyle_when_locations_present(cq_plane):
    fig = _capture_fig([cq_plane])
    for button in fig.layout.updatemenus[3].buttons:
        assert button.method == "restyle"
        assert button.args[1] != []



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


# ── show — export dropdown/button ────────────────────────────────────────────

def test_show_default_export_displays_dropdown_and_button(box):
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"), \
         patch("cadquery_simpleviewer.viewer.display") as mock_display:
        show(box, export_ifc=False)

    export_widget = mock_display.call_args[0][0]
    assert isinstance(export_widget, widgets.HBox)
    dropdown, button, status = export_widget.children
    assert dropdown.options == ("STEP",)
    assert isinstance(button, widgets.Button)
    assert button.description == "Export"
    assert isinstance(status, widgets.Output)

def test_show_export_false_skips_widget(box):
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"), \
         patch("cadquery_simpleviewer.viewer.display") as mock_display:
        show(box, export=False, export_ifc=False)

    mock_display.assert_not_called()

def test_show_export_missing_ipywidgets_falls_back_silently(box):
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"), \
         patch("cadquery_simpleviewer.viewer.widgets", None), \
         patch("cadquery_simpleviewer.viewer.display") as mock_display:
        show(box)

    mock_display.assert_not_called()

def test_show_export_ifc_offered_alongside_step(box):
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"), \
         patch("cadquery_simpleviewer.viewer.display") as mock_display, \
         patch("cadquery_simpleviewer.viewer._ifcopenshell_available", lambda: True):
        show(box)

    export_widget = mock_display.call_args[0][0]
    dropdown, _button, _status = export_widget.children
    assert dropdown.options == ("STEP", "IFC Proxy")
    assert dropdown.value == "STEP"

def test_show_export_button_click_writes_step_file(tmp_path, box):
    target = tmp_path / "exported.step"

    with patch("cadquery_simpleviewer.viewer.go.Figure.show"), \
         patch("cadquery_simpleviewer.viewer.display") as mock_display:
        show(box, export=dict(filename=str(target)), export_ifc=False)

    export_widget = mock_display.call_args[0][0]
    _dropdown, button, _status = export_widget.children
    button.click()

    assert target.exists()

def test_show_export_button_click_reports_failure(tmp_path, straight_edge, capsys):
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"), \
         patch("cadquery_simpleviewer.viewer.display") as mock_display:
        show(straight_edge, export=dict(filename=str(tmp_path / "edge.step")), export_ifc=False)

    export_widget = mock_display.call_args[0][0]
    _dropdown, button, _status = export_widget.children
    button.click()

    assert "Export failed" in capsys.readouterr().out

def test_show_export_ifc_selected_calls_export_ifc_proxy(box):
    calls = []

    def fake_export_ifc_proxy(*a, **kw):
        calls.append((a, kw))
        return "model.ifc"

    with patch("cadquery_simpleviewer.viewer.go.Figure.show"), \
         patch("cadquery_simpleviewer.viewer.display") as mock_display, \
         patch("cadquery_simpleviewer.viewer._ifcopenshell_available", lambda: True), \
         patch("cadquery_simpleviewer.viewer.export_ifc_proxy", fake_export_ifc_proxy):
        show(box, export=False)

        export_widget = mock_display.call_args[0][0]
        dropdown, button, _status = export_widget.children
        dropdown.value = "IFC Proxy"
        button.click()

    assert len(calls) == 1
    assert calls[0][1]["schema"] == "IFC4"

def test_show_ifc_config_schema_forwarded_to_export_ifc_proxy(box):
    calls = []

    def fake_export_ifc_proxy(*a, **kw):
        calls.append((a, kw))
        return "model.ifc"

    with patch("cadquery_simpleviewer.viewer.go.Figure.show"), \
         patch("cadquery_simpleviewer.viewer.display") as mock_display, \
         patch("cadquery_simpleviewer.viewer._ifcopenshell_available", lambda: True), \
         patch("cadquery_simpleviewer.viewer.export_ifc_proxy", fake_export_ifc_proxy):
        show(box, export=False, ifc_config=dict(schema="IFC2X3"))

        export_widget = mock_display.call_args[0][0]
        dropdown, button, _status = export_widget.children
        dropdown.value = "IFC Proxy"
        button.click()

    assert calls[0][1]["schema"] == "IFC2X3"
