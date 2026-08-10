from . import cadquery_adapter, build123d_adapter


def get_adapter(obj):
    """
    Return the adapter module that owns obj's type, or None if obj is not
    a recognized CadQuery/build123d object (e.g. a plain [x, y, z] point).

    Dispatch is done by inspecting type(obj).__module__ rather than
    isinstance(), so neither cadquery nor build123d has to be imported
    just to check whether an object belongs to it.
    """
    module_name = type(obj).__module__
    if module_name.startswith("cadquery"):
        return cadquery_adapter
    if module_name.startswith("build123d"):
        return build123d_adapter
    return None
