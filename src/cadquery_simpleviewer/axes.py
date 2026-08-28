import plotly.graph_objects as go

_AXIS_COLORS = ("red", "green", "blue")


def _axis_triad_traces(origin, x_tip, y_tip, z_tip, opacity, width, legendgroup, visible):
    """
    Build 3 go.Scatter3d line traces (X=red, Y=green, Z=blue) from origin
    to each tip. Bypasses tessellation entirely — these are raw lines, not
    solid geometry routed through an adapter.
    """
    tips = (x_tip, y_tip, z_tip)
    traces = []

    for color, tip in zip(_AXIS_COLORS, tips):
        traces.append(go.Scatter3d(
            x=[origin[0], tip[0]],
            y=[origin[1], tip[1]],
            z=[origin[2], tip[2]],
            mode="lines",
            line=dict(color=color, width=width),
            opacity=opacity,
            legendgroup=legendgroup,
            showlegend=False,
            hoverinfo="skip",
            visible=visible,
        ))

    return traces


def _world_axis_traces(scale, visible, width=4):
    """The single fixed red/green/blue triad at the global origin."""
    origin = (0.0, 0.0, 0.0)
    x_tip = (scale, 0.0, 0.0)
    y_tip = (0.0, scale, 0.0)
    z_tip = (0.0, 0.0, scale)

    return _axis_triad_traces(
        origin, x_tip, y_tip, z_tip,
        opacity=1.0, width=width, legendgroup="world_axes", visible=visible,
    )


def _local_axis_traces(origin, x_tip, y_tip, z_tip, visible, width=3, opacity=0.45):
    """
    One per-object triad, dimmed (lower opacity) relative to the world
    triad so the two are visually distinguishable while sharing the same
    red/green/blue hues.
    """
    return _axis_triad_traces(
        origin, x_tip, y_tip, z_tip,
        opacity=opacity, width=width, legendgroup="local_axes", visible=visible,
    )
