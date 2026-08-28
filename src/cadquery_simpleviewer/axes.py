import math

import plotly.graph_objects as go

_AXIS_COLORS = ("red", "green", "blue")
_LOCAL_AXIS_COLORS = ("lightcoral", "lightgreen", "lightskyblue")

# Arm radius as a fraction of arm length — keeps the cylinders "long in
# height, small in radius" regardless of axes_scale.
_RADIUS_RATIO = 0.035

_CYLINDER_SEGMENTS = 10


def _cylinder_mesh(origin, tip, radius, segments=_CYLINDER_SEGMENTS):
    """
    Build the vertex/face arrays (x, y, z, i, j, k) of a solid capped
    cylinder from `origin` to `tip`, ready for go.Mesh3d.

    Axis arms are drawn as real tessellated geometry rather than thin
    Scatter3d lines: gl3d line rendering (width, in particular) is
    unreliable across browsers/WebGL contexts — e.g. arms can render
    invisible in some environments (observed on Google Colab) regardless
    of geometry size or opacity — whereas Mesh3d uses the exact same
    rendering path as every other solid already shown, so it behaves
    identically everywhere that does.
    """
    ox, oy, oz = origin
    tx, ty, tz = tip
    dx, dy, dz = tx - ox, ty - oy, tz - oz
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    if length == 0:
        return [], [], [], [], [], []

    az = (dx / length, dy / length, dz / length)

    # Any vector not parallel to az works as a seed for a perpendicular basis.
    seed = (0.0, 0.0, 1.0) if abs(az[2]) < 0.9 else (1.0, 0.0, 0.0)

    def cross(a, b):
        return (
            a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0],
        )

    def normalize(v):
        n = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
        return (v[0] / n, v[1] / n, v[2] / n)

    ax = normalize(cross(seed, az))
    ay = cross(az, ax)

    xs, ys, zs = [ox], [oy], [oz]  # index 0: bottom cap center

    bottom_start = 1
    for i in range(segments):
        theta = 2 * math.pi * i / segments
        cx, cy = math.cos(theta) * radius, math.sin(theta) * radius
        xs.append(ox + cx * ax[0] + cy * ay[0])
        ys.append(oy + cx * ax[1] + cy * ay[1])
        zs.append(oz + cx * ax[2] + cy * ay[2])

    top_center = bottom_start + segments
    xs.append(tx); ys.append(ty); zs.append(tz)  # top cap center

    top_start = top_center + 1
    for i in range(segments):
        theta = 2 * math.pi * i / segments
        cx, cy = math.cos(theta) * radius, math.sin(theta) * radius
        xs.append(tx + cx * ax[0] + cy * ay[0])
        ys.append(ty + cx * ax[1] + cy * ay[1])
        zs.append(tz + cx * ax[2] + cy * ay[2])

    ii, jj, kk = [], [], []

    for i in range(segments):
        a = bottom_start + i
        b = bottom_start + (i + 1) % segments
        ii.append(0); jj.append(b); kk.append(a)  # bottom cap fan

    for i in range(segments):
        a = top_start + i
        b = top_start + (i + 1) % segments
        ii.append(top_center); jj.append(a); kk.append(b)  # top cap fan

    for i in range(segments):
        b0 = bottom_start + i
        b1 = bottom_start + (i + 1) % segments
        t0 = top_start + i
        t1 = top_start + (i + 1) % segments
        ii.append(b0); jj.append(b1); kk.append(t0)  # side wall, tri 1
        ii.append(b1); jj.append(t1); kk.append(t0)  # side wall, tri 2

    return xs, ys, zs, ii, jj, kk


def _axis_triad_traces(origin, x_tip, y_tip, z_tip, colors, legendgroup, visible):
    """
    Build 3 go.Mesh3d cylinder traces from origin to each tip, tessellated
    the same way as any other solid, at full opacity — semi-transparent
    Mesh3d traces are unreliable across Plotly.js/WebGL renderers (e.g.
    VS Code's notebook renderer can silently fail to draw them at all,
    regardless of the `visible` flag), the same class of bug that ruled
    out thin Scatter3d lines for these triads in the first place.
    """
    tips = (x_tip, y_tip, z_tip)
    traces = []

    for color, tip in zip(colors, tips):
        length = math.dist(origin, tip)
        radius = length * _RADIUS_RATIO
        x, y, z, i, j, k = _cylinder_mesh(origin, tip, radius)

        traces.append(go.Mesh3d(
            x=x, y=y, z=z,
            i=i, j=j, k=k,
            color=color,
            opacity=1.0,
            flatshading=True,
            legendgroup=legendgroup,
            showlegend=False,
            hoverinfo="skip",
            visible=visible,
        ))

    return traces


def _world_axis_traces(scale, visible):
    """The single fixed red/green/blue triad at the global origin."""
    origin = (0.0, 0.0, 0.0)
    x_tip = (scale, 0.0, 0.0)
    y_tip = (0.0, scale, 0.0)
    z_tip = (0.0, 0.0, scale)

    return _axis_triad_traces(
        origin, x_tip, y_tip, z_tip,
        colors=_AXIS_COLORS, legendgroup="world_axes", visible=visible,
    )


def _local_axis_traces(origin, x_tip, y_tip, z_tip, visible, legendgroup="local_axes"):
    """
    One per-object triad, in lighter tints of the world triad's red/green/
    blue so the two are visually distinguishable — full opacity throughout
    (see `_axis_triad_traces`), rather than the previous opacity-based
    dimming, which could render invisibly.

    `legendgroup` defaults to a single shared group for standalone
    Location/Plane/Axis objects (no solid of their own to tie to), but the
    automatic per-solid triad passes the solid's own mesh legendgroup
    instead, so toggling that solid off in the legend hides its triad too.
    """
    return _axis_triad_traces(
        origin, x_tip, y_tip, z_tip,
        colors=_LOCAL_AXIS_COLORS, legendgroup=legendgroup, visible=visible,
    )
