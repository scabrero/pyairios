"""Airios VMD-02RPS78 controller implementation."""

from __future__ import annotations

import math

from dataclasses import dataclass, field
from typing import List

from pyairios.client import AsyncAiriosModbusClient
from pyairios.constants import (
    VMDBypassMode,
    VMDBypassPosition,
    VMDCapabilities,
    VMDErrorCode,
    VMDHeater,
    VMDHeaterStatus,
    VMDRequestedVentilationSpeed,
    VMDSensorStatus,
    VMDTemperature,
    VMDVentilationSpeed,
)
from pyairios.data_model import VMD02RPS78Data
from pyairios.device import AiriosDevice
from pyairios.exceptions import AiriosInvalidArgumentException
from pyairios.node import _safe_fetch
from pyairios.registers import (
    FloatRegister,
    RegisterAccess,
    RegisterAddress,
    RegisterBase,
    Result,
    U16Register,
)


# serious
# @dataclass
# class VMDPresetFansSpeeds:
#     """Preset fan speeds."""
#
#     exhaust_fan_speed: Result[int] = field(default_factory=int)
#     """Exhaust fan speed (%)"""
#     supply_fan_speed: Result[int] = field(default_factory=int)
#     """Supply fan speed (%)"""
#
#     def __post_init__(self):
#         if self.exhaust_fan_speed is None:
#             self.exhaust_fan_speed = Result(-1)
#         if self.supply_fan_speed is None:
#             self.supply_fan_speed = Result(-1)


class Reg(RegisterAddress):
    """Register set for VMD-02RPS78 controller node."""

    CURRENT_VENTILATION_SPEED = 41000
    FAN_SPEED_EXHAUST = 41001
    FAN_SPEED_SUPPLY = 41002
    ERROR_CODE = 41003
    VENTILATION_SPEED_OVERRIDE_REMAINING_TIME = 41004
    TEMPERATURE_INDOOR = 41005
    TEMPERATURE_OUTDOOR = 41007
    TEMPERATURE_EXHAUST = 41009
    TEMPERATURE_SUPPLY = 41011
    PREHEATER = 41013
    FILTER_DIRTY = 41014
    DEFROST = 41015
    BYPASS_POSITION = 41016
    HUMIDITY_INDOOR = 41017
    HUMIDITY_OUTDOOR = 41018
    FLOW_INLET = 41019
    FLOW_OUTLET = 41021
    AIR_QUALITY = 41023
    AIR_QUALITY_BASIS = 41024
    CO2_LEVEL = 41025
    POST_HEATER = 41026
    CAPABILITIES = 41027
    FILTER_REMAINING_DAYS = 41040
    FILTER_DURATION = 41041
    FILTER_REMAINING_PERCENT = 41042
    FAN_RPM_EXHAUST = 41043
    FAN_RPM_SUPPLY = 41044
    BYPASS_MODE = 41050
    BYPASS_STATUS = 41051
    REQUESTED_VENTILATION_SPEED = 41500
    OVERRIDE_TIME_SPEED_LOW = 41501
    OVERRIDE_TIME_SPEED_MID = 41502
    OVERRIDE_TIME_SPEED_HIGH = 41503
    REQUESTED_BYPASS_MODE = 41550
    FILTER_RESET = 42000
    FAN_SPEED_AWAY_SUPPLY = 42001
    FAN_SPEED_AWAY_EXHAUST = 42002
    FAN_SPEED_LOW_SUPPLY = 42003
    FAN_SPEED_LOW_EXHAUST = 42004
    FAN_SPEED_MID_SUPPLY = 42005
    FAN_SPEED_MID_EXHAUST = 42006
    FAN_SPEED_HIGH_SUPPLY = 42007
    FAN_SPEED_HIGH_EXHAUST = 42008
    FROST_PROTECTION_PREHEATER_SETPOINT = 42009
    PREHEATER_SETPOINT = 42011
    FREE_VENTILATION_HEATING_SETPOINT = 42013
    FREE_VENTILATION_COOLING_OFFSET = 42015


