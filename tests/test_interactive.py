import sys
import types

import ipywidgets as widgets
import plotly.graph_objects as go
import pytest
from unittest.mock import MagicMock, patch

cq = pytest.importorskip("cadquery")

from cadquery_simpleviewer.interactive import interactive, _make_slider


# ── fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _no_display():
    """Every test patches display so nothing tries to touch a real IPython
    frontend, and patches go.Figure.show so no browser tab is opened."""
    with patch("cadquery_simpleviewer.interactive.display") as mock_display, \
         patch("cadquery_simpleviewer.viewer.go.Figure.show"):
        yield mock_display


# ── _make_slider ──────────────────────────────────────────────────────────────

def test_make_slider_int_tuple_is_int_slider():
    slider = _make_slider(widgets, "width", (1, 10))
    assert isinstance(slider, widgets.IntSlider)
    assert slider.min == 1 and slider.max == 10
    assert 1 <= slider.value <= 10


def test_make_slider_float_tuple_is_float_slider():
    slider = _make_slider(widgets, "radius", (0.5, 3.5))
    assert isinstance(slider, widgets.FloatSlider)
    assert slider.min == 0.5 and slider.max == 3.5


def test_make_slider_explicit_step_and_default():
    slider = _make_slider(widgets, "height", (1, 10, 0.5, 7))
    assert slider.step == 0.5
    assert slider.value == 7


def test_make_slider_passthrough_widget():
    dropdown = widgets.Dropdown(options=["a", "b"], value="a")
    result = _make_slider(widgets, "mode", dropdown)
    assert result is dropdown


def test_make_slider_invalid_spec_raises():
    with pytest.raises(ValueError):
        _make_slider(widgets, "bad", "not-a-spec")


# ── interactive() decorator ──────────────────────────────────────────────────

def test_interactive_returns_original_function():
    @interactive(width=(1, 10))
    def model(width):
        return cq.Workplane("XY").box(width, 3, 2)

    assert model(5).val().Volume() > 0


def test_interactive_builds_one_slider_per_control(_no_display):
    @interactive(width=(1, 10), height=(1, 8))
    def model(width, height):
        return cq.Workplane("XY").box(width, height, 2)

    vbox = _no_display.call_args[0][0]
    controls_box = vbox.children[0]
    assert len(controls_box.children) == 2


def test_interactive_unknown_control_raises():
    with pytest.raises(ValueError):
        @interactive(depth=(1, 10))
        def model(width):
            return cq.Workplane("XY").box(width, 3, 2)


def test_interactive_initial_render_calls_build_fn():
    calls = []

    @interactive(width=(1, 10, 1, 5))
    def model(width):
        calls.append(width)
        return cq.Workplane("XY").box(width, 3, 2)

    assert calls == [5]


def test_interactive_show_kwargs_forwarded():
    captured = {}
    original_figure = go.Figure

    def spy_figure(*args, **kwargs):
        fig = original_figure(*args, **kwargs)
        captured["fig"] = fig
        return fig

    with patch("cadquery_simpleviewer.viewer.go.Figure", side_effect=spy_figure):
        @interactive(width=(1, 10, 1, 5), show_kwargs=dict(colors=["indianred"]))
        def model(width):
            return cq.Workplane("XY").box(width, 3, 2)

    mesh_traces = [t for t in captured["fig"].data if isinstance(t, go.Mesh3d)]
    assert mesh_traces[0].color == "indianred"


# ── dict return overrides ───────────────────────────────────────────────────

def _spy_last_figure():
    """Patch go.Figure to capture the most recently built Figure, returning
    the dict of captured state and the unittest.mock.patch context manager."""
    captured = {}
    original_figure = go.Figure

    def spy_figure(*args, **kwargs):
        fig = original_figure(*args, **kwargs)
        captured["fig"] = fig
        return fig

    return captured, patch("cadquery_simpleviewer.viewer.go.Figure", side_effect=spy_figure)


def test_interactive_dict_return_overrides_show_kwargs():
    captured, spy = _spy_last_figure()

    with spy:
        @interactive(radius=(1, 9, 1, 5), show_kwargs=dict(colors=["steelblue"]))
        def model(radius):
            box = cq.Workplane("XY").box(10, 10, 2)
            if radius >= 5:
                return {"objects": box, "colors": ["indianred"]}
            return box

    mesh_traces = [t for t in captured["fig"].data if isinstance(t, go.Mesh3d)]
    assert mesh_traces[0].color == "indianred"


def test_interactive_plain_return_still_uses_show_kwargs():
    captured, spy = _spy_last_figure()

    with spy:
        @interactive(radius=(1, 9, 1, 2), show_kwargs=dict(colors=["steelblue"]))
        def model(radius):
            box = cq.Workplane("XY").box(10, 10, 2)
            if radius >= 5:
                return {"objects": box, "colors": ["indianred"]}
            return box

    mesh_traces = [t for t in captured["fig"].data if isinstance(t, go.Mesh3d)]
    assert mesh_traces[0].color == "steelblue"


def test_interactive_dict_without_objects_key_raises():
    with pytest.raises(ValueError, match="objects"):
        @interactive(radius=(1, 9, 1, 5))
        def model(radius):
            return {"colors": ["indianred"]}


def test_interactive_dict_with_unknown_key_raises():
    with pytest.raises(ValueError, match="unknown"):
        @interactive(radius=(1, 9, 1, 5))
        def model(radius):
            box = cq.Workplane("XY").box(10, 10, 2)
            return {"objects": box, "not_a_real_param": 123}


# ── Colab custom widget manager ────────────────────────────────────────────

def test_interactive_skips_colab_setup_outside_colab():
    assert "google.colab" not in sys.modules

    @interactive(width=(1, 10))
    def model(width):
        return cq.Workplane("XY").box(width, 3, 2)
    # No google.colab module present, so nothing to assert on directly —
    # this just documents/guards that decorating outside Colab doesn't
    # try to import google.colab and blow up.


def test_interactive_enables_colab_custom_widget_manager(monkeypatch):
    fake_output = MagicMock()
    fake_colab_output_module = types.ModuleType("google.colab.output")
    fake_colab_output_module.enable_custom_widget_manager = fake_output
    fake_colab_module = types.ModuleType("google.colab")
    fake_colab_module.output = fake_colab_output_module
    fake_google_module = types.ModuleType("google")
    fake_google_module.colab = fake_colab_module

    monkeypatch.setitem(sys.modules, "google", fake_google_module)
    monkeypatch.setitem(sys.modules, "google.colab", fake_colab_module)
    monkeypatch.setitem(sys.modules, "google.colab.output", fake_colab_output_module)

    @interactive(width=(1, 10))
    def model(width):
        return cq.Workplane("XY").box(width, 3, 2)

    fake_output.assert_called_once_with()


def test_interactive_missing_ipywidgets_raises_import_error():
    # monkeypatch.setattr("cadquery_simpleviewer.interactive.widgets", ...)
    # resolves through the package's `interactive` name first, which
    # __init__.py has already rebound to the interactive() function itself
    # (from .interactive import interactive) — patch() imports the dotted
    # module path directly instead, avoiding that shadowing.
    with patch("cadquery_simpleviewer.interactive.widgets", None):
        with pytest.raises(ImportError):
            @interactive(width=(1, 10))
            def model(width):
                return cq.Workplane("XY").box(width, 3, 2)
