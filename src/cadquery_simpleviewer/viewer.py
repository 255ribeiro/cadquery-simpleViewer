import plotly.graph_objects as go
from .plane import _base_plane

_DEFAULT_COLORS = [
    "steelblue", "indianred", "seagreen",
    "sandybrown", "mediumpurple", "cadetblue", "goldenrod"
]

# Valid values for the visible_axes parameter
_VALID_AXES = {None, "x", "y", "z", "xy", "xz", "yz", "xyz"}


def _axis_style(visible: bool) -> dict:
    """
    Return an axis dict using Plotly's default visual style (grey-blue background,
    white grid lines). When visible=False all visual elements are hidden.
    """
    if not visible:
        return dict(
            showbackground=False,
            showgrid=False,
            zeroline=False,
            showline=False,
            showticklabels=False,
            showspikes=False,
            title=dict(text="")
        )
    return dict(
        showbackground=True,
        backgroundcolor="rgb(230, 236, 245)",  # Plotly default grey-blue
        showgrid=True,
        gridcolor="white",
        gridwidth=1,
        zeroline=True,
        zerolinecolor="white",
        zerolinewidth=2,
        showline=False,
        showticklabels=True,
        showspikes=True,
        title=dict(text="")
    )


def _padded_axis(min_val: float, max_val: float, visible: bool,
                 padding_factor: float = 0.15) -> dict:
    """
    Build an axis dict with a padded range so geometry does not touch
    the background planes.
    """
    span    = max_val - min_val
    padding = span * padding_factor if span > 0 else 1.0

    style = _axis_style(visible)
    style["range"] = [min_val - padding, max_val + padding]
    return style


def _build_traces(objects, names, colors, opacity, tessellation_tolerance):
    """Tessellate a list of CadQuery objects into Plotly Mesh3d traces."""
    if not isinstance(objects, list):
        objects = [objects]

    traces = []

    for index in range(len(objects)):

        vertices, triangles = objects[index].val().tessellate(tessellation_tolerance)

        x  = []
        y  = []
        z  = []
        for v in vertices:
            x.append(v.x)
            y.append(v.y)
            z.append(v.z)

        ii = []
        jj = []
        kk = []
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


def _bounding_box(traces):
    """Return the combined x, y, z min/max across all Mesh3d traces."""
    all_x = []
    all_y = []
    all_z = []

    for trace in traces:
        if isinstance(trace, go.Mesh3d) and trace.showlegend:
            all_x.extend(trace.x)
            all_y.extend(trace.y)
            all_z.extend(trace.z)

    return (min(all_x), max(all_x),
            min(all_y), max(all_y),
            min(all_z), max(all_z))


def _axes_from_string(visible_axes: str):
    """
    Parse the visible_axes string and return three booleans (x, y, z).
    None maps to all axes visible ("xyz").
    """
    if visible_axes is None:
        key = "xyz"
    else:
        key = visible_axes.lower()

    if key not in _VALID_AXES:
        raise ValueError(
            f"visible_axes must be one of {sorted(str(v) for v in _VALID_AXES)}, "
            f"got '{visible_axes}'"
        )

    show_x = "x" in key
    show_y = "y" in key
    show_z = "z" in key
    return show_x, show_y, show_z


def _make_axes_menu(xmin, xmax, ymin, ymax, zmin, zmax, padding):
    """
    Build a Plotly updatemenus dropdown with three checkboxes:
    X axis, Y axis, Z axis. Each button toggles the visibility of one axis.
    The eight combinations (2^3) are pre-computed as separate buttons arranged
    as three independent toggles using restyle.
    """
    # Helper: build scene dict for a given visibility combination
    def scene_for(sx, sy, sz):
        return dict(
            scene_xaxis=_padded_axis(xmin, xmax, sx, padding),
            scene_yaxis=_padded_axis(ymin, ymax, sy, padding),
            scene_zaxis=_padded_axis(zmin, zmax, sz, padding),
        )

    # We use three separate button groups, one per axis.
    # Each group has "show" / "hide" buttons for that axis only,
    # leaving the other axes unchanged via relayout with partial dicts.
    # Plotly does not support true checkboxes natively, so we build
    # three small dropdowns, each acting as an on/off toggle for one axis.

    def axis_menu(axis_label, axis_key, min_val, max_val, initial_visible, x_pos):
        on_dict  = _padded_axis(min_val, max_val, True,  padding)
        off_dict = _padded_axis(min_val, max_val, False, padding)
        return dict(
            type="dropdown",
            direction="down",
            x=x_pos,
            y=1.12,
            xanchor="left",
            showactive=True,
            active=0 if initial_visible else 1,
            bgcolor="white",
            bordercolor="lightgray",
            font=dict(size=11),
            buttons=[
                dict(
                    label=f"{axis_label} ✓",
                    method="relayout",
                    args=[{f"scene.{axis_key}": on_dict}]
                ),
                dict(
                    label=f"{axis_label} ✕",
                    method="relayout",
                    args=[{f"scene.{axis_key}": off_dict}]
                ),
            ]
        )

    return axis_menu, [xmin, xmax, ymin, ymax, zmin, zmax]


