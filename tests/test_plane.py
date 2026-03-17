import plotly.graph_objects as go
from cadquery_simpleviewer.plane import _base_plane


def test_base_plane_returns_mesh3d():
    trace = _base_plane(size=10, color="whitesmoke", opacity=0.8, z=0)
    assert isinstance(trace, go.Mesh3d)


def test_base_plane_z_elevation():
    """All z values of the plane must match the requested elevation."""
    z_level = 3.5
    trace = _base_plane(size=10, color="whitesmoke", opacity=0.8, z=z_level)
    for value in trace.z:
        assert value == z_level


def test_base_plane_size():
    """Vertices must span the requested size in both x and y."""
    trace = _base_plane(size=20, color="white", opacity=1.0, z=0)
    assert min(trace.x) == -20
    assert max(trace.x) ==  20
    assert min(trace.y) == -20
    assert max(trace.y) ==  20


def test_base_plane_not_in_legend():
    trace = _base_plane(size=10, color="white", opacity=1.0, z=0)
    assert trace.showlegend == False