import pytest

cq = pytest.importorskip("cadquery")
b3d = pytest.importorskip("build123d")

from cadquery_simpleviewer.adapters import (
    get_adapter,
    cadquery_adapter,
    build123d_adapter,
)


def test_get_adapter_cadquery():
    assert get_adapter(cq.Vector(1, 2, 3)) is cadquery_adapter

def test_get_adapter_build123d():
    assert get_adapter(b3d.Vector(1, 2, 3)) is build123d_adapter

def test_get_adapter_plain_list():
    assert get_adapter([1, 2, 3]) is None

def test_get_adapter_unrecognized():
    assert get_adapter(object()) is None
