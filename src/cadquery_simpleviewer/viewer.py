import plotly.graph_objects as go
from .plane import _base_plane

_DEFAULT_COLORS = [
    "steelblue", "indianred", "seagreen",
    "sandybrown", "mediumpurple", "cadetblue", "goldenrod"
]

_AXIS_ON = dict(
    showbackground=True,
    backgroundcolor="white",
    showgrid=True,
    gridcolor="lightgray",
    zeroline=True,
    showline=True,
    showticklabels=True,
    showspikes=True,
)

_AXIS_OFF = dict(
    showbackground=False,
    showgrid=False,
    zeroline=False,
    showline=False,
    showticklabels=False,
    showspikes=False,
    title=dict(text="")
)


def _build_traces(objects, names, colors, opacity, tessellation_tolerance):
    """Tessellate a list of CadQuery objects into Plotly Mesh3d traces."""
    if not isinstance(objects, list):
        objects = [objects]

    traces = []

    for index in range(len(objects)):

        vertices, triangles = objects[index].val().tessellate(tessellation_tolerance)

        x   = []
        y   = []
        z   = []
        for v in vertices:
            x.append(v.x)
            y.append(v.y)
            z.append(v.z)

        ii  = []
        jj  = []
        kk  = []
        for t in triangles:
            ii.append(t[0])
            jj.append(t[1])
            kk.append(t[2])

        color = colors[index] if colors else _DEFAULT_COLORS[index % len(_DEFAULT_COLORS)]
        name  = names[index]  if names  else "Object " + str(index + 1)

        traces.append(go.Mesh3d(
            x=x, y=y, z=z,
            i=ii, j=jj, k=kk,
            color=color,
            opacity=opacity,
            name=name,
            flatshading=True,
            showlegend=True,
            lighting=dict(ambient=0.4, diffuse=0.8, specular=0.2)
        ))

    return traces


def show(
    objects,
    names=None,
    colors=None,
    opacity=1.0,
    tessellation_tolerance=0.01,
):
    """
    Display one or more CadQuery objects with full axes and grid visible.
    Useful for inspecting dimensions and spatial relationships during modelling.

    Parameters
    ----------
    objects                 : single CadQuery object or list of CadQuery objects
    names                   : list of legend labels (optional)
    colors                  : list of face colors (optional)
    opacity                 : solid opacity — 1.0 = fully opaque
    tessellation_tolerance  : mesh precision — smaller = finer, slower
    """
    traces = _build_traces(objects, names, colors, opacity, tessellation_tolerance)

    fig = go.Figure(data=traces)
    fig.update_layout(
        scene=dict(
            aspectmode="data",
            xaxis=dict(**_AXIS_ON),
            yaxis=dict(**_AXIS_ON),
            zaxis=dict(**_AXIS_ON),
        ),
        legend=dict(x=0, y=1),
        margin=dict(l=0, r=0, t=30, b=0)
    )
    fig.show()


def show_arch(
    objects,
    names=None,
    colors=None,
    opacity=1.0,
    z=None,
    plane_color="whitesmoke",
    plane_size=50,
    plane_opacity=0.8,
    tessellation_tolerance=0.01,
):
    """
    Display one or more CadQuery objects with a clean architectural presentation:
    no axis labels, no grid lines, no tick numbers.
    Optionally draws a base plane at a given z elevation.

    Parameters
    ----------
    objects                 : single CadQuery object or list of CadQuery objects
    names                   : list of legend labels (optional)
    colors                  : list of face colors (optional)
    opacity                 : solid opacity — 1.0 = fully opaque
    z                       : elevation of the base plane; None = no plane (default)
    plane_color             : color of the base plane
    plane_size              : half-side length of the base plane quad
    plane_opacity           : opacity of the base plane
    tessellation_tolerance  : mesh precision — smaller = finer, slower
    """
    traces = _build_traces(objects, names, colors, opacity, tessellation_tolerance)

    if z is not None:
        traces.insert(0, _base_plane(
            size=plane_size,
            color=plane_color,
            opacity=plane_opacity,
            z=z
        ))

    fig = go.Figure(data=traces)
    fig.update_layout(
        scene=dict(
            aspectmode="data",
            xaxis=dict(**_AXIS_OFF),
            yaxis=dict(**_AXIS_OFF),
            zaxis=dict(**_AXIS_OFF),
        ),
        legend=dict(x=0, y=1),
        margin=dict(l=0, r=0, t=30, b=0)
    )
    fig.show()