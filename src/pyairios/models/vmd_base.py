"""Airios VMD-BASE controller implementation."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

# from typing import List
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

# from pyairios.data_model import VMD02RPS78Data, VMD07RPS13Data
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


@dataclass
class VMDPresetFansSpeeds:
    """Preset fan speeds."""

    exhaust_fan_speed: Result[int] = field(default_factory=int)
    """Exhaust fan speed (%)"""
    supply_fan_speed: Result[int] = field(default_factory=int)
    """Supply fan speed (%)"""

    def __post_init__(self):
        if self.exhaust_fan_speed is None:
            self.exhaust_fan_speed = Result(-1)
        if self.supply_fan_speed is None:
            self.supply_fan_speed = Result(-1)


class Reg(RegisterAddress):
    """Register set for VMD-BASE controller node."""


def product_id() -> int:
    # base class, should not be called
    return 0x0


class VMD_BASE(AiriosDevice):
    """Base class for VMD-xxx controller nodes."""

    def __init__(self, slave_id: int, client: AsyncAiriosModbusClient) -> None:
        """Initialize the VMD-x controller node instance."""
        super().__init__(slave_id, client)
        # vmd_registers: List[RegisterBase] = [
        #     U16Register(Reg.CURRENT_VENTILATION_SPEED, RegisterAccess.READ | RegisterAccess.STATUS),
        #     U16Register(Reg.FAN_SPEED_EXHAUST, RegisterAccess.READ | RegisterAccess.STATUS),
        #     U16Register(Reg.FAN_SPEED_SUPPLY, RegisterAccess.READ | RegisterAccess.STATUS),
        #     U16Register(Reg.ERROR_CODE, RegisterAccess.READ | RegisterAccess.STATUS),
        #     U16Register(
        #         Reg.VENTILATION_SPEED_OVERRIDE_REMAINING_TIME,
        #         RegisterAccess.READ | RegisterAccess.STATUS,
        #     ),
        #     FloatRegister(Reg.TEMPERATURE_INDOOR, RegisterAccess.READ | RegisterAccess.STATUS),
        #     FloatRegister(Reg.TEMPERATURE_OUTDOOR, RegisterAccess.READ | RegisterAccess.STATUS),
        #     FloatRegister(Reg.TEMPERATURE_EXHAUST, RegisterAccess.READ | RegisterAccess.STATUS),
        #     FloatRegister(Reg.TEMPERATURE_SUPPLY, RegisterAccess.READ | RegisterAccess.STATUS),
        #     U16Register(Reg.PREHEATER, RegisterAccess.READ | RegisterAccess.STATUS),
        #     U16Register(Reg.FILTER_DIRTY, RegisterAccess.READ | RegisterAccess.STATUS),
        #     U16Register(Reg.DEFROST, RegisterAccess.READ | RegisterAccess.STATUS),
        #     U16Register(Reg.BYPASS_POSITION, RegisterAccess.READ | RegisterAccess.STATUS),
        #     U16Register(Reg.HUMIDITY_INDOOR, RegisterAccess.READ | RegisterAccess.STATUS),
        #     U16Register(Reg.HUMIDITY_OUTDOOR, RegisterAccess.READ | RegisterAccess.STATUS),
        #     FloatRegister(Reg.FLOW_INLET, RegisterAccess.READ | RegisterAccess.STATUS),
        #     FloatRegister(Reg.FLOW_OUTLET, RegisterAccess.READ | RegisterAccess.STATUS),
        #     U16Register(Reg.AIR_QUALITY, RegisterAccess.READ | RegisterAccess.STATUS),
        #     U16Register(Reg.AIR_QUALITY_BASIS, RegisterAccess.READ | RegisterAccess.STATUS),
        #     U16Register(Reg.CO2_LEVEL, RegisterAccess.READ | RegisterAccess.STATUS),
        #     U16Register(Reg.POST_HEATER, RegisterAccess.READ | RegisterAccess.STATUS),
        #     U16Register(Reg.CAPABILITIES, RegisterAccess.READ | RegisterAccess.STATUS),
        #     U16Register(Reg.FILTER_REMAINING_DAYS, RegisterAccess.READ | RegisterAccess.STATUS),
        #     U16Register(Reg.FILTER_DURATION, RegisterAccess.READ | RegisterAccess.STATUS),
        #     U16Register(Reg.FILTER_REMAINING_PERCENT, RegisterAccess.READ | RegisterAccess.STATUS),
        #     U16Register(Reg.FAN_RPM_EXHAUST, RegisterAccess.READ | RegisterAccess.STATUS),
        #     U16Register(Reg.FAN_RPM_SUPPLY, RegisterAccess.READ | RegisterAccess.STATUS),
        #     U16Register(Reg.BYPASS_MODE, RegisterAccess.READ | RegisterAccess.STATUS),
        #     U16Register(Reg.BYPASS_STATUS, RegisterAccess.READ | RegisterAccess.STATUS),
        #     U16Register(
        #         Reg.REQUESTED_VENTILATION_SPEED,
        #         RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
        #     ),
        #     U16Register(Reg.OVERRIDE_TIME_SPEED_LOW, RegisterAccess.WRITE),
        #     U16Register(Reg.OVERRIDE_TIME_SPEED_MID, RegisterAccess.WRITE),
        #     U16Register(Reg.OVERRIDE_TIME_SPEED_HIGH, RegisterAccess.WRITE),
        #     U16Register(
        #         Reg.REQUESTED_BYPASS_MODE,
        #         RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
        #     ),
        #     U16Register(Reg.FILTER_RESET, RegisterAccess.WRITE | RegisterAccess.STATUS),
        #     U16Register(
        #         Reg.FAN_SPEED_AWAY_SUPPLY,
        #         RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
        #     ),
        #     U16Register(
        #         Reg.FAN_SPEED_AWAY_EXHAUST,
        #         RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
        #     ),
        #     U16Register(
        #         Reg.FAN_SPEED_LOW_SUPPLY,
        #         RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
        #     ),
        #     U16Register(
        #         Reg.FAN_SPEED_LOW_EXHAUST,
        #         RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
        #     ),
        #     U16Register(
        #         Reg.FAN_SPEED_MID_SUPPLY,
        #         RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
        #     ),
        #     U16Register(
        #         Reg.FAN_SPEED_MID_EXHAUST,
        #         RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
        #     ),
        #     U16Register(
        #         Reg.FAN_SPEED_HIGH_SUPPLY,
        #         RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
        #     ),
        #     U16Register(
        #         Reg.FAN_SPEED_HIGH_EXHAUST,
        #         RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
        #     ),
        #     FloatRegister(
        #         Reg.FROST_PROTECTION_PREHEATER_SETPOINT,
        #         RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
        #     ),
        #     FloatRegister(
        #         Reg.PREHEATER_SETPOINT,
        #         RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
        #     ),
        #     FloatRegister(
        #         Reg.FREE_VENTILATION_HEATING_SETPOINT,
        #         RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
        #     ),
        #     FloatRegister(
        #         Reg.FREE_VENTILATION_COOLING_OFFSET,
        #         RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
        #     ),
        # ]
        # self._add_registers(vmd_registers)

    def __str__(self) -> str:
        # TODO how to use this from subclasses using correct slave_id?
        prompt = str(re.sub(r"_", "-", self.__module__.__getattribute__(__name__).upper()))
        return f"{prompt}@{self.slave_id}"

    def print_data(self, result) -> None:
        print("----------------")
