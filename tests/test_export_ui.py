import pytest

widgets = pytest.importorskip("ipywidgets")

from cadquery_simpleviewer._export_ui import build_export_widget


def test_build_export_widget_empty_formats_returns_none():
    assert build_export_widget([]) is None

def test_build_export_widget_single_format_option():
    w = build_export_widget([("STEP", lambda: "model.step")])
    dropdown, button, status = w.children
    assert dropdown.options == ("STEP",)
    assert dropdown.value == "STEP"

def test_build_export_widget_defaults_to_first_entry():
    w = build_export_widget([("STEP", lambda: "a"), ("IFC Proxy", lambda: "b")])
    dropdown, button, status = w.children
    assert dropdown.options == ("STEP", "IFC Proxy")
    assert dropdown.value == "STEP"

def test_build_export_widget_click_calls_selected_format():
    calls = []

    def export_step():
        calls.append("step")
        return "model.step"

    def export_ifc():
        calls.append("ifc")
        return "model.ifc"

    w = build_export_widget([("STEP", export_step), ("IFC Proxy", export_ifc)])
    dropdown, button, status = w.children

    button.click()
    assert calls == ["step"]

    dropdown.value = "IFC Proxy"
    button.click()
    assert calls == ["step", "ifc"]

def test_build_export_widget_click_reports_success(capsys):
    # Output()'s context manager only routes prints into .outputs inside a
    # real IPython kernel — outside one (e.g. under pytest) it falls back
    # to plain stdout, so success/failure text is asserted via capsys.
    w = build_export_widget([("STEP", lambda: "model.step")])
    dropdown, button, status = w.children

    button.click()

    assert "Exported to model.step" in capsys.readouterr().out

def test_build_export_widget_click_reports_failure(capsys):
    def failing():
        raise RuntimeError("boom")

    w = build_export_widget([("STEP", failing)])
    dropdown, button, status = w.children

    button.click()

    assert "Export failed: boom" in capsys.readouterr().out