def product_id() -> int:
    # for key VMD_02RPS78
    return 0x0001C892


class VMD_BASE(AiriosDevice):
    """Base class for VMD-xxx controller nodes."""

    def __init__(self, slave_id: int, client: AsyncAiriosModbusClient) -> None:
        """Initialize the VMD-x controller node instance."""
        super().__init__(slave_id, client)
        vmd_registers: List[RegisterBase] = [
            U16Register(Reg.CURRENT_VENTILATION_SPEED, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.FAN_SPEED_EXHAUST, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.FAN_SPEED_SUPPLY, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.ERROR_CODE, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(
                Reg.VENTILATION_SPEED_OVERRIDE_REMAINING_TIME,
                RegisterAccess.READ | RegisterAccess.STATUS,
            ),
            FloatRegister(Reg.TEMPERATURE_INDOOR, RegisterAccess.READ | RegisterAccess.STATUS),
            FloatRegister(Reg.TEMPERATURE_OUTDOOR, RegisterAccess.READ | RegisterAccess.STATUS),
            FloatRegister(Reg.TEMPERATURE_EXHAUST, RegisterAccess.READ | RegisterAccess.STATUS),
            FloatRegister(Reg.TEMPERATURE_SUPPLY, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.PREHEATER, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.FILTER_DIRTY, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.DEFROST, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.BYPASS_POSITION, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.HUMIDITY_INDOOR, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.HUMIDITY_OUTDOOR, RegisterAccess.READ | RegisterAccess.STATUS),
            FloatRegister(Reg.FLOW_INLET, RegisterAccess.READ | RegisterAccess.STATUS),
            FloatRegister(Reg.FLOW_OUTLET, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.AIR_QUALITY, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.AIR_QUALITY_BASIS, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.CO2_LEVEL, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.POST_HEATER, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.CAPABILITIES, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.FILTER_REMAINING_DAYS, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.FILTER_DURATION, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.FILTER_REMAINING_PERCENT, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.FAN_RPM_EXHAUST, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.FAN_RPM_SUPPLY, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.BYPASS_MODE, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.BYPASS_STATUS, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(
                Reg.REQUESTED_VENTILATION_SPEED,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            U16Register(Reg.OVERRIDE_TIME_SPEED_LOW, RegisterAccess.WRITE),
            U16Register(Reg.OVERRIDE_TIME_SPEED_MID, RegisterAccess.WRITE),
            U16Register(Reg.OVERRIDE_TIME_SPEED_HIGH, RegisterAccess.WRITE),
            U16Register(
                Reg.REQUESTED_BYPASS_MODE,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            U16Register(Reg.FILTER_RESET, RegisterAccess.WRITE | RegisterAccess.STATUS),
            U16Register(
                Reg.FAN_SPEED_AWAY_SUPPLY,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            U16Register(
                Reg.FAN_SPEED_AWAY_EXHAUST,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            U16Register(
                Reg.FAN_SPEED_LOW_SUPPLY,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            U16Register(
                Reg.FAN_SPEED_LOW_EXHAUST,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            U16Register(
                Reg.FAN_SPEED_MID_SUPPLY,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            U16Register(
                Reg.FAN_SPEED_MID_EXHAUST,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            U16Register(
                Reg.FAN_SPEED_HIGH_SUPPLY,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            U16Register(
                Reg.FAN_SPEED_HIGH_EXHAUST,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            FloatRegister(
                Reg.FROST_PROTECTION_PREHEATER_SETPOINT,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            FloatRegister(
                Reg.PREHEATER_SETPOINT,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            FloatRegister(
                Reg.FREE_VENTILATION_HEATING_SETPOINT,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            FloatRegister(
                Reg.FREE_VENTILATION_COOLING_OFFSET,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
        ]
        self._add_registers(vmd_registers)

    def __str__(self) -> str:
        return f"VMD-02RPS78@{self.slave_id}"  # could be a filename  # TODO pass in  prompt
