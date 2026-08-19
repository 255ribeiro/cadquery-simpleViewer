import plotly.graph_objects as go
from .adapters import get_adapter
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

_DEFAULT_LINES_DISPLAY = dict(
    color="steelblue",
    width=2,
    mode="lines",       # "lines", "lines+markers"
    samples=50,         # number of sample points along the curve
    opacity=1.0,
)

_VALID_AXES = {None, "x", "y", "z", "xy", "xz", "yz", "xyz"}

_EQUAL_ASPECT = dict(x=1, y=1, z=1)


# ── plain point detection (no CAD library involved) ────────────────────────────

def _is_plain_point(obj):
    """Return True if obj is a list/tuple of exactly 3 numbers."""
    if isinstance(obj, (list, tuple)) and len(obj) == 3:
        return all(isinstance(v, (int, float)) for v in obj)
    return False


def _plain_point_to_xyz(obj):
    """Extract (x, y, z) from a [x, y, z] list/tuple."""
    return float(obj[0]), float(obj[1]), float(obj[2])


# ── axis style ────────────────────────────────────────────────────────────────

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


# ── trace building ────────────────────────────────────────────────────────────

def _build_traces(objects, names, colors, opacity,
                  tessellation_tolerance, points_display, lines_display,
                  angular_tolerance=0.1, flat_shading=False):
    """
    Build Plotly traces from a mixed list of CadQuery and/or build123d objects.

    Solid (CadQuery Workplane / build123d Part, Sketch, Solid, Compound)
                                       → go.Mesh3d  (tessellated)
    Edge / Wire                       → go.Scatter3d (sampled lines)
    Vector / [x, y, z]                → go.Scatter3d (markers)

    Which library an object belongs to is resolved per-object via
    adapters.get_adapter(), so CadQuery and build123d objects can be
    freely mixed in the same call.

    Returns (traces, all_x, all_y, all_z) where the coordinate lists span
    all objects for bounding box computation.
    """
    if not isinstance(objects, list):
        objects = [objects]

    # Merge caller dicts with defaults (caller wins)
    p_style = dict(_DEFAULT_POINTS_DISPLAY)
    if points_display is not None:
        p_style.update(points_display)

    l_style = dict(_DEFAULT_LINES_DISPLAY)
    if lines_display is not None:
        l_style.update(lines_display)

    samples = int(l_style.get("samples", 50))

    traces          = []
    all_x           = []
    all_y           = []
    all_z           = []
    mesh_color_index = 0

    for index in range(len(objects)):
        obj  = objects[index]
        name = names[index] if names else "Object " + str(index + 1)

        adapter = get_adapter(obj)

        # ── Workplane with pending wire (e.g. .rect(), .circle(), .polygon()) ──
        if adapter and adapter.is_pending_wire(obj):
            obj = adapter.extract_wire(obj)

        # ── Edge ──────────────────────────────────────────────────────────
        if adapter and adapter.is_edge(obj):
            x, y, z = adapter.sample_edge(obj, samples)

            # Filter None values for bounding box
            all_x.extend(v for v in x if v is not None)
            all_y.extend(v for v in y if v is not None)
            all_z.extend(v for v in z if v is not None)

            traces.append(go.Scatter3d(
                x=x, y=y, z=z,
                mode=l_style.get("mode", "lines"),
                line=dict(
                    color=l_style.get("color", "red"),
                    width=l_style.get("width", 2),
                ),
                opacity=l_style.get("opacity", 1.0),
                name=name,
                showlegend=True,
            ))

        # ── Wire ──────────────────────────────────────────────────────────
        elif adapter and adapter.is_wire(obj):
            x, y, z = adapter.sample_wire(obj, samples)

            all_x.extend(v for v in x if v is not None)
            all_y.extend(v for v in y if v is not None)
            all_z.extend(v for v in z if v is not None)

            traces.append(go.Scatter3d(
                x=x, y=y, z=z,
                mode=l_style.get("mode", "lines"),
                line=dict(
                    color=l_style.get("color", "red"),
                    width=l_style.get("width", 2),
                ),
                opacity=l_style.get("opacity", 1.0),
                name=name,
                showlegend=True,
            ))

        # ── Point ─────────────────────────────────────────────────────────
        elif (adapter and adapter.is_point(obj)) or (adapter is None and _is_plain_point(obj)):
            px, py, pz = adapter.point_to_xyz(obj) if adapter else _plain_point_to_xyz(obj)
            all_x.append(px)
            all_y.append(py)
            all_z.append(pz)

            traces.append(go.Scatter3d(
                x=[px], y=[py], z=[pz],
                mode="markers",
                marker=dict(
                    size=p_style.get("size", 5),
                    color=p_style.get("color", "red"),
                    symbol=p_style.get("symbol", "circle"),
                    opacity=p_style.get("opacity", 1.0),
                ),
                name=name,
                showlegend=True,
            ))

        # ── Solid ─────────────────────────────────────────────────────────
        else:
            if adapter is None:
                raise TypeError(f"Unrecognized object type for show(): {type(obj)!r}")

            x, y, z, ii, jj, kk = adapter.tessellate_solid(
                obj, tessellation_tolerance, angular_tolerance
            )

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
                flatshading=flat_shading,
                showlegend=True,
                lighting=dict(ambient=0.4, diffuse=0.8, specular=0.2)
            ))

    return traces, all_x, all_y, all_z


