# cadquery-simpleViewer

An interactive 3D viewer for [CadQuery](https://github.com/CadQuery/cadquery) and [build123d](https://github.com/gumyr/build123d) models, built on [Plotly](https://plotly.com/python/). Renders geometry directly inside Jupyter notebooks and Google Colab cells — no external software, no extensions, no server required.

---

## Features

- Interactive orbit, zoom and pan inside the notebook cell
- Supports CadQuery `Workplane`/`Edge`/`Wire`/`Vector`, build123d `Part`/`Sketch`/`Curve`/`Edge`/`Wire`/`Vector`, and `[x, y, z]` lists — mixed freely in the same call, even across both libraries at once
- Edge and wire rendering works with any curve type: straight lines, arcs, ellipses, splines, helices, B-splines
- Axes visibility toggles (X, Y, Z independently)
- Camera mode selector (Perspective / Orthographic)
- Optional ground plane at a chosen elevation
- Equal scale enforced across all three axes — 1 unit in X occupies the same screen distance as 1 unit in Y or Z
- Works in JupyterLab, VS Code notebooks, and Google Colab

---

## Installation

### pip

```bash
pip install cadquery-simpleviewer
```

### uv

```bash
uv add cadquery-simpleviewer
```

### pixi (PyPI source)

```bash
pixi add --pypi cadquery-simpleviewer
```

### Poetry

```bash
poetry add cadquery-simpleviewer
```

> **Note**: `cadquery-simpleviewer` declares `plotly` as a dependency but intentionally does not require `cadquery` or `build123d` themselves — install whichever library (or both) you use, via the `cadquery`, `build123d`, or `all` extras:
>
> ```bash
> pip install "cadquery-simpleviewer[cadquery]"
> pip install "cadquery-simpleviewer[build123d]"
> pip install "cadquery-simpleviewer[all]"       # both
> ```
>
> Requires Python 3.11+ (matching the minimum supported by current CadQuery and build123d releases). See the [CadQuery installation guide](https://cadquery.readthedocs.io/en/latest/installation.html) or the [build123d installation guide](https://build123d.readthedocs.io/en/latest/installation.html) for details on installing each library itself.

---

## Quick Start

```python
import cadquery as cq
from cadquery_simpleviewer import show

box = cq.Workplane("XY").box(5, 3, 2)
show(box)
```

### Quick Start (build123d)

```python
from build123d import BuildPart, Box
from cadquery_simpleviewer import show

with BuildPart() as bp:
    Box(5, 3, 2)

show(bp.part)
```

CadQuery and build123d objects can be mixed freely in the same `show()` call:

```python
import cadquery as cq
from build123d import BuildPart, Box
from cadquery_simpleviewer import show

cq_box = cq.Workplane("XY").box(5, 3, 2)

with BuildPart() as bp:
    Box(4, 4, 4)

show([cq_box, bp.part], names=["CadQuery box", "build123d box"])
```

### Multiple objects with names and colors

```python
box      = cq.Workplane("XY").box(5, 3, 2)
cylinder = cq.Workplane("XY").cylinder(6, 1).translate((8, 0, 0))

show(
    [box, cylinder],
    names=["Box", "Cylinder"],
    colors=["lightsteelblue", "indianred"]
)
```

### With a ground plane

```python
show(
    [box, cylinder],
    names=["Box", "Cylinder"],
    z=0,
    plane_color="gainsboro",
    plane_size=20
)
```

### Clean presentation (axes hidden)

```python
show(
    [box, cylinder],
    names=["Box", "Cylinder"],
    visible_axes=None,
    z=0,
    plane_color="whitesmoke",
    plane_size=20
)
```

---

## Displaying Edges and Wires

`show()` accepts `Edge` and `Wire` objects (from either library) alongside solids. Any curve type is supported — the geometry is sampled along the curve (`positionAt(t)` for CadQuery, `position_at(t)` for build123d), so the result faithfully follows arcs, splines, helices, and B-splines.

### Straight edge

```python
edge = cq.Edge.makeLine(cq.Vector(0, 0, 0), cq.Vector(5, 0, 0))
show(edge)

# build123d equivalent
from build123d import Edge
edge = Edge.make_line((0, 0, 0), (5, 0, 0))
show(edge)
```

### Arc

```python
arc = cq.Edge.makeCircle(radius=3.0)
show(arc, lines_display=dict(color="steelblue", width=3, samples=100))

# build123d equivalent
arc = Edge.make_circle(radius=3.0)
show(arc, lines_display=dict(color="steelblue", width=3, samples=100))
```

### Helix

```python
helix = cq.Wire.makeHelix(pitch=1.0, height=5.0, radius=2.0)
show(helix, lines_display=dict(color="seagreen", samples=200))
```

### Mixed solids and curves

```python
box  = cq.Workplane("XY").box(5, 3, 2)
arc  = cq.Edge.makeCircle(radius=4.0)
wire = cq.Wire.makePolygon(
    [cq.Vector(-3, -2, 0), cq.Vector(3, -2, 0), cq.Vector(3, 2, 0), cq.Vector(-3, 2, 0)],
    close=True,
)

show(
    [box, arc, wire],
    names=["Box", "Arc", "Rectangle"],
    lines_display=dict(color="indianred", width=2)
)
```

### Customising line appearance

Pass a `lines_display` dict to control the line style. All keys are optional.

```python
show(
    helix,
    lines_display=dict(
        color="steelblue",
        width=3,
        mode="lines+markers",
        samples=150,
        opacity=0.8
    )
)
```

| `lines_display` key | Default | Description |
|---------------------|---------|-------------|
| `color` | `"red"` | Line color — any CSS name or hex. See [Plotly CSS colors](https://plotly.com/python/css-colors/) |
| `width` | `2` | Line width in pixels |
| `mode` | `"lines"` | `"lines"` or `"lines+markers"` |
| `samples` | `50` | Number of points sampled along each edge. Increase for tight arcs, helices, or complex splines |
| `opacity` | `1.0` | Line opacity — `0.0` to `1.0` |

> **Choosing `samples`**: straight lines need only 2, a full circle looks smooth at 50–100, and a helix with many turns may need 200 or more. When in doubt, start high and reduce if performance is a concern.

---

## Displaying Points

`show()` accepts `cq.Vector`/build123d `Vector` objects and `[x, y, z]` lists alongside any other object type. Points are rendered as `Scatter3d` markers — no tessellation involved.

### Single point

```python
show(cq.Vector(2.5, 0, 1))

# List notation
show([2.5, 0, 1])

# build123d equivalent
from build123d import Vector
show(Vector(2.5, 0, 1))
```

### Points from edge division

```python
def divide_edge(edge, n):
    points = []
    for i in range(n + 1):
        t = i / n
        points.append(edge.positionAt(t))
    return points

edge   = cq.Edge.makeLine(cq.Vector(-5, 0, 0), cq.Vector(5, 0, 0))
points = divide_edge(edge, 8)

show(points, names=["P" + str(i) for i in range(len(points))])
```

### Mixed solids and points

```python
box    = cq.Workplane("XY").box(5, 3, 2)
corner = cq.Vector(2.5, 1.5, 1.0)

show(
    [box, corner],
    names=["Box", "Corner"],
    points_display=dict(size=8, color="red", symbol="diamond")
)
```

### Customising point appearance

| `points_display` key | Default | Options |
|----------------------|---------|---------|
| `size` | `5` | Any integer (pixels) |
| `color` | `"red"` | Any CSS color name or hex — see [Plotly CSS colors](https://plotly.com/python/css-colors/) |
| `symbol` | `"circle"` | `"circle"`, `"circle-open"`, `"square"`, `"diamond"`, `"cross"`, `"x"` |
| `opacity` | `1.0` | `0.0` – `1.0` |

> `points_display` and `lines_display` apply uniformly to all points and lines in the call respectively.

---

## Google Colab

### Using CadQuery — no restart needed

CadQuery has no `ipython` dependency, so installing the `cadquery` extra never
touches Colab's preinstalled packages:

```python
import sys
IN_COLAB = "google.colab" in sys.modules
if IN_COLAB:
    !pip install -q "cadquery-simpleviewer[cadquery]"

import cadquery as cq
from cadquery_simpleviewer import show

box = cq.Workplane("XY").box(5, 3, 2)
show(box)
```

### Using build123d — do not restart the runtime

`build123d` requires a newer `ipython` than the one Colab ships with, so a
plain `pip install "cadquery-simpleviewer[build123d]"` (or `[all]`) upgrades
`ipython` in place. **Do not restart the runtime after that.** Colab's own
kernel bootstrap (`google.colab._shell_customizations`) is only compatible
with the IPython version Colab ships by default — starting a new kernel on
top of the upgraded IPython fails immediately, and it fails on *every*
subsequent restart too, since the working version is no longer on disk. At
that point the only way back is "Disconnect and delete runtime" (a fresh VM).

The fix is to immediately pin `ipython` back down after installing, without
restarting. The already-running kernel keeps using the IPython it already
loaded into memory, so nothing in your current session breaks — and putting
the compatible version back on disk means a future restart (e.g. if Colab
recycles the runtime) won't hit the broken code path either:

```python
import sys

IN_COLAB = "google.colab" in sys.modules
if IN_COLAB:
    import subprocess
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q",
         "cadquery-simpleviewer[build123d]"],
        check=True,
    )
    # build123d pulls in a newer ipython than Colab's kernel bootstrap
    # tolerates. Put Colab's version back on disk — do NOT restart the
    # runtime, the current kernel already has the working ipython loaded.
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q",
         "ipython==7.34.0", "--no-deps"],
        check=True,
    )
else:
    print("Not running in Colab, skipping package installation.")


```

#### Testing installation

```python
# testing installation
from build123d import BuildPart, Box
from cadquery_simpleviewer import show

with BuildPart() as bp:
    Box(5, 3, 2)

show(bp.part)
```

Running this cell again later in the same session just reinstalls the same
pinned versions — safe to leave in the notebook.

The viewer renders inline as an interactive Plotly figure. No extensions or widget managers are needed.

---

## Sliders / Interactive Parameters

Wrap a model-building function with `@interactive(...)` to control its parameters with sliders and re-render on every change — in JupyterLab, VS Code notebooks, and Google Colab alike. It's built entirely on core `ipywidgets` (sliders, `Output`) driving a `show()`-style Plotly chart, patched in place on every change rather than rebuilt from scratch — so whatever camera angle and zoom you leave the chart at is preserved across slider moves instead of resetting. A "Reset View" button on the chart snaps back to the default framing at any time.

Because the camera direction is preserved in a normalized, equal-aspect view cube rather than in absolute coordinates, a very large jump in one dimension can still shift how the object sits in frame even though the *angle* stays the same — click "Reset View" (or the "Perspective"/"Orthographic" camera menu) to reframe.

```python
import cadquery as cq
from cadquery_simpleviewer import interactive

@interactive(width=(1, 10, 0.5, 5), height=(1, 8, 0.5, 3))
def model(width, height):
    return cq.Workplane("XY").box(width, height, 2)
```

Running that cell is enough — the sliders and the rendered model appear immediately, no separate call needed. `model` itself is returned unchanged by the decorator, so it can still be called directly like a normal function.

Each keyword passed to `@interactive(...)` must match a parameter name of the decorated function, and its value is either a slider spec or a ready-made `ipywidgets` widget:

```python
@interactive(
    width=(1, 10),              # (min, max)              — step defaults to 1 (int) or (max-min)/100
    height=(1, 8, 0.5),         # (min, max, step)         — default value defaults to the midpoint
    depth=(1, 5, 0.5, 2),       # (min, max, step, default)
)
def model(width, height, depth):
    return cq.Workplane("XY").box(width, height, depth)
```

Pass an `ipywidgets` widget directly for anything beyond a plain slider (a `Dropdown`, `Checkbox`, etc.):

```python
import ipywidgets as widgets

@interactive(shape=widgets.Dropdown(options=["box", "cylinder"], value="box"))
def model(shape):
    if shape == "box":
        return cq.Workplane("XY").box(4, 4, 4)
    return cq.Workplane("XY").cylinder(4, 2)
```

Display options (`colors`, `opacity`, `z`, `visible_axes`, etc. — the same keys `show()` accepts) go in a separate `show_kwargs` dict so they can never collide with a model parameter name:

```python
@interactive(
    width=(1, 10, 0.5, 5),
    show_kwargs=dict(colors=["steelblue"], z=0, plane_color="gainsboro"),
)
def model(width):
    return cq.Workplane("XY").box(width, 3, 2)
```

To override display options on a *specific* render — e.g. to flag invalid geometry — return a dict instead of the bare object(s). It must include an `"objects"` key (the object(s) to render, same as a plain return), and any other key must match a `show()` parameter name; those override `show_kwargs` for that render only, leaving `show_kwargs` itself untouched for the next one:

```python
@interactive(radius=(1, 9), show_kwargs=dict(colors=["steelblue"]))
def model(radius):
    box = cq.Workplane("XY").box(10, 10, 2)
    if radius >= 5:
        return {"objects": box, "colors": ["indianred"]}  # radius too big for this box
    return box
```

By default sliders rebuild the model **on release**, not on every drag tick — a CAD rebuild plus re-tessellation isn't instant, so live-per-tick updates can lag or queue up on nontrivial geometry. Pass `continuous_update=True` for live updates while dragging, best suited to cheap/fast geometry:

```python
@interactive(width=(1, 10), continuous_update=True)
def model(width):
    return cq.Workplane("XY").box(width, 3, 2)
```

`interactive()` requires `ipywidgets`, installed via the `interactive` extra (or included in `[all]`):

```bash
pip install "cadquery-simpleviewer[interactive]"
```

---

## `show()` Reference

```python
show(
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
    lines_display=None,
    export=None,
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `objects` | object or list | — | Any mix of CadQuery `Workplane`/`Edge`/`Wire`/`Vector`, build123d `Part`/`Sketch`/`Curve`/`Edge`/`Wire`/`Vector`, or `[x, y, z]` lists — objects from both libraries can be mixed in one call |
| `names` | list of str | `None` | Legend label for each object. Defaults to `"Object 1"`, `"Object 2"`, … |
| `colors` | list of str | `None` | Face color for each mesh object. Accepts CSS color names and hex. See [Plotly CSS colors](https://plotly.com/python/css-colors/). Defaults to a built-in palette |
| `opacity` | float | `1.0` | Surface opacity for mesh objects. `1.0` = fully opaque |
| `visible_axes` | str or None | `"xyz"` | Initial axes visibility. `None` hides all axes. Valid values: `None`, `"x"`, `"y"`, `"z"`, `"xy"`, `"xz"`, `"yz"`, `"xyz"` |
| `z` | float or None | `None` | Elevation of the ground plane. `None` = no plane drawn |
| `plane_color` | str | `"whitesmoke"` | Color of the ground plane |
| `plane_size` | float | `50` | Half-side length of the ground plane quad |
| `plane_opacity` | float | `0.8` | Opacity of the ground plane |
| `tessellation_tolerance` | float | `0.01` | Mesh precision for solid → triangle conversion. Smaller = finer, slower |
| `padding` | float | `0.15` | Fraction of the bounding box span added as margin on each axis |
| `points_display` | dict or None | `None` | Marker style for point objects. Keys: `size`, `color`, `symbol`, `opacity` |
| `lines_display` | dict or None | `None` | Line style for edge and wire objects. Keys: `color`, `width`, `mode`, `samples`, `opacity` |
| `export` | dict, False, or None | `None` | STEP export button config. `None` (default) shows the button, exporting in meters. `False` disables it. A dict customizes it (`filename`, `unit` — `"M"` or `"MM"`) — see [Exporting to STEP](#exporting-to-step) |

### Interactive controls

| Control | Action |
|---------|--------|
| **X ● / X ○** | Toggle X axis on or off |
| **Y ● / Y ○** | Toggle Y axis on or off |
| **Z ● / Z ○** | Toggle Z axis on or off |
| **Camera** | Switch between Perspective and Orthographic projection |
| **Export STEP** | Write the currently shown solid(s) to a STEP file on disk |
| Left drag | Orbit |
| Scroll | Zoom |
| Right drag | Pan |

---

## Exporting to STEP

Both `show()` and `interactive()` display an **Export STEP** button by default, right below the figure. Clicking it writes the model's solid object(s) to a STEP file on disk (in the notebook's working directory by default) and prints a confirmation — or an error — below the button.

```python
show(box)  # "Export STEP" button writes ./model.step on click
```

Customize the output path or unit with a dict, or turn the button off entirely with `False`:

```python
show(box, export=dict(filename="parts/bracket.step"))
show(box, export=dict(unit="MM"))  # STEP file declared/scaled in millimeters instead
show(box, export=False)
```

The exported file is written in **meters** by default (`unit="M"`) — pass `unit="MM"` for millimeters. Both CadQuery and build123d always model in millimeters internally, so converting to meters means both the numbers *and* the file's declared unit are changed together, consistently, so the model's true physical size round-trips correctly through any STEP-compliant importer.

> **Why this matters for Revit:** a STEP file is only valid if its declared unit and its raw coordinate values agree on the model's real-world size. Get that wrong — e.g. by relabeling a file's unit without rescaling its coordinates, or vice versa — and the file still *opens* in lenient viewers like Rhino (which mostly just renders whatever numbers it's given), but can silently balk or reject the import in a stricter, standards-conformant tool like Revit. If you're exporting build123d objects: build123d's own `export_step(unit=...)` has exactly this bug in current versions — passing anything but its default (millimeters) rescales the coordinates without updating the file's header, producing a file that's internally inconsistent by exactly 1000x. `export_step()` in this package works around it (pre-scaling the shape correctly and patching the header to match) so `unit="M"`/`unit="MM"` are both safe to use here regardless.

Only solid objects are exported — edges, wires, and plain points are skipped. If `objects` contains several solids from the same library (CadQuery or build123d), they're combined into a single compound in the STEP file. Mixing CadQuery and build123d solids in the same call raises an error, since they can't be combined into one compound.

For `interactive()`, pass `export` inside `show_kwargs`. Clicking the button always exports the object(s) built from the sliders' **current** values, not the values at the time the decorator ran:

```python
@interactive(width=(1, 10, 0.5, 5), show_kwargs=dict(export=dict(filename="box.step")))
def model(width):
    return cq.Workplane("XY").box(width, 3, 2)
```

The export button requires `ipywidgets` (see the `interactive` extra above); if it isn't installed, `show()` falls back to its normal behavior with no button — `interactive()` itself already requires `ipywidgets` regardless of export.

## Pixi environment example

```toml
[workspace]
channels = ["cadquery", "conda-forge"]
name = "my_project"
platforms = ["win-64", "osx-arm64", "osx-64", "linux-64"]

[dependencies]
python = "3.12.*"
cadquery = "*"
ipykernel = ">=6"

[pypi-dependencies]
cadquery-simpleviewer = "*"
```

---

## Repository

[https://github.com/255ribeiro/cadquery-simpleViewer](https://github.com/255ribeiro/cadquery-simpleViewer)

---

## License

MIT
