"""
Shared lazy import point for ipywidgets/IPython.display, used by both
viewer.py (optional — show() degrades gracefully without it) and
interactive.py (required — interactive() raises ImportError without it).
"""

import sys

try:
    import ipywidgets as widgets
    from IPython.display import display, clear_output, HTML, Javascript
except ImportError:
    widgets = None
    display = None
    clear_output = None
    HTML = None
    Javascript = None


def enable_colab_custom_widget_manager():
    """
    Google Colab renders ipywidgets through its own frontend, which only
    executes third-party JS content (like the <script> Plotly injects to
    draw a chart) inside an Output widget once the custom widget manager
    is enabled — without it, sliders render fine but the Output stays
    visually empty even though the figure was captured into it. This is a
    no-op outside Colab.
    """
    if "google.colab" not in sys.modules:
        return
    from google.colab import output as colab_output
    colab_output.enable_custom_widget_manager()