# ── range helpers ─────────────────────────────────────────────────────────────

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
    half = max(half, 1.0)

    return (
        [x_center - half, x_center + half],
        [y_center - half, y_center + half],
        [z_center - half, z_center + half],
    )


def _expand_for_plane(x_range, y_range, z_range, plane_size, z_level):
    """
    Expand axis ranges to include the base plane extents so it is never
    clipped by the explicit axis ranges.
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


# ── UI controls ───────────────────────────────────────────────────────────────

def _make_axis_toggle(label, scene_key, initial_visible, val_range, x_pos):
    """Build an on/off button pair for one axis."""
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


# ── public API ────────────────────────────────────────────────────────────────

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
    angular_tolerance=0.1,
    flat_shading=False,
    padding=0.15,
    points_display=None,
    lines_display=None,
):
    """
    Display one or more CadQuery and/or build123d objects as an interactive
    3D Plotly figure.

    Accepts a mixed list of object types in any combination, from either
    library, in the same call:
      - Solid (CadQuery Workplane / build123d Part, Sketch, Solid, Compound)
                                    → tessellated mesh
      - Edge / Wire                → sampled line (works with straight lines,
                                      arcs, ellipses, splines, helices, etc.)
      - Vector / [x, y, z]         → point marker

    Equal scale is enforced: 1 unit in X occupies the same screen distance
    as 1 unit in Y or Z, in both perspective and orthographic modes.

    Parameters
    ----------
    objects                 : object or list — any mix of CadQuery Workplane
                              /Edge/Wire/Vector, build123d Part/Sketch/Curve/
                              Edge/Wire/Vector, or [x, y, z] lists
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
    tessellation_tolerance  : mesh precision (linear deflection) — smaller = finer, slower
    angular_tolerance       : mesh precision on curved surfaces, in radians —
                              smaller = smoother curves/fillets, slower.
                              Lower this (e.g. 0.05) if curved faces near a
                              boolean cut look faceted or moiré-patterned.
    flat_shading            : True = one flat normal per triangle (faceted,
                              low-poly look); False = smooth per-vertex
                              normals within each face (default) — fixes the
                              dark moiré patches that flat shading produces
                              on curved faces introduced by boolean ops.
    padding                 : fraction of bounding box span added as axis margin
    points_display          : dict to configure point markers. Keys (all optional):
                                size    — marker size in pixels (default 5)
                                color   — marker color (default "red")
                                symbol  — "circle", "square", "diamond",
                                          "cross", "x", "circle-open" (default "circle")
                                opacity — marker opacity (default 1.0)
    lines_display           : dict to configure edge/wire lines. Keys (all optional):
                                color   — line color (default "red")
                                width   — line width in pixels (default 2)
                                mode    — "lines" or "lines+markers" (default "lines")
                                samples — number of points sampled along each edge
                                          (default 50). Increase for tight curves,
                                          helices, or complex splines.
                                opacity — line opacity (default 1.0)
    """
    show_x, show_y, show_z = _axes_from_string(visible_axes)

    traces, all_x, all_y, all_z = _build_traces(
        objects, names, colors, opacity,
        tessellation_tolerance, points_display, lines_display,
        angular_tolerance=angular_tolerance, flat_shading=flat_shading
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
