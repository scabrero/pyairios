"""Data model for the node data fetching functions."""

from dataclasses import dataclass
from typing import Dict

from pyairios.properties import AiriosBaseProperty
from pyairios.registers import Result

type AiriosDeviceData = Dict[AiriosBaseProperty, Result]


@dataclass
class AiriosData:
    """Data from bridge and all bound nodes."""

    bridge: AiriosDeviceData
    nodes: Dict[int, AiriosDeviceData]
