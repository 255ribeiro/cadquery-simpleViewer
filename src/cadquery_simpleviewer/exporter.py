"""
STEP export helpers shared by show() and interactive(). Kept independent of
any UI toolkit so it can be unit-tested without ipywidgets/IPython involved.
"""

import os

from .adapters import get_adapter

_DEFAULT_EXPORT_FILENAME = "model.step"
_DEFAULT_EXPORT_UNIT = "M"

# Neither CadQuery nor build123d's geometry kernel enforces a unit — a
# modeled value of 10 is just the number 10 until a unit is declared on
# export. These are the units export_step() can declare.
_SUPPORTED_UNITS = {"MM", "M"}

# The exact STEP header entity text for each supported unit's SI_UNIT
# declaration, used to patch build123d's exported header (see _export_b3d
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
    if unit not in _SUPPORTED_UNITS:
        raise ValueError(
            f"Unsupported export unit {unit!r} — supported units: "
            f"{sorted(_SUPPORTED_UNITS)}"
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
    Export CadQuery solids to STEP, declaring the file's unit as `unit`
    with no rescaling — the raw geometry values are taken exactly as
    modeled and just labeled `unit` (e.g. a box built with .box(10, 10, 2)
    is written as literally 10 of whatever `unit` is, not converted from
    an assumed "true" unit). Passing only `unit` (no `outputUnit`) makes
    OCCT interpret and declare the values in the same unit, so nothing is
    rescaled — verified: the exported CARTESIAN_POINT values are identical
    regardless of `unit`, only the header's SI_UNIT declaration changes.
    """
    import cadquery as cq

    shapes = [solid.val() for solid in cq_solids]
    cq.exporters.export(shapes, filepath, exportType="STEP", unit=unit)


def _export_b3d(b3d_solids, filepath, unit):
    """
    Export build123d solids to STEP, declaring the file's unit as `unit`
    with no rescaling — same "values taken as-is" contract as _export_cq().

    build123d's own export_step(unit=...) can't be used for this: passing
    anything but its default Unit.MM silently rescales the exported
    coordinate values by the unit ratio (e.g. x1000 for Unit.M) while
    *always* writing the header's SI_UNIT declaration as millimeter
    regardless of `unit` — confirmed by inspecting the raw STEP output
    (see exporter tests). That mismatch between declared unit and actual
    coordinate magnitude is exactly what produces a file that opens at the
    wrong scale (or gets rejected by strict importers like Revit) — the
    numbers get scaled but the label lies about it.

    The workaround: always export with build123d's default (Unit.MM,
    verified to pass the coordinate values through unchanged — no `unit=`
    kwarg passed here at all), then patch the resulting file's header text
    directly to declare `unit`, without touching the coordinates.
    """
    from build123d.topology import Compound
    from build123d.exporters3d import export_step as _b3d_export_step

    shape = Compound(b3d_solids) if len(b3d_solids) > 1 else b3d_solids[0]

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
    `filepath`, declared in `unit` ("M" or "MM", default "M"). The raw
    geometry values are written exactly as modeled — no rescaling happens.
    Neither CadQuery nor build123d's geometry kernel enforces a unit, so
    `unit` just labels the numbers already on the model: if your modeling
    convention treats a dimension of 10 as 10 meters, `unit="M"` (the
    default) declares the file that way with no conversion; a workflow
    that models in millimeters should pass `unit="MM"` instead. Non-solid
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
