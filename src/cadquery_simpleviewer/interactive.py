import inspect
import json
import uuid

from plotly.utils import PlotlyJSONEncoder

from .viewer import _build_figure
from .exporter import resolve_export_config, export_step
from .ifc_exporter import (
    resolve_ifc_export_config, resolve_ifc_config, export_ifc_proxy, _ifcopenshell_available,
)
from ._export_ui import build_export_widget
from ._optional_widgets import (
    widgets, display, clear_output, HTML, Javascript,
    enable_colab_custom_widget_manager,
)

_UIREVISION = "cadquery-simpleviewer"


def _make_slider(widgets, name, spec):
    """
    Build an ipywidgets slider from a (min, max[, step[, default]]) spec,
    or pass an already-constructed ipywidgets widget straight through.
    """
    if hasattr(spec, "value") and not isinstance(spec, (tuple, list)):
        # Caller supplied a ready-made ipywidgets widget (Dropdown,
        # Checkbox, IntSlider with custom description, etc.)
        return spec

    if not isinstance(spec, (tuple, list)) or len(spec) not in (2, 3, 4):
        raise ValueError(
            f"control {name!r} must be a (min, max), (min, max, step), "
            f"(min, max, step, default) tuple, or an ipywidgets widget, "
            f"got {spec!r}"
        )

    minimum = spec[0]
    maximum = spec[1]
    step = spec[2] if len(spec) >= 3 else None
    default = spec[3] if len(spec) == 4 else None

    all_int = all(
        isinstance(v, int) and not isinstance(v, bool)
        for v in (minimum, maximum, *([step] if step is not None else []),
                   *([default] if default is not None else []))
    )

    if step is None:
        step = 1 if all_int else (maximum - minimum) / 100 or 1
    if default is None:
        default = (minimum + maximum) / 2
        if all_int:
            default = int(round(default))

    slider_cls = widgets.IntSlider if all_int else widgets.FloatSlider

    return slider_cls(
        min=minimum, max=maximum, step=step, value=default,
        description=name, continuous_update=False,
    )


