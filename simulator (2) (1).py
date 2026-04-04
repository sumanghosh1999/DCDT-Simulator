"""
simulator.py
================

This module implements a simple digital‑twin of a data hall for
educational purposes.  The core of the simulator is a discrete 2‑D grid
representing the room.  Each cell holds a temperature value and may
contain a ServerRack or a Cooling device.  Temperature evolves
according to a very simple finite difference scheme for heat
conduction: every timestep, the temperature at a point tends towards
the average of its four neighbours (up, down, left, right).  This is
similar to the discretisation described in Tutorialspoint’s 2‑D heat
conduction article(Check Project User Guide or Tutorial notebook for link),
where the temperature at an internal node is the
average of its neighbours.  Additional heat
sources (racks) and sinks (cooling units) are included as forcing terms.

The simulator also computes common data‑centre metrics such as
Power Usage Effectiveness (PUE).  PUE is defined as the ratio of
the total amount of energy used by a data centre facility to the
energy delivered to computing equipment; a value of
1.0 would indicate perfect efficiency.  In our simplified model the
facility energy consists of the IT power plus an estimate of the
cooling power.

Every method contains a docstring explaining the 
principles behind it.  The simulator supports fault injection
(e.g., failing a rack’s fan or spiking its load) and produces a
structured telemetry packet at every timestep.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

import numpy as np

random.seed(69)
np.random.seed(69)

@dataclass
class ServerRack:
    """Represents a simplified server rack in the data centre.

    Attributes
    ----------
    rack_id: int
        Unique identifier for the rack.
    position: Tuple[int, int]
        (row, column) location of the rack within the grid.
    cpu_load: float
        Fractional workload (0–1).  A value of 0 means idle and 1
        means maximum utilisation.  Students can think of this as the
        proportion of active cores in the rack.
    base_power: float
        Idle power consumption in watts.  Even an idle server draws
        some power to keep components alive.
    max_power: float
        Maximum power draw of the rack at full load.  The power
        consumption at any given time is

        ``power_draw = base_power + cpu_load * (max_power - base_power)``.
    fail_fan_multiplier: float
        When a rack’s cooling fan fails, its ability to expel heat
        decreases.  To model this we multiply the exhaust temperature
        by this factor (>1).  When operating normally the multiplier
        equals 1.

    Notes
    -----
    The rack does not explicitly model individual CPUs or GPUs, but
    aggregates their behaviour.  Students can extend this to
    include more detailed thermal models (e.g., per‑component heat
    generation) if desired.
    """
    rack_id: int
    position: Tuple[int, int]
    cpu_load: float = 0.0
    base_power: float = 500.0
    max_power: float = 1000.0
    fail_fan_multiplier: float = 1.0
    inlet_temp: float = 25.0
    exhaust_temp: float = 40.0

    def update(self, room_temp: float) -> None:
        """Update the rack’s inlet and exhaust temperatures and compute its power.

        Parameters
        ----------
        room_temp : float
            Current temperature of the grid cell in which the rack sits.  In a
            real data centre the inlet temperature depends on the room air
            supplied to the front of the rack (cold aisle), while the
            exhaust temperature reflects the heated air leaving the rear of
            the rack.  Here we simply assume the inlet
            equals the ambient cell temperature and the exhaust is elevated
            proportionally to the power draw.

        Notes
        -----
        A rack’s cooling fans remove heat from the chassis by expelling
        air through the rear.  When the fan fails (``fail_fan_multiplier`` > 1),
        the exhaust becomes hotter because less air is moved.  Students
        are encouraged to vary ``fail_fan_multiplier`` and observe the
        resulting thermal behaviour.
        """
        self.inlet_temp = room_temp
        # Compute power draw based on load
        self.power_draw = self.base_power + self.cpu_load * (self.max_power - self.base_power)
        # Heat generation is proportional to the rack’s power draw.  For
        # every watt consumed, assume 1 joule per second of heat is
        # produced.  Divide by an arbitrary heat capacity to obtain a
        # temperature rise (this constant scales the effect of power on
        # temperature).  The value chosen below (0.1) yields sensible
        # magnitudes for demonstration.
        heat_rise = 0.1 * self.power_draw
        # Exhaust temperature is inlet plus heat rise.  If the fan has
        # failed, multiply the rise.
        self.exhaust_temp = self.inlet_temp + heat_rise * self.fail_fan_multiplier

    def inject_fault(self, fault_type: str) -> None:
        """Inject a fault into the rack.

        Parameters
        ----------
        fault_type : {"fan", "spike", "reset"}
            Type of fault to inject.  "fan" causes the rack’s cooling
            efficiency to drop (multiplies exhaust temperature by 1.5).
            "spike" increases the workload to simulate a sudden surge in
            computational demand.  "reset" clears all faults and returns
            the rack to nominal operation.
        """
        if fault_type == "fan":
            self.fail_fan_multiplier = 1.5
        elif fault_type == "spike":
            # Spike to 100% load briefly
            self.cpu_load = 1.0
        elif fault_type == "reset":
            self.fail_fan_multiplier = 1.0
            # Reset to a modest load
            self.cpu_load = 0.5
        else:
            raise ValueError(f"Unknown fault type: {fault_type}")


@dataclass
class CoolingUnit:
    """Represents a simple Computer Room Air Conditioning (CRAC) unit.

    Parameters
    ----------
    position : Tuple[int, int]
        Grid coordinate of the cooling unit.
    setpoint : float
        Target temperature (°C) that the unit attempts to maintain at its
        outlet.  In practice a CRAC unit blows chilled air into the
        cold aisle and removes warm air from the hot aisle.  This
        simplification models the chilled supply by imposing a low
        temperature boundary at the unit’s location.
    max_cooling_power : float
        Maximum cooling capacity in watts.  A higher value allows the
        unit to extract more heat from the room.  The actual amount of
        heat removed is proportional to the difference between the
        ambient temperature and the setpoint, scaled by a gain factor and
        limited by ``max_cooling_power``.
    """
    position: Tuple[int, int]
    setpoint: float = 20.0
    max_cooling_power: float = 5000.0
    control_signal: float = 1.0  # 0–1 multiplier applied to the cooling power

    def compute_cooling(self, cell_temp: float) -> float:
        """Compute the cooling power delivered by this CRAC unit.

        The cooling power is proportional to the temperature difference
        between the room air and the unit’s setpoint, and scaled by
        ``control_signal``.  It is capped at ``max_cooling_power``.

        Parameters
        ----------
        cell_temp : float
            Current temperature of the cell at the unit’s location.

        Returns
        -------
        cooling_watts : float
            Rate of heat removal (watts).  Positive values indicate heat
            removed from the room.
        """
        delta = max(0.0, cell_temp - self.setpoint)
        cooling_watts = min(self.max_cooling_power * self.control_signal, delta * 200.0)
        return cooling_watts


class DataHall:
    """Simulates a rectangular data hall with heat propagation and cooling.

    A data hall is modelled as a two‑dimensional grid of temperatures.
    Each timestep the temperature at cell (i,j) is updated via a
    diffusion equation similar to the equation of the Tutorialspoint article
    (Ti,j = 1/4(T_{i−1,j}+T_{i+1,j}+T_{i,j−1}+T_{i,j+1})…).  Heat
    generated by racks is added to the appropriate cell, and cooling
    units remove heat from their cells.  A small upward bias is
    included to reflect the fact that hot air tends to rise.

    Parameters
    ----------
    rows, cols : int
        Dimensions of the grid.
    ambient_temp : float
        Initial uniform temperature of the room (°C).
    racks : List[ServerRack]
        List of server racks placed in the hall.
    cooling_units : List[CoolingUnit]
        List of CRAC units providing cooling.
    conduction_coeff : float
        Diffusion coefficient controlling how quickly heat spreads between
        neighbouring cells.  Typical values range from 0.1–0.5.
    convection_bias : float
        Additional weight given to upward (negative row direction) heat
        transfer to model natural convection (hot air rising).  A value
        of 0.1 means roughly 10 % more heat flows upward than downward.
    heat_capacity : float
        Effective heat capacity of the air in each cell.  A higher
        value means temperature changes more slowly for a given amount
        of heat added or removed.
    """

    def __init__(self, rows: int, cols: int, ambient_temp: float,
                 racks: List[ServerRack], cooling_units: List[CoolingUnit],
                 conduction_coeff: float = 0.2, convection_bias: float = 0.1,
                 heat_capacity: float = 1000.0):
        self.rows = rows
        self.cols = cols
        self.grid = np.full((rows, cols), ambient_temp, dtype=float)
        self.racks = racks
        self.cooling_units = cooling_units
        self.conduction_coeff = conduction_coeff
        self.convection_bias = convection_bias
        self.heat_capacity = heat_capacity
        # Map from grid coordinates to rack indices for quick lookup
        self.rack_map: Dict[Tuple[int, int], int] = {rack.position: i for i, rack in enumerate(racks)}
        self.time = 0

    def step(self, dt: float = 1.0) -> Dict:
        """Advance the simulation by one timestep.

        Parameters
        ----------
        dt : float
            Duration of the timestep in seconds.  The discretisation
            parameters (conduction_coeff and heat_capacity) are tuned to
            dt=1.0 s; using different values may require retuning.

        Returns
        -------
        telemetry : Dict
            Telemetry dictionary containing rack metrics, room metrics and
            computed PUE.
        """
        self.time += dt
        # Copy the current grid for computing new temperatures
        new_grid = self.grid.copy()
        # Heat added by racks (W) and removed by cooling (W)
        total_rack_power = 0.0
        total_cooling_power = 0.0
        # Update racks and accumulate heat in grid
        for rack in self.racks:
            row, col = rack.position
            # Update rack state based on current cell temperature
            rack.update(self.grid[row, col])
            total_rack_power += rack.power_draw
            # Convert power (W) to temperature rise: dT = (power * dt) / heat_capacity
            temp_rise = (rack.power_draw * dt) / self.heat_capacity
            new_grid[row, col] += temp_rise
        # Apply cooling units
        for unit in self.cooling_units:
            row, col = unit.position
            cooling = unit.compute_cooling(self.grid[row, col])
            total_cooling_power += cooling
            # Convert cooling power to temperature drop.  Limit the drop so
            # temperatures don’t become unrealistically cold.
            temp_drop = (cooling * dt) / self.heat_capacity
            new_grid[row, col] = max(unit.setpoint, new_grid[row, col] - temp_drop)
        # Conduction/convection update for all cells
        # For each cell, compute heat flow with neighbours
        for i in range(self.rows):
            for j in range(self.cols):
                # Skip if cell contains cooling unit; its temp already updated
                if (i, j) in [unit.position for unit in self.cooling_units]:
                    continue
                # Compute average of neighbours with convection bias upwards
                neighbours: List[Tuple[int, int]] = []
                if i > 0:
                    neighbours.append((i - 1, j))
                if i < self.rows - 1:
                    neighbours.append((i + 1, j))
                if j > 0:
                    neighbours.append((i, j - 1))
                if j < self.cols - 1:
                    neighbours.append((i, j + 1))
                # Weighted sum: upward neighbour gets extra weight
                total = 0.0
                weight_sum = 0.0
                for (ni, nj) in neighbours:
                    weight = 1.0
                    if ni < i:  # neighbour above: hot air rises
                        weight += self.convection_bias
                    total += weight * self.grid[ni, nj]
                    weight_sum += weight
                if weight_sum > 0:
                    avg_neighbour = total / weight_sum
                    # Simple diffusion towards neighbour average
                    diff = avg_neighbour - self.grid[i, j]
                    new_grid[i, j] += self.conduction_coeff * diff * dt
        # Update the grid
        self.grid = new_grid
        # Compute telemetry
        telemetry = {
            "time": self.time,
            "racks": [],
        }
        for rack in self.racks:
            telemetry["racks"].append({
                "id": rack.rack_id,
                "position": rack.position,
                "cpu_load": rack.cpu_load,
                "power_draw": rack.power_draw,
                "inlet_temp": rack.inlet_temp,
                "exhaust_temp": rack.exhaust_temp,
            })
        # Room metrics
        telemetry["room"] = {
            "average_temp": float(np.mean(self.grid)),
            "max_temp": float(np.max(self.grid)),
            "min_temp": float(np.min(self.grid)),
            "humidity": 50.0 + 5.0 * math.sin(0.01 * self.time),  # simple oscillation
        }
        # Compute PUE: (IT + cooling) / IT
        it_energy = total_rack_power
        facility_energy = total_rack_power + total_cooling_power
        telemetry["pue"] = facility_energy / max(it_energy, 1e-6)
        return telemetry

    def reset(self) -> None:
        """Reset the simulation to its initial state."""
        self.grid.fill(np.mean(self.grid))
        self.time = 0.0
        for rack in self.racks:
            rack.cpu_load = 0.5
            rack.fail_fan_multiplier = 1.0
        for unit in self.cooling_units:
            unit.control_signal = 1.0

    def inject_fault(self, rack_id: int, fault_type: str) -> None:
        """Inject a fault into one of the racks.

        Parameters
        ----------
        rack_id : int
            Identifier of the rack into which the fault is injected.
        fault_type : str
            Type of fault (passed to :meth:`ServerRack.inject_fault`).
        """
        for rack in self.racks:
            if rack.rack_id == rack_id:
                rack.inject_fault(fault_type)
                break


def create_default_hall(server_racks, cooling_systems, rows, cols) -> DataHall:
    """Create a default data hall with a few racks and a cooling unit.

    This helper function simplifies the creation of a hall for testing.
    It places three racks at fixed positions and a single cooling unit
    near one corner.  Students can modify this layout to explore
    different thermal interactions.
    """
    racks = []
    cooling_units = []
    
    if server_racks:
      load = np.random.randint(3, 8, size=len(server_racks))/10
      print(load) 
      for i in range(len(server_racks)):
        racks.append(
          ServerRack(rack_id=i, position=tuple(server_racks[i]), cpu_load=load[i])
          )
    else:
      racks = [
          ServerRack(rack_id=0, position=(2, 2), cpu_load=0.5),
          ServerRack(rack_id=1, position=(5, 7), cpu_load=0.6),
          ServerRack(rack_id=2, position=(7, 3), cpu_load=0.4),
      ]

    if cooling_systems:
      for i in range(len(cooling_systems)):
        cooling_units.append(
          CoolingUnit(position=tuple(cooling_systems[i]), setpoint=18.0, max_cooling_power=8000.0)
          )
    else:
      cooling_units = [
          CoolingUnit(position=(0, 0), setpoint=18.0, max_cooling_power=8000.0),
      ]

    hall = DataHall(rows, cols, ambient_temp=25.0, racks=racks, cooling_units=cooling_units)
    return hall


if __name__ == "__main__":
    # Basic test: run the simulator for a few steps and print telemetry.
    hall = create_default_hall()
    for step in range(5):
        telem = hall.step()
        print(f"Time {telem['time']:.1f}s, PUE={telem['pue']:.3f}, MaxTemp={telem['room']['max_temp']:.2f}°C")