from __future__ import annotations
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np
from IPython.display import clear_output, display

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    HAS_PLOTLY = True
except Exception:
    HAS_PLOTLY = False


@dataclass
class Dashboard:
    hall: any
    controller: any
    max_history: int = 200
    times: List[float] = field(init=False, default_factory=list)
    pue_values: List[float] = field(init=False, default_factory=list)
    power_values: List[float] = field(init=False, default_factory=list)

    def update(self, telemetry: Dict):
        # 1. Update Data
        self.times.append(telemetry["time"])
        self.pue_values.append(telemetry["pue"])
        # Simple power calculation: IT Power + (PUE-1)*IT Power
        it_power = sum(r["power_draw"] for r in telemetry["racks"])
        total_power = it_power * telemetry["pue"]
        self.power_values.append(total_power)

        if len(self.times) > self.max_history:
            self.times.pop(0)
            self.pue_values.pop(0)
            self.power_values.pop(0)

        fig = make_subplots(
            rows=2, cols=2,
            specs=[[{"type": "heatmap", "rowspan": 2}, {"type": "scatter"}],
                   [None, {"type": "scatter"}]],
            subplot_titles=("Thermal Gradient (Digital Twin)", "PUE Efficiency", "Power Usage (W)")
        )

        # Heatmap
        fig.add_trace(go.Heatmap(
            z=self.hall.grid, 
            colorscale="Hot", 
            zmin=20, zmax=60, # Lock limits so colors don't flicker
            colorbar=dict(title="°C")
        ), row=1, col=1)

        # PUE Plot
        fig.add_trace(go.Scatter(x=self.times, y=self.pue_values, name="PUE", line=dict(color='blue')), row=1, col=2)
        
        # Power Plot
        fig.add_trace(go.Scatter(x=self.times, y=self.power_values, name="Watts", line=dict(color='green')), row=2, col=2)

        fig.update_layout(height=500, width=900, template="plotly_dark", showlegend=False)
        return fig
