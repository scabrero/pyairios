"""Data model for the node data fetching functions."""

from dataclasses import dataclass
from datetime import timedelta
from typing import TypedDict

from pyairios.constants import (
    BatteryStatus,
    BoundStatus,
    FaultStatus,
    ProductId,
    RFCommStatus,
    ValueErrorStatus,
)
from pyairios.registers import Result


@dataclass
class AiriosBoundNodeInfo:
    """Bridge bound node information."""

    slave_id: int
    product_id: ProductId
    rf_address: int


class AiriosNodeData(TypedDict):
    """Generic RF node data."""

    slave_id: int
    rf_address: Result[int] | None
    product_id: Result[ProductId] | None
    product_name: Result[str] | None
    sw_version: Result[int] | None
    rf_comm_status: Result[RFCommStatus] | None
    battery_status: Result[BatteryStatus] | None
    fault_status: Result[FaultStatus] | None


class AiriosDeviceData(AiriosNodeData):
    """Generic RF device data."""

    bound_status: Result[BoundStatus] | None
    value_error_status: Result[ValueErrorStatus] | None


##### special devices only, 'normal' node data_models are in their respective models/module file ######


class BRDG02R13Data(AiriosNodeData):
    """BRDG-02R13 node data."""

    rf_sent_messages_last_hour: Result[int] | None
    rf_sent_messages_current_hour: Result[int] | None
    rf_load_last_hour: Result[float] | None
    rf_load_current_hour: Result[float] | None
    power_on_time: Result[timedelta] | None


@dataclass
class AiriosData:
    """Data from all bridge bound nodes."""

    bridge_rf_address: int
    nodes: dict[int, AiriosNodeData]
