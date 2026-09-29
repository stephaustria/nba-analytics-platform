import numpy as np
import plotly.graph_objects as go


def _arc(r, t0, t1, cx=0.0, cy=0.0, n=80):
    t = np.linspace(t0, t1, n)
    return cx + r * np.cos(t), cy + r * np.sin(t)


def court_traces() -> list:
    """Half court in NBA shot-chart units (tenths of feet, rim at the origin)."""
    traces = []

    def add(x, y, dash=None):
        traces.append(go.Scatter(x=list(x), y=list(y), mode="lines", hoverinfo="skip",
                                 showlegend=False, line=dict(color="#555", width=2, dash=dash)))

    add([-250, 250, 250, -250, -250], [-47.5, -47.5, 422.5, 422.5, -47.5])   # boundary
    add([-80, -80, 80, 80], [-47.5, 142.5, 142.5, -47.5])                     # outer paint
    add([-60, -60, 60, 60], [-47.5, 142.5, 142.5, -47.5])                     # inner paint
    add(*_arc(60, 0, np.pi, cy=142.5))                                         # free throw circle
    add(*_arc(60, np.pi, 2 * np.pi, cy=142.5), dash="dot")
    add(*_arc(40, 0, np.pi))                                                   # restricted area
    add(*_arc(7.5, 0, 2 * np.pi))                                              # rim
    add([-30, 30], [-7.5, -7.5])                                               # backboard
    t0 = np.arccos(220 / 237.5)                                                # three-point line
    x, y = _arc(237.5, t0, np.pi - t0)
    add(x, y)
    add([-220, -220], [-47.5, y[0]])
    add([220, 220], [-47.5, y[-1]])
    return traces