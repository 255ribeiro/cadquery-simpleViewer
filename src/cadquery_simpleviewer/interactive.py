import inspect

from .viewer import _build_figure

try:
    import ipywidgets as widgets
    from IPython.display import display
except ImportError:
    widgets = None
    display = None


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
    no custom widget manager, so it works the same in JupyterLab, VS Code
    notebooks, and Google Colab.

    The decorated function is expected to accept the same keyword names
    given in **controls and return the object(s) show()/_build_figure()
    already accepts (a single CadQuery/build123d object, or a list of them).

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
                          points_display, lines_display). Kept separate
                          from **controls so it can never collide with a
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

        def _redraw(**values):
            # Runs inside the Output widget interactive_output() manages
            # (clear_output(wait=True) + capture already handled there) —
            # do not wrap this in a second, separately-displayed Output;
            # nested Output widgets can end up sharing the same frontend
            # routing id, so the figure renders into the hidden one instead
            # of the one actually shown on screen.
            fig = _build_figure(
                build_fn(**values),
                figure_kwargs["names"], figure_kwargs["colors"],
                figure_kwargs["opacity"], figure_kwargs["visible_axes"],
                figure_kwargs["z"], figure_kwargs["plane_color"],
                figure_kwargs["plane_size"], figure_kwargs["plane_opacity"],
                figure_kwargs["tessellation_tolerance"],
                figure_kwargs["angular_tolerance"],
                figure_kwargs["flat_shading"], figure_kwargs["padding"],
                figure_kwargs["points_display"], figure_kwargs["lines_display"],
            )
            fig.show()

        output = widgets.interactive_output(_redraw, sliders)

        display(widgets.VBox([widgets.VBox(list(sliders.values())), output]))

        return build_fn

    return _decorate
