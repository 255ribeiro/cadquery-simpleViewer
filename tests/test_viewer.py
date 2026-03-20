import cadquery as cq
import plotly.graph_objects as go
import pytest
from unittest.mock import patch

from cadquery_simpleviewer.viewer import (
    _build_traces,
    _bounding_box,
    _axes_from_string,
    _axis_style,
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


# ── _axis_style ──────────────────────────────────────────────────────────────

def test_axis_style_visible_has_background():
    style = _axis_style(True)
    assert style["showbackground"] == True
    assert style["showticklabels"] == True
    assert style["showgrid"] == True


def test_axis_style_hidden_has_no_background():
    style = _axis_style(False)
    assert style["showbackground"] == False
    assert style["showticklabels"] == False
    assert style["showgrid"] == False


def test_axis_style_visible_uses_default_plotly_colors():
    style = _axis_style(True)
    assert "rgb" in style["backgroundcolor"]
    assert style["gridcolor"] == "white"


# ── _axes_from_string ────────────────────────────────────────────────────────

def test_axes_none_maps_to_all_visible():
    x, y, z = _axes_from_string("xyz")
    assert x == True
    assert y == True
    assert z == True


def test_axes_x_only():
    x, y, z = _axes_from_string("x")
    assert x == True
    assert y == False
    assert z == False


def test_axes_xy():
    x, y, z = _axes_from_string("xy")
    assert x == True
    assert y == True
    assert z == False


def test_axes_yz():
    x, y, z = _axes_from_string("yz")
    assert x == False
    assert y == True
    assert z == True


def test_axes_z_only():
    x, y, z = _axes_from_string("z")
    assert x == False
    assert y == False
    assert z == True


def test_axes_invalid_raises():
    with pytest.raises(ValueError):
        _axes_from_string("w")


def test_axes_invalid_combined_raises():
    with pytest.raises(ValueError):
        _axes_from_string("xw")


# ── _build_traces ────────────────────────────────────────────────────────────

def test_build_traces_single_object(box):
    traces = _build_traces(box, names=None, colors=None,
                           opacity=1.0, tessellation_tolerance=0.1)
    assert len(traces) == 1
    assert isinstance(traces[0], go.Mesh3d)


def test_build_traces_multiple_objects(two_objects):
    traces = _build_traces(two_objects, names=None, colors=None,
                           opacity=1.0, tessellation_tolerance=0.1)
    assert len(traces) == 2


def test_build_traces_custom_names(two_objects):
    traces = _build_traces(two_objects, names=["Box", "Cylinder"], colors=None,
                           opacity=1.0, tessellation_tolerance=0.1)
    assert traces[0].name == "Box"
    assert traces[1].name == "Cylinder"


def test_build_traces_default_names(two_objects):
    traces = _build_traces(two_objects, names=None, colors=None,
                           opacity=1.0, tessellation_tolerance=0.1)
    assert traces[0].name == "Object 1"
    assert traces[1].name == "Object 2"


def test_build_traces_custom_colors(box):
    traces = _build_traces(box, names=None, colors=["red"],
                           opacity=1.0, tessellation_tolerance=0.1)
    assert traces[0].color == "red"


def test_build_traces_opacity(box):
    traces = _build_traces(box, names=None, colors=None,
                           opacity=0.5, tessellation_tolerance=0.1)
    assert traces[0].opacity == 0.5


def test_build_traces_has_geometry(box):
    traces = _build_traces(box, names=None, colors=None,
                           opacity=1.0, tessellation_tolerance=0.1)
    assert len(traces[0].x) > 0
    assert len(traces[0].i) > 0


# ── _bounding_box ────────────────────────────────────────────────────────────

def test_bounding_box_single_trace(box):
    traces = _build_traces(box, None, None, 1.0, 0.1)
    xmin, xmax, ymin, ymax, zmin, zmax = _bounding_box(traces)
    assert xmin < xmax
    assert ymin < ymax
    assert zmin < zmax


def test_bounding_box_excludes_plane_trace():
    """Base plane trace has showlegend=False and must be excluded from bbox."""
    from cadquery_simpleviewer.plane import _base_plane
    plane = _base_plane(size=100, color="white", opacity=1.0, z=0)
    box_obj = cq.Workplane("XY").box(2, 2, 2)
    traces = _build_traces(box_obj, None, None, 1.0, 0.1)
    traces.insert(0, plane)
    xmin, xmax, ymin, ymax, zmin, zmax = _bounding_box(traces)
    # bounding box must reflect the box geometry, not the 100-unit plane
    assert xmax < 10


# ── show ─────────────────────────────────────────────────────────────────────

def test_show_runs_without_error(box):
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
        show(box)


def test_show_default_visible_axes_is_xyz(box):
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
        # Should not raise — xyz is the default
        show(box, visible_axes="xyz")


def test_show_accepts_none_axes(box):
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
        show(box, visible_axes=None)


def test_show_invalid_axes_raises(box):
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
        with pytest.raises(ValueError):
            show(box, visible_axes="w")


def test_show_with_plane(box):
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
        show(box, z=0)


def test_show_without_plane(box):
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
        show(box, z=None)


def test_show_has_updatemenus(box):
    """Figure must contain 4 updatemenus: X, Y, Z axes + camera."""
    captured = {}

    def fake_show(self):
        captured["fig"] = self

    with patch("cadquery_simpleviewer.viewer.go.Figure.show", fake_show):
        show(box)

    fig = captured["fig"]
    assert len(fig.layout.updatemenus) == 4


def test_show_camera_menu_has_three_options(box):
    """Camera dropdown must have exactly 3 buttons."""
    captured = {}

    def fake_show(self):
        captured["fig"] = self

    with patch("cadquery_simpleviewer.viewer.go.Figure.show", fake_show):
        show(box)

    fig = captured["fig"]
    # Camera menu is the 4th updatemenu (index 3)
    camera_menu = fig.layout.updatemenus[3]
    assert len(camera_menu.buttons) == 3


def test_show_equal_aspect_ratio(box):
    """Scene aspectratio must be 1:1:1 to enforce equal axis scaling."""
    captured = {}

    def fake_show(self):
        captured["fig"] = self

    with patch("cadquery_simpleviewer.viewer.go.Figure.show", fake_show):
        show(box)

    fig = captured["fig"]
    ratio = fig.layout.scene.aspectratio
    assert ratio.x == 1
    assert ratio.y == 1
    assert ratio.z == 1


def test_show_equal_axis_ranges(box):
    """X, Y and Z axis ranges must have the same span to ensure equal scaling."""
    captured = {}

    def fake_show(self):
        captured["fig"] = self

    with patch("cadquery_simpleviewer.viewer.go.Figure.show", fake_show):
        show(box)

    fig = captured["fig"]
    scene = fig.layout.scene

    x_span = scene.xaxis.range[1] - scene.xaxis.range[0]
    y_span = scene.yaxis.range[1] - scene.yaxis.range[0]
    z_span = scene.zaxis.range[1] - scene.zaxis.range[0]

    assert abs(x_span - y_span) < 1e-9
    assert abs(y_span - z_span) < 1e-9


def test_show_x_axis_hidden_when_not_in_visible_axes(box):
    """When visible_axes='yz', x axis must have showbackground=False."""
    captured = {}

    def fake_show(self):
        captured["fig"] = self

    with patch("cadquery_simpleviewer.viewer.go.Figure.show", fake_show):
        show(box, visible_axes="yz")

    fig = captured["fig"]
    assert fig.layout.scene.xaxis.showbackground == False


def test_show_all_axes_visible_when_xyz(box):
    """When visible_axes='xyz', all three axes must have showbackground=True."""
    captured = {}

    def fake_show(self):
        captured["fig"] = self

    with patch("cadquery_simpleviewer.viewer.go.Figure.show", fake_show):
        show(box, visible_axes="xyz")

    fig = captured["fig"]
    assert fig.layout.scene.xaxis.showbackground == True
    assert fig.layout.scene.yaxis.showbackground == True
    assert fig.layout.scene.zaxis.showbackground == True
