"""
STEP export helpers shared by show() and interactive(). Kept independent of
any UI toolkit so it can be unit-tested without ipywidgets/IPython involved.
"""

import os

from .adapters import get_adapter

_DEFAULT_EXPORT_FILENAME = "model.step"
_DEFAULT_EXPORT_UNIT = "M"

# millimeters per unit — both CadQuery and build123d always represent
# geometry internally in millimeters, so every conversion is relative to MM.
_MM_PER_UNIT = {"MM": 1.0, "M": 1000.0}

# The exact STEP header entity text for each supported unit's SI_UNIT
# declaration, used to patch build123d's exported header (see _b3d_export
# for why this is necessary).
_STEP_SI_UNIT_TEXT = {
    "MM": "SI_UNIT(.MILLI.,.METRE.)",
    "M": "SI_UNIT($,.METRE.)",
}


def resolve_export_config(export):
    """
    Normalize the `export` parameter accepted by show()/interactive().

    None  -> default config (export enabled, default filename, meters) —
             export is on by default.
    False -> None (export disabled)
    dict  -> defaults merged with caller overrides ("filename" and "unit"
             are recognized; "unit" must be "MM" or "M")
    """
    if export is False:
        return None
    config = {"filename": _DEFAULT_EXPORT_FILENAME, "unit": _DEFAULT_EXPORT_UNIT}
    if isinstance(export, dict):
        config.update(export)
    _validate_unit(config["unit"])
    return config


def _validate_unit(unit):
    if unit not in _MM_PER_UNIT:
        raise ValueError(
            f"Unsupported export unit {unit!r} — supported units: "
            f"{sorted(_MM_PER_UNIT)}"
        )


def _is_solid(obj, adapter):
    """True if obj is a solid (i.e. not a point/edge/wire/pending sketch)."""
    if adapter is None:
        return False
    if adapter.is_point(obj) or adapter.is_edge(obj) or adapter.is_wire(obj):
        return False
    if adapter.is_pending_wire(obj):
        return False
    return True


def _export_cq(cq_solids, filepath, unit):
    """
    Export CadQuery solids to STEP in `unit`.

    CadQuery's Workplane geometry is always expressed internally in
    millimeters, so `unit="MM"` here always describes the *true* unit of
    the raw geometry values — it must never change. `outputUnit` is what
    actually controls the unit the STEP file is written in: OCCT converts
    the coordinate values from `unit` to `outputUnit` on write, and writes
    the matching SI_UNIT declaration in the header, so the file stays
    internally consistent (verified: a 10mm CadQuery box exported with
    outputUnit="M" round-trips back to a 10mm box on import, not 10m).
    """
    import cadquery as cq

    shapes = [solid.val() for solid in cq_solids]
    cq.exporters.export(shapes, filepath, exportType="STEP", unit="MM", outputUnit=unit)


def _export_b3d(b3d_solids, filepath, unit):
    """
    Export build123d solids to STEP in `unit`.

    build123d's export_step(unit=...) is unsafe for anything but the
    default Unit.MM: passing e.g. Unit.M silently rescales the exported
    coordinate values by 1000x, but always writes the header's SI_UNIT
    declaration as millimeter regardless of `unit` (confirmed by
    inspecting the raw STEP output — see exporter tests). Using it
    directly produces a file whose declared unit and actual coordinate
    magnitude disagree — lenient viewers like Rhino render it anyway
    (at 1000x the true size), while stricter importers like Revit can
    reject it outright.

    The workaround: pre-scale the shape ourselves with Shape.scale() to
    the target unit, export with build123d's default (Unit.MM, which
    applies no extra scaling — a verified no-op), then patch the
    resulting file's header text to declare the unit we actually used.
    """
    from build123d.topology import Compound
    from build123d.exporters3d import export_step as _b3d_export_step

    shape = Compound(b3d_solids) if len(b3d_solids) > 1 else b3d_solids[0]

    factor = _MM_PER_UNIT["MM"] / _MM_PER_UNIT[unit]
    if factor != 1.0:
        shape = shape.scale(factor)

    _b3d_export_step(shape, filepath)

    if unit != "MM":
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        content = content.replace(_STEP_SI_UNIT_TEXT["MM"], _STEP_SI_UNIT_TEXT[unit])
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)


def export_step(objects, filepath, unit=_DEFAULT_EXPORT_UNIT):
    """
    Export the solid object(s) in `objects` (same shape show() accepts —
    a single object or a list, CadQuery and/or build123d) to a STEP file at
    `filepath`, declared in `unit` ("M" or "MM", default "M"). Non-solid
    items (edges/wires/points) are skipped. Multiple solids from the same
    library are combined into a single compound.

    Raises ValueError if there are no solids to export, if the solids span
    both CadQuery and build123d (mixed-kernel export isn't supported —
    export each library's objects separately), or if `unit` isn't
    recognized.
    """
    _validate_unit(unit)

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
        _export_cq(cq_solids, filepath, unit)
    else:
        _export_b3d(b3d_solids, filepath, unit)

    return filepath
