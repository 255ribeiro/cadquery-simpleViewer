import plotly.graph_objects as go
from cadquery_simpleviewer.axes import _world_axis_traces, _local_axis_traces


# ── _world_axis_traces ───────────────────────────────────────────────────────

def test_world_axis_traces_count():
    traces = _world_axis_traces(scale=1, visible=True)
    assert len(traces) == 3
    assert all(isinstance(t, go.Scatter3d) for t in traces)

def test_world_axis_traces_colors():
    traces = _world_axis_traces(scale=1, visible=True)
    assert [t.line.color for t in traces] == ["red", "green", "blue"]

def test_world_axis_traces_full_opacity():
    traces = _world_axis_traces(scale=1, visible=True)
    assert all(t.opacity == 1.0 for t in traces)

def test_world_axis_traces_scale():
    traces = _world_axis_traces(scale=7, visible=True)
    x_trace = traces[0]
    assert x_trace.x == (0, 7)

def test_world_axis_traces_visible_flag():
    traces = _world_axis_traces(scale=1, visible=False)
    assert all(t.visible is False for t in traces)

def test_world_axis_traces_not_in_legend():
    traces = _world_axis_traces(scale=1, visible=True)
    assert all(t.showlegend is False for t in traces)


# ── _local_axis_traces ───────────────────────────────────────────────────────

def test_local_axis_traces_dimmed():
    traces = _local_axis_traces(
        (1, 1, 1), (2, 1, 1), (1, 2, 1), (1, 1, 2), visible=True
    )
    assert all(t.opacity < 1.0 for t in traces)

def test_local_axis_traces_colors():
    traces = _local_axis_traces(
        (0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1), visible=True
    )
    assert [t.line.color for t in traces] == ["red", "green", "blue"]

def test_local_axis_traces_origin_offset():
    traces = _local_axis_traces(
        (1, 1, 1), (2, 1, 1), (1, 2, 1), (1, 1, 2), visible=True
    )
    for t in traces:
        assert t.x[0] == 1 and t.y[0] == 1 and t.z[0] == 1
