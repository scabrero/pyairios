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
    VMDBypassMode,
    VMDBypassPosition,
    VMDErrorCode,
    VMDHeater,
    VMDRequestedVentilationSpeed,
    VMDTemperature,
    VMDVentilationSpeed,
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


class VMD02RPS78Data(AiriosDeviceData):
    """VMD-02RPS78 node data."""

    error_code: Result[VMDErrorCode] | None
    ventilation_speed: Result[VMDVentilationSpeed] | None
    override_remaining_time: Result[int] | None
    exhaust_fan_speed: Result[int] | None
    supply_fan_speed: Result[int] | None
    exhaust_fan_rpm: Result[int] | None
    supply_fan_rpm: Result[int] | None
    indoor_air_temperature: Result[VMDTemperature] | None
    outdoor_air_temperature: Result[VMDTemperature] | None
    exhaust_air_temperature: Result[VMDTemperature] | None
    supply_air_temperature: Result[VMDTemperature] | None
    filter_dirty: Result[int] | None
    filter_remaining_percent: Result[int] | None
    filter_duration_days: Result[int] | None
    bypass_position: Result[VMDBypassPosition] | None
    bypass_mode: Result[VMDBypassMode] | None
    bypass_status: Result[int] | None
    defrost: Result[int] | None
    preheater: Result[VMDHeater] | None
    postheater: Result[VMDHeater] | None
    preheater_setpoint: Result[float] | None
    free_ventilation_setpoint: Result[float] | None
    free_ventilation_cooling_offset: Result[float] | None
    frost_protection_preheater_setpoint: Result[float] | None
    preset_high_fan_speed_supply: Result[int] | None
    preset_high_fan_speed_exhaust: Result[int] | None
    preset_medium_fan_speed_supply: Result[int] | None
    preset_medium_fan_speed_exhaust: Result[int] | None
    preset_low_fan_speed_supply: Result[int] | None
    preset_low_fan_speed_exhaust: Result[int] | None
    preset_standby_fan_speed_supply: Result[int] | None
    preset_standby_fan_speed_exhaust: Result[int] | None


class BRDG02R13Data(AiriosNodeData):
    """BRDG-02R13 node data."""

    rf_sent_messages_last_hour: Result[int] | None
    rf_sent_messages_current_hour: Result[int] | None
    rf_load_last_hour: Result[float] | None
    rf_load_current_hour: Result[float] | None
    power_on_time: Result[timedelta] | None


class VMN05LM02Data(AiriosDeviceData):
    """VMN-05LM02 node data."""

    requested_ventilation_speed: Result[VMDRequestedVentilationSpeed] | None


@dataclass
class AiriosData:
    """Data from all bridge bound nodes."""

    bridge_rf_address: int
    nodes: dict[int, AiriosNodeData]
