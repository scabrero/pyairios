"""Data model for the node data fetching functions."""

from dataclasses import dataclass
from typing import Dict

from pyairios.constants import ProductId
from pyairios.registers import Result
from pyairios.properties import AiriosBaseProperty


@dataclass
class AiriosBoundNodeInfo:
    """Bridge bound node information."""

    device_id: int
    product_id: ProductId
    rf_address: int


type AiriosDeviceData = Dict[AiriosBaseProperty, Result]


@dataclass
class AiriosData:
    """Data from bridge and all bound nodes."""

    bridge: AiriosDeviceData
    nodes: Dict[int, AiriosDeviceData]
