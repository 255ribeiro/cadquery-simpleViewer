import pytest

b3d = pytest.importorskip("build123d")

from cadquery_simpleviewer.adapters import build123d_adapter as adapter


# ── fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def part():
    with b3d.BuildPart() as bp:
        b3d.Box(5, 3, 2)
    return bp.part


@pytest.fixture
def sketch():
    with b3d.BuildSketch() as bs:
        b3d.Circle(3.0)
    return bs.sketch


@pytest.fixture
def vec():
    return b3d.Vector(1.0, 2.0, 3.0)


@pytest.fixture
def straight_edge():
    return b3d.Edge.make_line((0, 0, 0), (5, 0, 0))


@pytest.fixture
def arc_edge():
    return b3d.Edge.make_circle(radius=3.0)


@pytest.fixture
def rect_wire():
    return b3d.Wire.make_rect(4.0, 2.0)


# ── is_point ────────────────────────────────────────────────────────────────

def test_is_point_vector(vec):
    assert adapter.is_point(vec) == True

def test_is_point_part(part):
    assert adapter.is_point(part) == False


# ── is_edge / is_wire ─────────────────────────────────────────────────────────

def test_is_edge_with_edge(straight_edge):
    assert adapter.is_edge(straight_edge) == True

def test_is_edge_with_wire(rect_wire):
    assert adapter.is_edge(rect_wire) == False

def test_is_wire_with_wire(rect_wire):
    assert adapter.is_wire(rect_wire) == True

def test_is_wire_with_edge(straight_edge):
    assert adapter.is_wire(straight_edge) == False

def test_is_pending_wire_always_false(part, straight_edge, rect_wire):
    assert adapter.is_pending_wire(part) == False
    assert adapter.is_pending_wire(straight_edge) == False
    assert adapter.is_pending_wire(rect_wire) == False


# ── point_to_xyz ──────────────────────────────────────────────────────────────

def test_point_to_xyz(vec):
    x, y, z = adapter.point_to_xyz(vec)
    assert (x, y, z) == (1.0, 2.0, 3.0)


# ── sample_edge ───────────────────────────────────────────────────────────────

def test_sample_edge_returns_correct_count(straight_edge):
    x, y, z = adapter.sample_edge(straight_edge, 10)
    assert len(x) == 11
    assert len(y) == 11
    assert len(z) == 11

def test_sample_edge_straight_endpoints(straight_edge):
    x, y, z = adapter.sample_edge(straight_edge, 5)
    assert abs(x[0] - 0.0) < 1e-6
    assert abs(x[-1] - 5.0) < 1e-6

def test_sample_edge_arc_stays_on_circle(arc_edge):
    x, y, z = adapter.sample_edge(arc_edge, 36)
    for i in range(len(x)):
        r = (x[i] ** 2 + y[i] ** 2) ** 0.5
        assert abs(r - 3.0) < 1e-4


# ── sample_wire ───────────────────────────────────────────────────────────────

def test_sample_wire_returns_lists(rect_wire):
    x, y, z = adapter.sample_wire(rect_wire, 10)
    assert isinstance(x, list)
    assert isinstance(y, list)
    assert isinstance(z, list)

def test_sample_wire_has_coordinates(rect_wire):
    x, y, z = adapter.sample_wire(rect_wire, 10)
    non_none = [v for v in x if v is not None]
    assert len(non_none) > 0


# ── tessellate_solid ────────────────────────────────────────────────────────

def test_tessellate_solid_part(part):
    x, y, z, i, j, k = adapter.tessellate_solid(part, 0.1)
    assert len(x) == len(y) == len(z)
    assert len(i) == len(j) == len(k)
    assert len(i) > 0

def test_tessellate_solid_sketch(sketch):
    x, y, z, i, j, k = adapter.tessellate_solid(sketch, 0.1)
    assert len(x) == len(y) == len(z)
    assert len(i) > 0
