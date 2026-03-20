import cadquery as cq
import plotly.graph_objects as go
from .plane import _base_plane

_DEFAULT_COLORS = [
    "steelblue", "indianred", "seagreen",
    "sandybrown", "mediumpurple", "cadetblue", "goldenrod"
]

_DEFAULT_POINTS_DISPLAY = dict(
    size=5,
    color="red",
    symbol="circle",
    opacity=1.0,
)

_VALID_AXES = {None, "x", "y", "z", "xy", "xz", "yz", "xyz"}

_EQUAL_ASPECT = dict(x=1, y=1, z=1)


def _is_point(obj):
    """
    Return True if obj is a cq.Vector or a list/tuple of exactly 3 numbers.
    These are rendered as Scatter3d markers instead of tessellated meshes.
    """
    if isinstance(obj, cq.occ_impl.geom.Vector):
        return True
    if isinstance(obj, (list, tuple)) and len(obj) == 3:
        return all(isinstance(v, (int, float)) for v in obj)
    return False


def _point_to_xyz(obj):
    """Extract (x, y, z) from a cq.Vector or a [x, y, z] list/tuple."""
    if isinstance(obj, cq.occ_impl.geom.Vector):
        return obj.x, obj.y, obj.z
    return float(obj[0]), float(obj[1]), float(obj[2])


