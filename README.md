# cadquery-simpleViewer

An interactive 3D viewer for [CadQuery](https://github.com/CadQuery/cadquery) models, built on [Plotly](https://plotly.com/python/). Renders geometry directly inside Jupyter notebooks and Google Colab cells — no external software, no extensions, no server required.

---

## Features

- Interactive orbit, zoom and pan inside the notebook cell
- Supports CadQuery solids, `cq.Vector` points, and `[x, y, z]` lists — mixed in the same call
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

> **Note**: `cadquery-simpleviewer` declares `plotly` as a dependency but intentionally does not pin `cadquery` itself — users typically manage their CadQuery installation separately (pip, conda, or the `cadquery` conda channel via pixi). See the [CadQuery installation guide](https://cadquery.readthedocs.io/en/latest/installation.html) for details.

---

## Quick Start

```python
import cadquery as cq
from cadquery_simpleviewer import show

box = cq.Workplane("XY").box(5, 3, 2)
show(box)
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

## Displaying Points

`show()` accepts `cq.Vector` objects and `[x, y, z]` lists alongside CadQuery solids. Points are rendered as `Scatter3d` markers — no tessellation involved.

### Single point

```python
show(cq.Vector(2.5, 0, 1))
```

### List notation

```python
show([2.5, 0, 1])
```

### Mixed solids and points

```python
box    = cq.Workplane("XY").box(5, 3, 2)
corner = cq.Vector(2.5, 1.5, 1.0)

show(
    [box, corner],
    names=["Box", "Corner"]
)
```

### Multiple points from edge division

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

### Customising point appearance

Pass a `points_display` dict to control the marker style. All keys are optional — unspecified keys fall back to the defaults.

```python
show(
    [box] + points,
    points_display=dict(
        size=8,
        color="blue",
        symbol="diamond",
        opacity=0.9
    )
)
```

| `points_display` key | Default | Options |
|----------------------|---------|---------|
| `size` | `5` | Any integer (pixels) |
| `color` | `"red"` | Any CSS color name or hex — see [Plotly CSS colors](https://plotly.com/python/css-colors/) |
| `symbol` | `"circle"` | `"circle"`, `"circle-open"`, `"square"`, `"diamond"`, `"cross"`, `"x"` |
| `opacity` | `1.0` | `0.0` – `1.0` |

> Note: `points_display` applies the same style to all point objects in the call. To display points with different colors, make separate `show()` calls or use `go.Scatter3d` directly.

---

## Google Colab

Install at the top of the notebook, then use normally:

```python
import sys
IN_COLAB = "google.colab" in sys.modules
if IN_COLAB:
    !pip install cadquery cadquery-simpleviewer

import cadquery as cq
from cadquery_simpleviewer import show

box = cq.Workplane("XY").box(5, 3, 2)
show(box)
```

The viewer renders inline as an interactive Plotly figure. No extensions or widget managers are needed.

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
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `objects` | object or list | — | CadQuery `Workplane`, `cq.Vector`, `[x, y, z]` list, or any mix of these |
| `names` | list of str | `None` | Legend label for each object. Defaults to `"Object 1"`, `"Object 2"`, … |
| `colors` | list of str | `None` | Face color for each mesh object. Accepts CSS color names and hex values. See [Plotly CSS colors](https://plotly.com/python/css-colors/). Defaults to a built-in palette |
| `opacity` | float | `1.0` | Surface opacity for mesh objects. `1.0` = fully opaque, `0.0` = fully transparent |
| `visible_axes` | str or None | `"xyz"` | Initial axes visibility. `None` hides all axes. Valid values: `None`, `"x"`, `"y"`, `"z"`, `"xy"`, `"xz"`, `"yz"`, `"xyz"` |
| `z` | float or None | `None` | Elevation of the ground plane. `None` = no plane drawn |
| `plane_color` | str | `"whitesmoke"` | Color of the ground plane |
| `plane_size` | float | `50` | Half-side length of the ground plane quad. The plane extends `±plane_size` from the scene center in X and Y |
| `plane_opacity` | float | `0.8` | Opacity of the ground plane |
| `tessellation_tolerance` | float | `0.01` | Mesh precision for BREP→triangle conversion. Smaller = finer mesh, slower |
| `padding` | float | `0.15` | Fraction of the bounding box span added as margin on each axis |
| `points_display` | dict or None | `None` | Marker style for point objects. See keys in the table above. `None` uses defaults |

### Interactive controls

Once rendered, the figure provides:

| Control | Action |
|---------|--------|
| **X ● / X ○** | Toggle X axis on or off |
| **Y ● / Y ○** | Toggle Y axis on or off |
| **Z ● / Z ○** | Toggle Z axis on or off |
| **Camera** | Switch between Perspective and Orthographic projection |
| Left drag | Orbit |
| Scroll | Zoom |
| Right drag | Pan |

---

## Pixi environment example

A minimal `pixi.toml` for a CadQuery project using this viewer:

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