def interactive(*, show_kwargs=None, continuous_update=False, **controls):
    """
    Decorator that turns a CAD model-building function into a slider-driven
    live view, rendered with Plotly exactly like show() — no FigureWidget,
    just standard ipywidgets sliders driving a rebuild. Unlike show(), the
    chart itself is drawn once into a fixed div and patched in place via
    Plotly.react() on every slider change, so the camera angle/zoom you
    leave it at is preserved across redraws instead of resetting — a
    "Reset View" button on the chart snaps back to the default framing.
    Works in JupyterLab, VS Code notebooks, and Google Colab; in Colab
    specifically this transparently enables Colab's custom widget manager,
    since Colab's default widget frontend doesn't execute the JS Plotly
    injects to draw or update a chart inside an Output widget otherwise.

    The decorated function is expected to accept the same keyword names
    given in **controls, and return either:
      - the object(s) show()/_build_figure() already accepts (a single
        CadQuery/build123d object, or a list of them) — rendered with the
        show_kwargs given here, or
      - a dict with an "objects" key (the object(s) to render, same as
        above) plus any other _build_figure()/show() parameter name
        (colors, opacity, z, ...) to override show_kwargs for that one
        render only, e.g. to flag invalid geometry:

            @interactive(radius=(1, 9), show_kwargs=dict(colors=["steelblue"]))
            def model(radius):
                box = cq.Workplane("XY").box(10, 10, 2)
                if radius >= 5:
                    return {"objects": box, "colors": ["indianred"]}
                return box

    Applying the decorator immediately builds the sliders, renders the
    initial figure, and displays both in the current cell's output — no
    separate call needed, e.g.:

        @interactive(width=(1, 10, 0.5, 5), height=(1, 8, 0.5, 3),
                     show_kwargs=dict(colors=["steelblue"], z=0))
        def model(width, height):
            return cq.Workplane("XY").box(width, height, 2)

    The decorated function itself is returned unchanged, so it stays
    callable normally (e.g. from tests) without the widget side effect.

    Parameters
    ----------
    show_kwargs        : dict of display options forwarded to
                          _build_figure() on every rebuild — same keys
                          show() accepts (names, colors, opacity,
                          visible_axes, z, plane_color, plane_size,
                          plane_opacity, tessellation_tolerance,
                          angular_tolerance, flat_shading, padding,
                          points_display, lines_display), plus "export",
                          "export_ifc", and "ifc_config" (see show()'s
                          `export`, `export_ifc`, and `ifc_config`
                          parameters) — the export formats are offered
                          together as options in one "Export"
                          dropdown+button row, and always export the
                          object(s) built from the sliders' *current*
                          values at the moment the button is clicked, not
                          the initial render. Kept separate from
                          **controls so they can never collide with a
                          model parameter name.
    continuous_update   : applied to every generated slider — False
                          (default) rebuilds only when the slider is
                          released, since a CAD rebuild + tessellation
                          isn't instant and per-tick updates on complex
                          geometry would lag or queue up. Pass True for
                          live dragging on cheap/fast geometry. Widgets
                          passed directly in **controls are used as-is
                          and are not overridden by this setting.
    **controls          : one entry per slider, keyed by the matching
                          parameter name of the decorated function. Each
                          value is either a (min, max), (min, max, step),
                          or (min, max, step, default) tuple, or an
                          already-constructed ipywidgets widget (Dropdown,
                          Checkbox, etc.) for full control.
    """
    if widgets is None:
        raise ImportError(
            "interactive() requires ipywidgets and IPython. Install with "
            "`pip install cadquery-simpleviewer[interactive]` "
            "(or `pip install ipywidgets` if IPython is already present)."
        )

    show_kwargs = dict(show_kwargs) if show_kwargs else {}
    export_cfg = resolve_export_config(show_kwargs.pop("export", None))
    export_ifc_cfg = resolve_ifc_export_config(show_kwargs.pop("export_ifc", None))
    ifc_cfg = resolve_ifc_config(show_kwargs.pop("ifc_config", None))
    figure_kwargs = dict(
        names=None, colors=None, opacity=1.0, visible_axes="xyz", z=None,
        plane_color="whitesmoke", plane_size=50, plane_opacity=0.8,
        tessellation_tolerance=0.01, angular_tolerance=0.1,
        flat_shading=False, padding=0.15,
        points_display=None, lines_display=None,
    )
    figure_kwargs.update(show_kwargs)

    def _decorate(build_fn):
        sig = inspect.signature(build_fn)
        for name in controls:
            if name not in sig.parameters:
                raise ValueError(
                    f"control {name!r} does not match any parameter of "
                    f"{build_fn.__name__}{sig}"
                )

        sliders = {}
        for name, spec in controls.items():
            slider = _make_slider(widgets, name, spec)
            if not (hasattr(spec, "value") and not isinstance(spec, (tuple, list))):
                slider.continuous_update = continuous_update
            sliders[name] = slider

        div_id = f"cqsv-{uuid.uuid4().hex}"
        plot_output = widgets.Output()
        js_output = widgets.Output()
        state = {"rendered": False}

        def _redraw(*_change):
            # Called directly from each slider's .observe() callback, not
            # from ipywidgets.interactive_output() — that helper wraps the
            # call in its own managing Output, and nesting a second,
            # separately-displayed Output inside it (which the first-render
            # / redraw paths below both need) can end up sharing the same
            # frontend routing id, so the figure renders into the hidden
            # Output instead of the one actually shown on screen.
            values = {name: slider.value for name, slider in sliders.items()}
            result = build_fn(**values)

            if isinstance(result, dict):
                if "objects" not in result:
                    raise ValueError(
                        "a dict returned by the decorated function must "
                        "include an 'objects' key with the object(s) to render"
                    )
                overrides = {k: v for k, v in result.items() if k != "objects"}
                unknown = sorted(set(overrides) - set(figure_kwargs))
                if unknown:
                    raise ValueError(
                        f"unknown show() parameter(s) in returned dict: {unknown}"
                    )
                call_kwargs = {**figure_kwargs, **overrides}
                objects = result["objects"]
            else:
                call_kwargs = figure_kwargs
                objects = result

            fig = _build_figure(
                objects,
                call_kwargs["names"], call_kwargs["colors"],
                call_kwargs["opacity"], call_kwargs["visible_axes"],
                call_kwargs["z"], call_kwargs["plane_color"],
                call_kwargs["plane_size"], call_kwargs["plane_opacity"],
                call_kwargs["tessellation_tolerance"],
                call_kwargs["angular_tolerance"],
                call_kwargs["flat_shading"], call_kwargs["padding"],
                call_kwargs["points_display"], call_kwargs["lines_display"],
            )
            fig.update_layout(scene=dict(uirevision=_UIREVISION))

            if not state["rendered"]:
                state["rendered"] = True
                with plot_output:
                    display(HTML(fig.to_html(
                        div_id=div_id, include_plotlyjs="cdn", full_html=False
                    )))
            else:
                # Patch the existing chart in place instead of rebuilding
                # it, and omit scene.camera from the patch entirely — this
                # is what makes Plotly.react() keep the camera angle/zoom
                # the user currently has instead of resetting it back to
                # the figure's default.
                fig_json = fig.to_plotly_json()
                layout_patch = fig_json["layout"]
                layout_patch.get("scene", {}).pop("camera", None)
                data_json = json.dumps(fig_json["data"], cls=PlotlyJSONEncoder)
                layout_json = json.dumps(layout_patch, cls=PlotlyJSONEncoder)
                with js_output:
                    clear_output(wait=True)
                    display(Javascript(
                        f"Plotly.react({json.dumps(div_id)}, {data_json}, {layout_json});"
                    ))

        for slider in sliders.values():
            slider.observe(_redraw, names="value")
        _redraw()

        def _current_export_objects():
            values = {name: slider.value for name, slider in sliders.items()}
            result = build_fn(**values)
            return result["objects"] if isinstance(result, dict) else result

        formats = []
        if export_cfg is not None:
            formats.append((
                "STEP",
                lambda: export_step(
                    _current_export_objects(), export_cfg["filename"], export_cfg["unit"]
                ),
            ))
        if export_ifc_cfg is not None and _ifcopenshell_available():
            formats.append((
                "IFC Proxy",
                lambda: export_ifc_proxy(
                    _current_export_objects(), export_ifc_cfg["filename"],
                    names=figure_kwargs["names"], unit=export_ifc_cfg["unit"],
                    schema=ifc_cfg["schema"],
                    tessellation_tolerance=figure_kwargs["tessellation_tolerance"],
                    angular_tolerance=figure_kwargs["angular_tolerance"],
                ),
            ))

        export_widget = build_export_widget(formats)
        vbox_children = (
            ([export_widget] if export_widget is not None else [])
            + [widgets.VBox(list(sliders.values())), plot_output, js_output]
        )

        enable_colab_custom_widget_manager()
        display(widgets.VBox(vbox_children))

        return build_fn

    return _decorate
