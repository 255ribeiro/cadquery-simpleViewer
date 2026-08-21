"""
STEP export helpers shared by show() and interactive(). Kept independent of
any UI toolkit so it can be unit-tested without ipywidgets/IPython involved.
"""

import os

from .adapters import get_adapter

_DEFAULT_EXPORT_FILENAME = "model.step"


def resolve_export_config(export):
    """
    Normalize the `export` parameter accepted by show()/interactive().

    None  -> default config (export enabled, default filename) — export is
             on by default.
    False -> None (export disabled)
    dict  -> defaults merged with caller overrides (currently only
             "filename" is recognized)
    """
    if export is False:
        return None
    config = {"filename": _DEFAULT_EXPORT_FILENAME}
    if isinstance(export, dict):
        config.update(export)
    return config


def _is_solid(obj, adapter):
    """True if obj is a solid (i.e. not a point/edge/wire/pending sketch)."""
    if adapter is None:
        return False
    if adapter.is_point(obj) or adapter.is_edge(obj) or adapter.is_wire(obj):
        return False
    if adapter.is_pending_wire(obj):
        return False
    return True


def export_step(objects, filepath):
    """
    Export the solid object(s) in `objects` (same shape show() accepts —
    a single object or a list, CadQuery and/or build123d) to a STEP file at
    `filepath`. Non-solid items (edges/wires/points) are skipped. Multiple
    solids from the same library are combined into a single compound.

    Raises ValueError if there are no solids to export, or if the solids
    span both CadQuery and build123d (mixed-kernel export isn't supported —
    export each library's objects separately).
    """
    if not isinstance(objects, list):
        objects = [objects]

    cq_solids = []
    b3d_solids = []

    for obj in objects:
        adapter = get_adapter(obj)
        if not _is_solid(obj, adapter):
            continue
        module_name = type(obj).__module__
        if module_name.startswith("cadquery"):
            cq_solids.append(obj)
        elif module_name.startswith("build123d"):
            b3d_solids.append(obj)

    if cq_solids and b3d_solids:
        raise ValueError(
            "Cannot export a mix of CadQuery and build123d solids to a "
            "single STEP file — export each library's objects separately."
        )
    if not cq_solids and not b3d_solids:
        raise ValueError(
            "No solid objects to export (edges/wires/points are skipped)."
        )

    directory = os.path.dirname(filepath)
    if directory:
        os.makedirs(directory, exist_ok=True)

    if cq_solids:
        import cadquery as cq
        shapes = [solid.val() for solid in cq_solids]
        cq.exporters.export(shapes, filepath, exportType="STEP")
    else:
        from build123d.topology import Compound
        from build123d.exporters3d import export_step as _b3d_export_step

        shape = Compound(b3d_solids) if len(b3d_solids) > 1 else b3d_solids[0]
        _b3d_export_step(shape, filepath)

    return filepath
