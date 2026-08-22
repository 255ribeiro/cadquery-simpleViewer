"""
Shared "pick a format, click Export" widget used by show() and
interactive(). A single dropdown lists whichever export formats are
currently enabled; one Export button dispatches to whichever format is
selected. Adding a new export format elsewhere only means appending one
more (label, export_callable) entry to the `formats` list passed in here —
no new widget-wiring code.
"""

from ._optional_widgets import widgets, display, clear_output


def build_export_widget(formats):
    """
    Build the shared export control: a Dropdown of format labels, an
    "Export" button, and a status Output.

    formats: list of (label, export_fn) pairs, already filtered to only
             the enabled/available formats. export_fn takes no arguments
             (callers close over objects/filename/unit/etc. via a lambda)
             and returns the written filepath, raising on error. Order
             determines dropdown order and the initial selection — the
             first entry is selected by default, so callers should put
             "STEP" first to keep it the default format.

    Returns an ipywidgets HBox (Dropdown + Export button + status Output),
    right-aligned via layout, or None if `formats` is empty — callers
    should skip displaying anything in that case.
    """
    if not formats:
        return None

    by_label = dict(formats)
    dropdown = widgets.Dropdown(options=[label for label, _ in formats], description="Export:")
    button = widgets.Button(description="Export", icon="download")
    status = widgets.Output()

    def _on_click(_btn):
        with status:
            clear_output(wait=True)
            try:
                path = by_label[dropdown.value]()
                print(f"Exported to {path}")
            except Exception as exc:
                print(f"Export failed: {exc}")

    button.on_click(_on_click)

    return widgets.HBox(
        [dropdown, button, status],
        layout=widgets.Layout(justify_content="flex-end"),
    )
