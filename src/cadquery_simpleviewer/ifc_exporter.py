"""
IFC export helpers shared by show() and interactive(). Kept independent of
any UI toolkit so it can be unit-tested without ipywidgets/IPython involved.

ifcopenshell is imported lazily inside each function that needs it (see
_require_ifcopenshell()), so cadquery-simpleviewer never requires it unless
IFC export is actually used.
"""

import os

from .adapters import get_adapter
from .exporter import _is_solid, _validate_unit

_DEFAULT_IFC_EXPORT_FILENAME = "model.ifc"
_DEFAULT_IFC_EXPORT_UNIT = "M"
_DEFAULT_IFC_SCHEMA = "IFC4"
_DEFAULT_TESSELLATION_TOLERANCE = 0.01
_DEFAULT_ANGULAR_TOLERANCE = 0.1


def resolve_ifc_export_config(export_ifc):
    """
    Normalize the `export_ifc` parameter accepted by show()/interactive().

    Same None/False/dict contract as resolve_export_config() in
    exporter.py, with an IFC-specific default filename ("model.ifc").

    None  -> default config (export enabled, default filename, meters)
    False -> None (export disabled)
    dict  -> defaults merged with caller overrides ("filename" and "unit"
             are recognized; "unit" must be "MM" or "M")
    """
    if export_ifc is False:
        return None
    config = {"filename": _DEFAULT_IFC_EXPORT_FILENAME, "unit": _DEFAULT_IFC_EXPORT_UNIT}
    if isinstance(export_ifc, dict):
        config.update(export_ifc)
    _validate_unit(config["unit"])
    return config


def resolve_ifc_config(ifc_config):
    """
    Normalize the `ifc_config` parameter accepted by show()/interactive().

    Unlike `export_ifc` (which toggles/configures the export itself),
    `ifc_config` carries IFC-specific settings that apply whenever an IFC
    file is written, regardless of how export was triggered — currently
    just `schema`.

    None -> default config ({"schema": "IFC4"})
    dict -> defaults merged with caller overrides ("schema" is recognized,
            any identifier the installed ifcopenshell accepts, e.g.
            "IFC4", "IFC2X3", "IFC4X3")
    """
    config = {"schema": _DEFAULT_IFC_SCHEMA}
    if isinstance(ifc_config, dict):
        config.update(ifc_config)
    return config


def _ifcopenshell_available():
    """True if ifcopenshell is importable — used to decide whether to
    offer IFC export in the UI at all, without raising."""
    try:
        import ifcopenshell  # noqa: F401
    except ImportError:
        return False
    return True


def _require_ifcopenshell():
    try:
        import ifcopenshell
        import ifcopenshell.api.root
        import ifcopenshell.api.unit
        import ifcopenshell.api.context
        import ifcopenshell.api.aggregate
        import ifcopenshell.api.spatial
        import ifcopenshell.api.geometry
        import ifcopenshell.api.owner
    except ImportError as exc:
        raise ImportError(
            "IFC export requires ifcopenshell. Install with "
            "`pip install cadquery-simpleviewer[ifc]` "
            "(or `pip install ifcopenshell` if not already present)."
        ) from exc
    return ifcopenshell


def _build_minimal_hierarchy(ifcopenshell, model, unit):
    """
    Build the minimum spatial scaffolding required for a structurally
    valid IFC file — IfcProject -> IfcSite -> IfcBuilding ->
    IfcBuildingStorey — plus a length unit and a "Body"/MODEL_VIEW
    geometric representation context. Returns (storey, body_context).

    ifcopenshell.api.root.create_entity() auto-generates GlobalId and
    OwnerHistory internally for IFC4+, but IFC2X3 additionally requires an
    IfcPersonAndOrganization/IfcApplication to already exist before the
    first rooted entity is created — create_owner_history() raises
    otherwise (see ifcopenshell.api.owner.settings.get_user/
    get_application). Setting this up unconditionally, with the library's
    own placeholder defaults, keeps export_ifc_proxy() schema-agnostic
    without special-casing IFC2X3 here.
    """
    person = ifcopenshell.api.owner.add_person(model)
    organisation = ifcopenshell.api.owner.add_organisation(model)
    ifcopenshell.api.owner.add_person_and_organisation(
        model, person=person, organisation=organisation
    )
    ifcopenshell.api.owner.add_application(model, application_developer=organisation)

    project = ifcopenshell.api.root.create_entity(
        model, ifc_class="IfcProject", name="cadquery-simpleviewer export"
    )
    site = ifcopenshell.api.root.create_entity(model, ifc_class="IfcSite", name="Site")
    building = ifcopenshell.api.root.create_entity(model, ifc_class="IfcBuilding", name="Building")
    storey = ifcopenshell.api.root.create_entity(
        model, ifc_class="IfcBuildingStorey", name="Storey"
    )

    ifcopenshell.api.aggregate.assign_object(model, relating_object=project, products=[site])
    ifcopenshell.api.aggregate.assign_object(model, relating_object=site, products=[building])
    ifcopenshell.api.aggregate.assign_object(model, relating_object=building, products=[storey])

    # assign_unit() called with no args silently fabricates millimeters
    # regardless of `unit`, so the length unit is always built explicitly.
    length_unit = ifcopenshell.api.unit.add_si_unit(
        model, unit_type="LENGTHUNIT", prefix=None if unit == "M" else "MILLI"
    )
    ifcopenshell.api.unit.assign_unit(model, units=[length_unit])

    model3d = ifcopenshell.api.context.add_context(model, context_type="Model")
    body = ifcopenshell.api.context.add_context(
        model,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=model3d,
    )

    return storey, body


