"""
logger.py
============

This module provides a simple logging facility for the digital twin.
It collects telemetry dictionaries emitted by the simulator and can
export them to CSV or JSON files.  Real data centre monitoring
systems produce continuous streams of sensor data; this logger
mimics such behaviour by appending a new record at each timestep.

Students can extend this module to connect to MQTT brokers, cloud
storage or time‑series databases.  The default implementation uses
Python’s standard ``csv`` and ``json`` modules to avoid extra
dependencies.
"""

from __future__ import annotations

import csv
import json
from typing import Dict, List


class TelemetryLogger:
    """Collects and exports telemetry packets.

    The logger simply stores each telemetry record in a list.  The
    :meth:`export_csv` and :meth:`export_json` methods write the
    accumulated data to disk.
    """
    def __init__(self) -> None:
        self.records: List[Dict] = []

    def append(self, telemetry: Dict) -> None:
        """Add a telemetry record to the log."""
        # Shallow copy to decouple from simulator state
        self.records.append(json.loads(json.dumps(telemetry)))

    def export_json(self, filename: str) -> None:
        """Export all telemetry to a JSON file.

        Parameters
        ----------
        filename : str
            Path to the JSON file to write.  Existing files will be
            overwritten.
        """
        with open(filename, "w") as f:
            json.dump(self.records, f, indent=2)

    def export_csv(self, filename: str) -> None:
        """Export all telemetry to a CSV file.

        The CSV format flattens nested structures by prefixing keys
        (e.g., ``racks_0_power_draw``).  Only scalar values are
        recorded; lists of racks are unrolled into separate columns.
        """
        if not self.records:
            return
        # Determine all column names
        first = self.records[0]
        columns = []
        # Top‑level scalar fields
        for key, value in first.items():
            if isinstance(value, (int, float, str)):
                columns.append(key)
        # Rack fields (racks is a list of dicts)
        max_racks = max(len(rec["racks"]) for rec in self.records)
        rack_keys = list(self.records[0]["racks"][0].keys())
        for idx in range(max_racks):
            for rk in rack_keys:
                columns.append(f"rack{idx}_{rk}")
        # Room fields
        for key in self.records[0]["room"].keys():
            columns.append(f"room_{key}")
        # PUE
        columns.append("pue")
        # Write CSV
        with open(filename, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            for rec in self.records:
                row = {}
                # Scalar fields
                for key in columns:
                    if key in rec:
                        row[key] = rec[key]
                # Racks
                for idx, rack in enumerate(rec["racks"]):
                    for rk, val in rack.items():
                        row[f"rack{idx}_{rk}"] = val
                # Room
                for k, v in rec["room"].items():
                    row[f"room_{k}"] = v
                # PUE
                row["pue"] = rec["pue"]
                writer.writerow(row)
