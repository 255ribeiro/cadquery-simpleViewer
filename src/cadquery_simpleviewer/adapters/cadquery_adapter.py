"""
CadQuery adapter — implements the shared adapter interface used by
_build_traces() in viewer.py. cadquery is imported lazily inside each
function so that cadquery_simpleviewer never requires it to be installed
unless a CadQuery object is actually passed to show().
"""


def is_point(obj):
    import cadquery as cq
    return isinstance(obj, cq.occ_impl.geom.Vector)


def is_edge(obj):
    import cadquery as cq
    return isinstance(obj, cq.occ_impl.shapes.Edge)


def is_wire(obj):
    import cadquery as cq
    return isinstance(obj, cq.occ_impl.shapes.Wire)


def is_pending_wire(obj):
    """
    True if obj is a Workplane whose stack holds a Wire or Edge
    (i.e. a 2D sketch like .rect(), .circle(), .polygon() that has not
    been extruded yet). These objects cannot be tessellated as solids
    and must be extracted before display.
    """
    import cadquery as cq
    if not isinstance(obj, cq.Workplane):
        return False
    try:
        val = obj.val()
        return isinstance(val, (cq.occ_impl.shapes.Wire, cq.occ_impl.shapes.Edge))
    except Exception:
        return False


def extract_wire(obj):
    """Extract a cq.Wire or cq.Edge from a Workplane with a pending sketch."""
    return obj.wires().val()


def point_to_xyz(obj):
    """Extract (x, y, z) from a cq.Vector."""
    return obj.x, obj.y, obj.z


def sample_edge(edge, samples):
    """
    Sample a cq.Edge into x, y, z coordinate lists using positionAt(t).

    positionAt(t) follows the actual curve geometry for any edge type:
    straight lines, arcs, ellipses, splines, helices, B-splines, etc.
    """
    x = []
    y = []
    z = []

    for i in range(samples + 1):
        t = i / samples
        p = edge.positionAt(t)
        x.append(p.x)
        y.append(p.y)
        z.append(p.z)

    return x, y, z


def sample_wire(wire, samples):
    """
    Sample a cq.Wire into x, y, z coordinate lists.

    A wire is a chain of edges. Each edge is sampled individually and the
    results are concatenated. A None separator is inserted between edges
    so Plotly draws them as disconnected segments rather than connecting
    the last point of one edge to the first point of the next.
    """
    x = []
    y = []
    z = []

    edges = wire.Edges()

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


def tessellate_solid(obj, tolerance):
    """
    Tessellate a CadQuery Workplane solid into Plotly-ready primitives.

    Returns (x, y, z, i, j, k) — vertex coordinate lists and triangle
    index lists, ready to hand straight to go.Mesh3d.
    """
    vertices, triangles = obj.val().tessellate(tolerance)

    x = [v.x for v in vertices]
    y = [v.y for v in vertices]
    z = [v.z for v in vertices]

    i = [t[0] for t in triangles]
    j = [t[1] for t in triangles]
    k = [t[2] for t in triangles]

    return x, y, z, i, j, k
