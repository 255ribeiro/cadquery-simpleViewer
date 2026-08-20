# Add slider-driven interactive `show()` for Colab/Jupyter

## Context

The user wants to add sliders that control parameter values (e.g. box dimensions, hole radius, fillet size) and live-update the `show()` output, and it must work in Google Colab specifically.

Colab imposes a real constraint discovered in this repo's own README ([README.md:274-352](../README.md#L274-L352)): Colab's IPython/kernel bootstrap is fragile, and third-party ("custom") Jupyter widgets — like Plotly's `go.FigureWidget`, which needs `google.colab.output.enable_custom_widget_manager()` — are a heavier, less reliable path there. Colab does, however, ship **core `ipywidgets`** (sliders, buttons, `Output`, layout boxes) preinstalled with first-class rendering support, no extension/manager needed — matching this project's existing promise ("No extensions or widget managers are needed", [README.md:352](../README.md#L352)).

So the design avoids `FigureWidget` entirely. Instead: standard `ipywidgets` sliders drive a callback that rebuilds the CAD shape, rebuilds a fresh `go.Figure` (reusing all of `show()`'s existing figure-building logic), and redraws it into an `ipywidgets.Output` region via `clear_output(wait=True)`. This is the most Colab-compatible pattern and requires no new fragile dependency chain (ipywidgets doesn't force an `ipython` upgrade the way `build123d` does).

Per the user's confirmed preference, slider updates fire **on release**, not on every drag tick — CAD rebuild + tessellation isn't instant, so live-per-tick updates would lag or queue up on nontrivial geometry. This is controlled by ipywidgets' own `continuous_update=False`, exposed as an overridable option.

## Changes

**0. Branch + save this plan into the project**

- Create and check out a new git branch (`feature/interactive-sliders`) off `main` for this work.
- Create `todo/` at the project root and write this plan document to `todo/interactive-sliders.md`.

**1. Refactor `src/cadquery_simpleviewer/viewer.py` — extract figure building from display**

Currently `show()` ([viewer.py:399-533](../src/cadquery_simpleviewer/viewer.py#L399-L533)) builds a `go.Figure` and immediately calls `fig.show()` at the end, with no way to get the `Figure` back. Split it:

- New `_build_figure(objects, names, colors, opacity, visible_axes, z, plane_color, plane_size, plane_opacity, tessellation_tolerance, angular_tolerance, flat_shading, padding, points_display, lines_display) -> go.Figure` — everything currently in `show()` from `show_x, show_y, show_z = _axes_from_string(...)` through the `fig.update_layout(...)` call, returning `fig` instead of calling `.show()`.
- `show()` keeps its full signature and docstring unchanged, becomes a thin wrapper: build via `_build_figure(...)` then `fig.show()`.

This is a pure refactor (no behavior change for `show()`), verified by the existing test suite passing unchanged.

**2. New module `src/cadquery_simpleviewer/interactive.py`**

Public **decorator** `interactive(*, show_kwargs=None, continuous_update=False, **controls)`, applied directly over a model-building function — mirrors `ipywidgets`' own `@interact(...)` decorator idiom:

```python
from cadquery_simpleviewer import interactive

@interactive(width=(1, 10, 0.5, 5), height=(1, 8, 0.5, 3),
             show_kwargs=dict(colors=["steelblue"], z=0))
def model(width, height):
    return cq.Workplane("XY").box(width, height, 2)
```

Running that cell is enough — sliders and the rendered figure appear immediately, no separate call needed (same UX as `ipywidgets.interact`). `model` itself is returned unmodified by the decorator, so it stays callable normally elsewhere (e.g. in tests) without the widget side effect.

- `**controls`: keyword name must match a parameter of the decorated function. Each value is either:
  - a `(min, max, step, default)` tuple (`default` optional, midpoint used if omitted) — becomes `ipywidgets.FloatSlider`/`IntSlider` (int slider chosen when min/max/step/default are all `int`),
  - or an already-constructed `ipywidgets` widget, for callers who want a `Dropdown`, `Checkbox`, etc.
- `show_kwargs`: dict forwarded to `_build_figure()` for display options (`names`, `colors`, `opacity`, `visible_axes`, `z`, `plane_*`, `tessellation_tolerance`, `angular_tolerance`, `flat_shading`, `padding`, `points_display`, `lines_display`). Kept as a single nested dict (not `**kwargs` alongside `**controls`) so it can never collide with a model parameter name.
- `continuous_update`: forwarded to every generated slider widget; `False` (update on release) by default per the user's choice, settable to `True` for live dragging on cheap geometry.

Implementation, inside `interactive(...)` returning a real decorator `_decorate(build_fn)`:
- Lazy-import `ipywidgets` and `IPython.display.{display, clear_output}`; raise a clear `ImportError` ("pip install cadquery-simpleviewer[interactive]" / "pip install ipywidgets") if unavailable, so the base package stays dependency-light.
- Build one slider (or pass through a supplied widget) per `controls` entry, keyed by the matching parameter name.
- `output = ipywidgets.Output()`.
- `def _redraw(**values): ` inside, do `with output: clear_output(wait=True); _build_figure(build_fn(**values), **(show_kwargs or {})).show()`.
- Wire with `ipywidgets.interactive_output(_redraw, sliders)` (not `interact()`, so layout is controllable) — this also fires one initial draw automatically.
- `display(ipywidgets.VBox([ipywidgets.VBox(list(sliders.values())), output]))` as a side effect of applying the decorator.
- Return `build_fn` unchanged from `_decorate`.

**3. `src/cadquery_simpleviewer/__init__.py`**
Export the new decorator: `from .interactive import interactive`, add to `__all__`.

**4. `pyproject.toml`**
Add a new optional extra:
```toml
[project.optional-dependencies]
...
interactive = ["ipywidgets>=7.0"]
```
Loose lower bound only, deliberately — Colab already ships a compatible `ipywidgets`, so this extra should be satisfiable there without pulling an upgrade (avoiding a repeat of the `ipython`-upgrade issue already documented for `build123d` in the README).

**5. `README.md`**
Add a "Sliders / interactive parameters" section under the existing Colab section, with a minimal runnable example using `@interactive(...)` (e.g. a box whose width/height are slider-controlled) and a note on the on-release default and how to switch to live updates.

## Verification

- Run `pytest` to confirm the `_build_figure`/`show()` refactor is behavior-preserving (existing `tests/test_viewer.py` assertions on trace construction, colors, bbox, etc. all still pass).
- Add unit tests in `tests/test_interactive.py` covering: `controls` tuple → correct slider widget type/count, `build_fn` receiving the right keyword values, the `ImportError` path when `ipywidgets` is mocked as absent, and that `_build_figure` output feeding a rebuild produces a valid `go.Figure` (mirrors patterns already in `tests/test_viewer.py`).
- Manually smoke-test in this environment: build a simple parametric example (box width/height sliders) decorated with `@interactive(...)` in a local Jupyter kernel to confirm sliders render and rebuild the figure on release.
- Ask the user to confirm the actual Colab rendering (sliders + figure redraw together in one cell) since this environment can't run a live Colab notebook — flag this explicitly as unverified-by-me in the final report.
