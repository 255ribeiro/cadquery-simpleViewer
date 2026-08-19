"""
build123d adapter — implements the shared adapter interface used by
_build_traces() in viewer.py. build123d is imported lazily inside each
function so that cadquery_simpleviewer never requires it to be installed
unless a build123d object is actually passed to show().

Naming differences from CadQuery, verified against build123d 0.11.1:
  - Vector.X / .Y / .Z are uppercase (CadQuery uses lowercase .x/.y/.z).
  - Edge.position_at(t) / Wire.edges() are snake_case (CadQuery uses
    positionAt(t) / Edges()).
  - Shape.tessellate(tolerance, angular_tolerance=0.1) is defined once on
    the shared Shape base, so Part/Sketch/Curve/Solid/Face all support it
    directly — there is no .val() indirection like CadQuery's
    Workplane.val().tessellate().
  - There is no Workplane/pending-stack concept: a 2D sketch built via
    BuildSketch() is already a Sketch (a Compound subclass) and flows
    through the same tessellate path as a solid.
"""


def is_point(obj):
    from build123d.geometry import Vector
    return isinstance(obj, Vector)


def is_edge(obj):
    from build123d.topology import Edge
    return isinstance(obj, Edge)


def is_wire(obj):
    from build123d.topology import Wire
    return isinstance(obj, Wire)


def is_pending_wire(obj):
    """build123d has no Workplane/pending-stack concept."""
    return False


def extract_wire(obj):
    raise NotImplementedError("build123d has no pending-wire concept")


def point_to_xyz(obj):
    """Extract (x, y, z) from a build123d Vector (uppercase X/Y/Z)."""
    return obj.X, obj.Y, obj.Z


def sample_edge(edge, samples):
    """Sample a build123d Edge into x, y, z coordinate lists using position_at(t)."""
    x = []
    y = []
    z = []

    for i in range(samples + 1):
        t = i / samples
        p = edge.position_at(t)
        x.append(p.X)
        y.append(p.Y)
        z.append(p.Z)

    return x, y, z


def sample_wire(wire, samples):
    """
    Sample a build123d Wire into x, y, z coordinate lists.

    A None separator is inserted between edges so Plotly draws them as
    disconnected segments rather than connecting the last point of one
    edge to the first point of the next.
    """
    x = []
    y = []
    z = []

    edges = list(wire.edges())

    for index in range(len(edges)):
        ex, ey, ez = sample_edge(edges[index], samples)
        x.extend(ex)
        y.extend(ey)
        z.extend(ez)

        if index < len(edges) - 1:
            x.append(None)
            y.append(None)
            z.append(None)

    return x, y, z


def tessellate_solid(obj, tolerance, angular_tolerance=0.1):
    """
    Tessellate a build123d Part/Sketch/Solid/Compound into Plotly-ready
    primitives. Returns (x, y, z, i, j, k), ready to hand straight to
    go.Mesh3d.
    """
    vertices, triangles = obj.tessellate(tolerance, angular_tolerance)

    x = [v.X for v in vertices]
    y = [v.Y for v in vertices]
    z = [v.Z for v in vertices]

    i = [t[0] for t in triangles]
    j = [t[1] for t in triangles]
    k = [t[2] for t in triangles]

    return x, y, z, i, j, k