def _axis_style(visible: bool) -> dict:
    """
    Return an axis dict using Plotly's default visual style
    (grey-blue background, white grid lines).
    When visible=False all visual elements are hidden.
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
        backgroundcolor="rgb(230, 236, 245)",
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


def _axes_from_string(visible_axes):
    """
    Parse visible_axes and return three booleans (show_x, show_y, show_z).

    None  → all axes hidden
    "xyz" → all axes visible (the default parameter value)
    """
    if visible_axes is None:
        return False, False, False

    key = visible_axes.lower()

    if key not in {v for v in _VALID_AXES if v is not None}:
        raise ValueError(
            f"visible_axes must be None or one of "
            f"{sorted(v for v in _VALID_AXES if v is not None)}, "
            f"got '{visible_axes}'"
        )

    return "x" in key, "y" in key, "z" in key


def _build_traces(objects, names, colors, opacity,
                  tessellation_tolerance, points_display):
    """
    Build Plotly traces from a mixed list of CadQuery objects and point objects.

    CadQuery Workplane objects → go.Mesh3d (tessellated)
    cq.Vector or [x, y, z]   → go.Scatter3d (markers only)

    Returns (traces, all_x, all_y, all_z) where the coordinate lists cover
    all objects for bounding box computation.
    """
    if not isinstance(objects, list):
        objects = [objects]

    # Merge caller's points_display with defaults (caller wins)
    marker_style = dict(_DEFAULT_POINTS_DISPLAY)
    if points_display is not None:
        marker_style.update(points_display)

    traces  = []
    all_x   = []
    all_y   = []
    all_z   = []

    mesh_color_index = 0

    for index in range(len(objects)):
        obj  = objects[index]
        name = names[index] if names else "Object " + str(index + 1)

        if _is_point(obj):
            # --- Point object → Scatter3d marker ---
            px, py, pz = _point_to_xyz(obj)
            all_x.append(px)
            all_y.append(py)
            all_z.append(pz)

            traces.append(go.Scatter3d(
                x=[px], y=[py], z=[pz],
                mode="markers",
                marker=dict(
                    size=marker_style.get("size", 5),
                    color=marker_style.get("color", "red"),
                    symbol=marker_style.get("symbol", "circle"),
                    opacity=marker_style.get("opacity", 1.0),
                ),
                name=name,
                showlegend=True,
            ))

        else:
            # --- CadQuery object → tessellated Mesh3d ---
            vertices, triangles = obj.val().tessellate(tessellation_tolerance)

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

            all_x.extend(x)
            all_y.extend(y)
            all_z.extend(z)

            if colors:
                color = colors[index]
            else:
                color = _DEFAULT_COLORS[mesh_color_index % len(_DEFAULT_COLORS)]
                mesh_color_index += 1

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

    return traces, all_x, all_y, all_z


def _equal_ranges(xmin, xmax, ymin, ymax, zmin, zmax, padding):
    """
    Compute equal axis ranges centered on each axis midpoint.

    Equal scale requires all three things together:
      1. aspectmode='manual'
      2. aspectratio=dict(x=1, y=1, z=1)
      3. Equal data ranges on all three axes
    """
    x_center = (xmin + xmax) / 2
    y_center = (ymin + ymax) / 2
    z_center = (zmin + zmax) / 2

    x_span = xmax - xmin
    y_span = ymax - ymin
    z_span = zmax - zmin

    half = max(x_span, y_span, z_span) / 2 * (1 + padding)
    # Ensure a minimum half-span so single points don't collapse to zero range
    half = max(half, 1.0)

    return (
        [x_center - half, x_center + half],
        [y_center - half, y_center + half],
        [z_center - half, z_center + half],
    )


def _expand_for_plane(x_range, y_range, z_range, plane_size, z_level):
    """
    Expand the axis ranges to include the base plane extents so it is
    never clipped by the explicit axis ranges.
    """
    x_center = (x_range[0] + x_range[1]) / 2
    y_center = (y_range[0] + y_range[1]) / 2

    half_xy = max(
        (x_range[1] - x_range[0]) / 2,
        (y_range[1] - y_range[0]) / 2,
        plane_size
    )

    new_x = [x_center - half_xy, x_center + half_xy]
    new_y = [y_center - half_xy, y_center + half_xy]
    new_z = [min(z_range[0], z_level), max(z_range[1], z_level)]

    x_span = new_x[1] - new_x[0]
    y_span = new_y[1] - new_y[0]
    z_span = new_z[1] - new_z[0]
    half   = max(x_span, y_span, z_span) / 2

    xc = (new_x[0] + new_x[1]) / 2
    yc = (new_y[0] + new_y[1]) / 2
    zc = (new_z[0] + new_z[1]) / 2

    return (
        [xc - half, xc + half],
        [yc - half, yc + half],
        [zc - half, zc + half],
    )


def _axis_dict(visible: bool, val_range: list) -> dict:
    """Combine _axis_style with an explicit range."""
    d = _axis_style(visible)
    d["range"] = val_range
    return d


def _make_axis_toggle(label, scene_key, initial_visible, val_range, x_pos):
    """
    Build an on/off button pair for one axis.
    type='buttons' renders them as a side-by-side segmented control.
    """
    on_dict  = _axis_dict(True,  val_range)
    off_dict = _axis_dict(False, val_range)

    return dict(
        type="buttons",
        direction="right",
        x=x_pos,
        y=1.13,
        xanchor="left",
        yanchor="top",
        showactive=True,
        active=0 if initial_visible else 1,
        bgcolor="white",
        bordercolor="lightgray",
        font=dict(size=11),
        buttons=[
            dict(
                label=f"{label} ●",
                method="relayout",
                args=[{f"scene.{scene_key}": on_dict}]
            ),
            dict(
                label=f"{label} ○",
                method="relayout",
                args=[{f"scene.{scene_key}": off_dict}]
            ),
        ]
    )


def _make_camera_menu(x_pos):
    """
    Build a two-option dropdown: Perspective and Orthographic.

    Every button also relayouts aspectmode='manual' and aspectratio=1:1:1
    because a Plotly relayout that sets only scene.camera silently resets
    aspectmode to 'auto', destroying the equal-scale setup.
    """
    shared = {
        "scene.aspectmode":  "manual",
        "scene.aspectratio": _EQUAL_ASPECT,
    }

    def cam_args(projection_type, ex, ey, ez):
        args = dict(shared)
        args["scene.camera"] = dict(
            projection=dict(type=projection_type),
            eye=dict(x=ex, y=ey, z=ez),
            up=dict(x=0, y=0, z=1)
        )
        return [args]

    return dict(
        type="dropdown",
        direction="down",
        x=x_pos,
        y=1.13,
        xanchor="left",
        yanchor="top",
        showactive=True,
        active=0,
        bgcolor="white",
        bordercolor="lightgray",
        font=dict(size=11),
        buttons=[
            dict(
                label="Perspective",
                method="relayout",
                args=cam_args("perspective", 1.5, 1.5, 1.5)
            ),
            dict(
                label="Orthographic",
                method="relayout",
                args=cam_args("orthographic", 2.5, 2.5, 2.5)
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
    points_display=None,
):
    """
    Display one or more CadQuery objects as an interactive 3D Plotly figure.

    Accepts a mixed list of CadQuery Workplane objects, cq.Vector points,
    and [x, y, z] lists. Workplane objects are tessellated into meshes;
    points are rendered as Scatter3d markers.

    Equal scale is enforced: 1 unit in X occupies the same screen distance
    as 1 unit in Y or Z, in both perspective and orthographic modes.

    Parameters
    ----------
    objects                 : object or list — CadQuery Workplane, cq.Vector,
                              or [x, y, z] list, or any mix of these
    names                   : list of legend labels (optional)
    colors                  : list of face colors for mesh objects —
                              see https://plotly.com/python/css-colors/
    opacity                 : solid opacity for mesh objects — 1.0 = fully opaque
    visible_axes            : initial axes visibility —
                              None = no axes, "x"/"y"/"z"/"xy"/"xz"/"yz"/"xyz" (default)
    z                       : elevation of the base plane; None = no plane (default)
    plane_color             : color of the base plane
    plane_size              : half-side length of the base plane quad
    plane_opacity           : opacity of the base plane
    tessellation_tolerance  : mesh precision — smaller = finer, slower
    padding                 : fraction of bounding box span added as axis margin
    points_display          : dict to configure point markers. Keys (all optional):
                                size    — marker size in pixels (default 5)
                                color   — marker color (default "red")
                                symbol  — marker shape (default "circle")
                                         other options: "square", "diamond",
                                         "cross", "x", "circle-open"
                                opacity — marker opacity (default 1.0)
    """
    show_x, show_y, show_z = _axes_from_string(visible_axes)

    traces, all_x, all_y, all_z = _build_traces(
        objects, names, colors, opacity,
        tessellation_tolerance, points_display
    )

    if z is not None:
        traces.insert(0, _base_plane(
            size=plane_size,
            color=plane_color,
            opacity=plane_opacity,
            z=z
        ))

    xmin, xmax = min(all_x), max(all_x)
    ymin, ymax = min(all_y), max(all_y)
    zmin, zmax = min(all_z), max(all_z)

    x_range, y_range, z_range = _equal_ranges(
        xmin, xmax, ymin, ymax, zmin, zmax, padding
    )

    if z is not None:
        x_range, y_range, z_range = _expand_for_plane(
            x_range, y_range, z_range, plane_size, z
        )

    menu_x   = _make_axis_toggle("X", "xaxis", show_x, x_range, x_pos=0.00)
    menu_y   = _make_axis_toggle("Y", "yaxis", show_y, y_range, x_pos=0.18)
    menu_z   = _make_axis_toggle("Z", "zaxis", show_z, z_range, x_pos=0.36)
    menu_cam = _make_camera_menu(x_pos=0.56)

    annotations = [
        dict(text="Axes:", x=-0.01, y=1.17, xref="paper", yref="paper",
             showarrow=False, font=dict(size=11), xanchor="right"),
        dict(text="Camera:", x=0.54,  y=1.17, xref="paper", yref="paper",
             showarrow=False, font=dict(size=11), xanchor="right"),
    ]

    fig = go.Figure(data=traces)
    fig.update_layout(
        scene=dict(
            aspectmode="manual",
            aspectratio=_EQUAL_ASPECT,
            xaxis=_axis_dict(show_x, x_range),
            yaxis=_axis_dict(show_y, y_range),
            zaxis=_axis_dict(show_z, z_range),
            camera=dict(
                projection=dict(type="perspective"),
                eye=dict(x=1.5, y=1.5, z=1.5),
                up=dict(x=0, y=0, z=1)
            )
        ),
        updatemenus=[menu_x, menu_y, menu_z, menu_cam],
        annotations=annotations,
        legend=dict(x=0, y=1),
        margin=dict(l=0, r=0, t=90, b=0)
    )

    fig.show()
