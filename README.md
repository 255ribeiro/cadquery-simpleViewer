# CadQuery Simple Viewer


## Functions

### `show(objects, names=None, colors=None, opacity=1.0, tessellation_tolerance=0.01)`

Display one or more CadQuery objects with visible axes, grids, and tick labels. Best for inspecting part dimensions and position relationships.

Parameters:
- `objects`: A single CadQuery object or a list of CadQuery objects.
- `names`: Optional list of legend labels.
- `colors`: Optional list of face colors.
- `opacity`: Transparency value (1.0 = fully opaque).
- `tessellation_tolerance`: Mesh precision (smaller = finer mesh).

### `show_arch(objects, names=None, colors=None, opacity=1.0, z=None, plane_color="whitesmoke", plane_size=50, plane_opacity=0.8, tessellation_tolerance=0.01)`

Display one or more CadQuery objects in an architectural style with axis labels/ticks/grid hidden. Optionally adds a base plane at elevation `z`.

Parameters:
- `objects`: A single CadQuery object or a list of CadQuery objects.
- `names`: Optional list of legend labels.
- `colors`: Optional list of face colors.
- `opacity`: Transparency value (1.0 = fully opaque).
- `z`: Optional height for a base plane. If `None`, no plane is displayed.
- `plane_color`: Color of the optional base plane.
- `plane_size`: Half side length of the base plane.
- `plane_opacity`: Opacity of the optional base plane.
- `tessellation_tolerance`: Mesh precision (smaller = finer mesh).

## Quick Start

```python
from cadquery import Workplane
from cadquery_simpleviewer.viewer import show, show_arch

box = Workplane("XY").box(10, 20, 5)
show(box)
show_arch(box, z=0)
```



