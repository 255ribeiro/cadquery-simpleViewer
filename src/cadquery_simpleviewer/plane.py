import plotly.graph_objects as go


def _base_plane(size: float, color: str, opacity: float, z: float):
    """Create a flat horizontal mesh at a given z level to simulate a ground plane."""
    x = [-size,  size,  size, -size]
    y = [-size, -size,  size,  size]
    z_vals = [z, z, z, z]

    return go.Mesh3d(
        x=x, y=y, z=z_vals,
        i=[0, 0],
        j=[1, 2],
        k=[2, 3],
        color=color,
        opacity=opacity,
        showlegend=False,
        hoverinfo="skip"
    )