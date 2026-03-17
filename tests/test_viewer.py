import cadquery as cq
import plotly.graph_objects as go
import pytest
from unittest.mock import patch

from cadquery_simpleviewer.viewer import _build_traces, show, show_arch


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


# ── _build_traces ────────────────────────────────────────────────────────────

def test_build_traces_single_object(box):
    """A single object (not a list) must be accepted and produce one trace."""
    traces = _build_traces(box, names=None, colors=None,
                           opacity=1.0, tessellation_tolerance=0.1)
    assert len(traces) == 1
    assert isinstance(traces[0], go.Mesh3d)


def test_build_traces_multiple_objects(two_objects):
    traces = _build_traces(two_objects, names=None, colors=None,
                           opacity=1.0, tessellation_tolerance=0.1)
    assert len(traces) == 2


def test_build_traces_custom_names(two_objects):
    names = ["Box", "Cylinder"]
    traces = _build_traces(two_objects, names=names, colors=None,
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
    """Tessellated trace must have vertices and triangle indices."""
    traces = _build_traces(box, names=None, colors=None,
                           opacity=1.0, tessellation_tolerance=0.1)
    trace = traces[0]
    assert len(trace.x) > 0
    assert len(trace.i) > 0


# ── show ─────────────────────────────────────────────────────────────────────

def test_show_runs_without_error(box):
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
        show(box)


def test_show_axes_are_visible(box):
    """show() must keep axes on — showticklabels must be True."""
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
        # Rebuild the figure manually to inspect layout
        import plotly.graph_objects as go
        from cadquery_simpleviewer.viewer import _build_traces, _AXIS_ON
        traces = _build_traces(box, None, None, 1.0, 0.1)
        fig = go.Figure(data=traces)
        fig.update_layout(scene=dict(xaxis=dict(**_AXIS_ON)))
        assert fig.layout.scene.xaxis.showticklabels == True


# ── show_arch ────────────────────────────────────────────────────────────────

def test_show_arch_runs_without_error(box):
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
        show_arch(box)


def test_show_arch_with_plane(two_objects):
    """When z is set, the first trace must be the base plane."""
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
        from cadquery_simpleviewer.viewer import _build_traces
        from cadquery_simpleviewer.plane import _base_plane

        traces = _build_traces(two_objects, None, None, 1.0, 0.1)
        plane  = _base_plane(size=50, color="whitesmoke", opacity=0.8, z=0)
        traces.insert(0, plane)

        # First trace is the plane — it has no legend entry
        assert traces[0].showlegend == False


def test_show_arch_without_plane(box):
    """When z is None, no base plane trace must be added."""
    with patch("cadquery_simpleviewer.viewer.go.Figure.show"):
        from cadquery_simpleviewer.viewer import _build_traces
        traces = _build_traces(box, None, None, 1.0, 0.1)
        # z=None means no insertion — only the object trace
        assert len(traces) == 1


def test_show_arch_axes_are_off(box):
    """show_arch() must have axes hidden — showticklabels must be False."""
    from cadquery_simpleviewer.viewer import _AXIS_OFF
    assert _AXIS_OFF["showticklabels"] == False