def _make_camera_menu(x_pos):
    """
    Build a Plotly updatemenus dropdown for camera presets:
    - 2-Point Perspective
    - 3-Point Perspective
    - Orthographic
    """
    return dict(
        type="dropdown",
        direction="down",
        x=x_pos,
        y=1.12,
        xanchor="left",
        showactive=True,
        active=0,
        bgcolor="white",
        bordercolor="lightgray",
        font=dict(size=11),
        buttons=[
            dict(
                label="2-Point Perspective",
                method="relayout",
                args=[{
                    "scene.camera": dict(
                        projection=dict(type="perspective"),
                        eye=dict(x=1.8, y=1.8, z=0.3),
                        up=dict(x=0, y=0, z=1)
                    )
                }]
            ),
            dict(
                label="3-Point Perspective",
                method="relayout",
                args=[{
                    "scene.camera": dict(
                        projection=dict(type="perspective"),
                        eye=dict(x=1.5, y=1.5, z=1.5),
                        up=dict(x=0, y=0, z=1)
                    )
                }]
            ),
            dict(
                label="Orthographic",
                method="relayout",
                args=[{
                    "scene.camera": dict(
                        projection=dict(type="orthographic"),
                        eye=dict(x=1.5, y=1.5, z=1.5),
                        up=dict(x=0, y=0, z=1)
                    )
                }]
            ),
        ]
    )


def show(
    objects,
    names=None,
    colors=None,
    opacity=1.0,
    visible_axes="xyz",
    z=None,
    plane_color="whitesmoke",
    plane_size=50,
    plane_opacity=0.8,
    tessellation_tolerance=0.01,
    padding=0.15,
):
    """
    Display one or more CadQuery objects as an interactive 3D Plotly figure.

    Parameters
    ----------
    objects                 : single CadQuery object or list of CadQuery objects
    names                   : list of legend labels (optional)
    colors                  : list of face colors — see https://plotly.com/python/css-colors/
    opacity                 : solid opacity — 1.0 = fully opaque
    visible_axes            : initial axes visibility — None or one of:
                              "x", "y", "z", "xy", "xz", "yz", "xyz" (default)
    z                       : elevation of the base plane; None = no plane (default)
    plane_color             : color of the base plane
    plane_size              : half-side length of the base plane quad
    plane_opacity           : opacity of the base plane
    tessellation_tolerance  : mesh precision — smaller = finer, slower
    padding                 : fraction of bounding box span added as axis margin
    """
    if visible_axes is None:
        visible_axes = "xyz"

    show_x, show_y, show_z = _axes_from_string(visible_axes)

    traces = _build_traces(objects, names, colors, opacity, tessellation_tolerance)

    if z is not None:
        traces.insert(0, _base_plane(
            size=plane_size,
            color=plane_color,
            opacity=plane_opacity,
            z=z
        ))

    xmin, xmax, ymin, ymax, zmin, zmax = _bounding_box(traces)

    # --- Compute a single shared range for all axes to enforce equal aspect ---
    # Find the largest span across all three axes and apply it to all,
    # so 1 unit in X is plotted using the same screen distance as 1 unit in Y or Z.
    x_center = (xmin + xmax) / 2
    y_center = (ymin + ymax) / 2
    z_center = (zmin + zmax) / 2

    x_span = xmax - xmin
    y_span = ymax - ymin
    z_span = zmax - zmin

    half = max(x_span, y_span, z_span) / 2 * (1 + padding)

    x_range = [x_center - half, x_center + half]
    y_range = [y_center - half, y_center + half]
    z_range = [z_center - half, z_center + half]

    # Build initial axis dicts with equal ranges
    def axis_dict(visible, val_range):
        d = _axis_style(visible)
        d["range"] = val_range
        return d

    # --- Axes dropdown menus (one per axis) ---
    def axis_menu(label, axis_key, initial_visible, val_range, x_pos):
        on_dict  = _axis_style(True)
        on_dict["range"]  = val_range
        off_dict = _axis_style(False)
        off_dict["range"] = val_range
        return dict(
            type="dropdown",
            direction="down",
            x=x_pos,
            y=1.12,
            xanchor="left",
            showactive=True,
            active=0 if initial_visible else 1,
            bgcolor="white",
            bordercolor="lightgray",
            font=dict(size=11),
            buttons=[
                dict(
                    label=f"{label} ✓",
                    method="relayout",
                    args=[{f"scene.{axis_key}": on_dict}]
                ),
                dict(
                    label=f"{label} ✕",
                    method="relayout",
                    args=[{f"scene.{axis_key}": off_dict}]
                ),
            ]
        )

    menu_x = axis_menu("X", "xaxis", show_x, x_range, 0.0)
    menu_y = axis_menu("Y", "yaxis", show_y, y_range, 0.12)
    menu_z = axis_menu("Z", "zaxis", show_z, z_range, 0.24)
    menu_cam = _make_camera_menu(x_pos=0.38)

    # --- Annotations as labels above each dropdown ---
    annotations = [
        dict(text="Axes:", x=0.0,  y=1.17, xref="paper", yref="paper",
             showarrow=False, font=dict(size=11)),
        dict(text="Camera:", x=0.36, y=1.17, xref="paper", yref="paper",
             showarrow=False, font=dict(size=11)),
    ]

    fig = go.Figure(data=traces)
    fig.update_layout(
        scene=dict(
            aspectmode="manual",
            aspectratio=dict(x=1, y=1, z=1),
            xaxis=axis_dict(show_x, x_range),
            yaxis=axis_dict(show_y, y_range),
            zaxis=axis_dict(show_z, z_range),
            camera=dict(
                projection=dict(type="perspective"),
                eye=dict(x=1.5, y=1.5, z=1.5),
                up=dict(x=0, y=0, z=1)
            )
        ),
        updatemenus=[menu_x, menu_y, menu_z, menu_cam],
        annotations=annotations,
        legend=dict(x=0, y=1),
        margin=dict(l=0, r=0, t=80, b=0)
    )

    fig.show()