def _add_proxy(ifcopenshell, model, body_context, storey, name, verts, faces):
    """
    Create one IfcBuildingElementProxy carrying a tessellated mesh
    representation (verts/faces from tessellate_solid()), and contain it
    in `storey`. No property sets, material, or type object are attached —
    geometry and name only.
    """
    proxy = ifcopenshell.api.root.create_entity(
        model, ifc_class="IfcBuildingElementProxy", name=name
    )
    ifcopenshell.api.geometry.edit_object_placement(model, product=proxy)

    # vertices/faces are each a list of lists — one sub-list per
    # representation item; a single mesh per proxy here.
    representation = ifcopenshell.api.geometry.add_mesh_representation(
        model, context=body_context, vertices=[verts], faces=[faces]
    )
    ifcopenshell.api.geometry.assign_representation(
        model, product=proxy, representation=representation
    )
    ifcopenshell.api.spatial.assign_container(
        model, products=[proxy], relating_structure=storey
    )


def export_ifc_proxy(
    objects,
    filepath,
    names=None,
    unit=_DEFAULT_IFC_EXPORT_UNIT,
    schema=_DEFAULT_IFC_SCHEMA,
    tessellation_tolerance=_DEFAULT_TESSELLATION_TOLERANCE,
    angular_tolerance=_DEFAULT_ANGULAR_TOLERANCE,
):
    """
    Export the solid object(s) in `objects` (same shape show() accepts —
    a single object or a list, CadQuery and/or build123d) to an IFC file
    at `filepath`, with each solid written as its own independent
    IfcBuildingElementProxy carrying only geometry and a name — no
    property sets, materials, or type objects.

    Unlike export_step(), solids are NOT combined into one compound: each
    object gets its own proxy, stays independently selectable/schedulable
    in the BIM program, and CadQuery and build123d solids CAN be freely
    mixed in a single call (there's no cross-kernel compound to build).

    Geometry is written as a tessellated triangular mesh — via each
    adapter's tessellate_solid(), the same function already used for the
    3D viewer, at the given `tessellation_tolerance`/`angular_tolerance` —
    not an exact BREP solid, since ifcopenshell's Python API has no
    supported path to write arbitrary OCCT BRep shapes as exact IFC
    solids.

    The file gets the minimum spatial-hierarchy scaffolding required for a
    structurally valid file in the given `schema` (IfcProject -> IfcSite ->
    IfcBuilding -> IfcBuildingStorey, with every proxy contained in that
    single storey) and nothing else.

    `names` follows the same convention as show()'s `names` — a list of
    per-object labels, defaulting to "Object 1", "Object 2", ... — used as
    each proxy's IFC `Name` attribute.

    `unit` ("M" or "MM", default "M") declares the file's IfcSIUnit prefix
    only — the coordinate numbers are written exactly as tessellated, with
    no rescaling, the same "modeled value taken as-is" convention as
    export_step().

    `schema` (default "IFC4") selects the IFC schema version written —
    any identifier the installed ifcopenshell accepts (e.g. "IFC4",
    "IFC2X3", "IFC4X3").

    Non-solid items (edges/wires/points) are skipped, same as
    export_step().

    Raises ValueError if there are no solids to export or `unit` isn't
    recognized. Raises ImportError if ifcopenshell isn't installed. An
    unrecognized `schema` raises whatever error the installed ifcopenshell
    itself raises for an unknown schema identifier.
    """
    ifcopenshell = _require_ifcopenshell()
    _validate_unit(unit)

    if not isinstance(objects, list):
        objects = [objects]

    solids = []
    for index, obj in enumerate(objects):
        adapter = get_adapter(obj)
        if not _is_solid(obj, adapter):
            continue
        name = names[index] if names else f"Object {index + 1}"
        solids.append((obj, adapter, name))

    if not solids:
        raise ValueError(
            "No solid objects to export (edges/wires/points are skipped)."
        )

    directory = os.path.dirname(filepath)
    if directory:
        os.makedirs(directory, exist_ok=True)

    model = ifcopenshell.file(schema=schema)
    storey, body_context = _build_minimal_hierarchy(ifcopenshell, model, unit)

    for obj, adapter, name in solids:
        x, y, z, ii, jj, kk = adapter.tessellate_solid(
            obj, tessellation_tolerance, angular_tolerance
        )
        verts = list(zip(x, y, z))
        faces = list(zip(ii, jj, kk))
        _add_proxy(ifcopenshell, model, body_context, storey, name, verts, faces)

    model.write(filepath)

    return filepath
