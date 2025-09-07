"""Airios VMD-BASE controller implementation."""

from __future__ import annotations

# import re
from dataclasses import dataclass, field

from pyairios.client import AsyncAiriosModbusClient
from pyairios.constants import VMDCapabilities
from pyairios.device import AiriosDevice
from pyairios.registers import (
    RegisterAddress,
    Result,
)


@dataclass
class VMDPresetFansSpeeds:
    """Preset fan speeds."""

    # this must load from vmd_base to prevent None error
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


def pr_id() -> int:
    # can't be named product_id to discern from node.product_id
    # base class, should not be called
    return 0x0


def product_descr() -> str | tuple[str, ...]:
    # base class, should not be called
    return "-"


class VmdBase(AiriosDevice):
    """Base class for VMD-xxx controller nodes."""

    def __init__(self, slave_id: int, client: AsyncAiriosModbusClient) -> None:
        """Initialize the VMD-x controller node instance."""
        super().__init__(slave_id, client)

        # vmd_registers: List[RegisterBase] = [
        #     U16Register(Reg.CURRENT_VENTILATION_SPEED, RegisterAccess.READ_STATUS),
        #     U16Register(Reg.FAN_SPEED_EXHAUST, RegisterAccess.READ_STATUS),
        #     U16Register(Reg.FAN_SPEED_SUPPLY, RegisterAccess.READ_STATUS),
        #     U16Register(Reg.ERROR_CODE, RegisterAccess.READ_STATUS),
        #     U16Register(
        #         Reg.VENTILATION_SPEED_OVERRIDE_REMAINING_TIME,
        #         RegisterAccess.READ_STATUS,
        #     ),
        #     FloatRegister(Reg.TEMPERATURE_INDOOR, RegisterAccess.READ_STATUS),
        #     FloatRegister(Reg.TEMPERATURE_OUTDOOR, RegisterAccess.READ_STATUS),
        #     FloatRegister(Reg.TEMPERATURE_EXHAUST, RegisterAccess.READ_STATUS),
        #     FloatRegister(Reg.TEMPERATURE_SUPPLY, RegisterAccess.READ_STATUS),
        #     U16Register(Reg.PREHEATER, RegisterAccess.READ_STATUS),
        #     U16Register(Reg.FILTER_DIRTY, RegisterAccess.READ_STATUS),
        #     U16Register(Reg.DEFROST, RegisterAccess.READ_STATUS),
        #     U16Register(Reg.BYPASS_POSITION, RegisterAccess.READ_STATUS),
        #     U16Register(Reg.HUMIDITY_INDOOR, RegisterAccess.READ_STATUS),
        #     U16Register(Reg.HUMIDITY_OUTDOOR, RegisterAccess.READ_STATUS),
        #     FloatRegister(Reg.FLOW_INLET, RegisterAccess.READ_STATUS),
        #     FloatRegister(Reg.FLOW_OUTLET, RegisterAccess.READ_STATUS),
        #     U16Register(Reg.AIR_QUALITY, RegisterAccess.READ_STATUS),
        #     U16Register(Reg.AIR_QUALITY_BASIS, RegisterAccess.READ_STATUS),
        #     U16Register(Reg.CO2_LEVEL, RegisterAccess.READ_STATUS),
        #     U16Register(Reg.POST_HEATER, RegisterAccess.READ_STATUS),
        #     U16Register(Reg.CAPABILITIES, RegisterAccess.READ_STATUS),
        #     U16Register(Reg.FILTER_REMAINING_DAYS, RegisterAccess.READ_STATUS),
        #     U16Register(Reg.FILTER_DURATION, RegisterAccess.READ_STATUS),
        #     U16Register(Reg.FILTER_REMAINING_PERCENT, RegisterAccess.READ_STATUS),
        #     U16Register(Reg.FAN_RPM_EXHAUST, RegisterAccess.READ_STATUS),
        #     U16Register(Reg.FAN_RPM_SUPPLY, RegisterAccess.READ_STATUS),
        #     U16Register(Reg.BYPASS_MODE, RegisterAccess.READ_STATUS),
        #     U16Register(Reg.BYPASS_STATUS, RegisterAccess.READ_STATUS),
        #     U16Register(
        #         Reg.REQUESTED_VENTILATION_SPEED,
        #         RegisterAccess.READ_WRITE_STATUS,
        #     ),
        #     U16Register(Reg.OVERRIDE_TIME_SPEED_LOW, RegisterAccess.WRITE),
        #     U16Register(Reg.OVERRIDE_TIME_SPEED_MID, RegisterAccess.WRITE),
        #     U16Register(Reg.OVERRIDE_TIME_SPEED_HIGH, RegisterAccess.WRITE),
        #     U16Register(
        #         Reg.REQUESTED_BYPASS_MODE,
        #         RegisterAccess.READ_WRITE_STATUS,
        #     ),
        #     U16Register(Reg.FILTER_RESET, RegisterAccess.WRITE_STATUS),
        #     U16Register(
        #         Reg.FAN_SPEED_AWAY_SUPPLY,
        #         RegisterAccess.READ_WRITE_STATUS,
        #     ),
        #     U16Register(
        #         Reg.FAN_SPEED_AWAY_EXHAUST,
        #         RegisterAccess.READ_WRITE_STATUS,
        #     ),
        #     U16Register(
        #         Reg.FAN_SPEED_LOW_SUPPLY,
        #         RegisterAccess.READ_WRITE_STATUS,
        #     ),
        #     U16Register(
        #         Reg.FAN_SPEED_LOW_EXHAUST,
        #         RegisterAccess.READ_WRITE_STATUS,
        #     ),
        #     U16Register(
        #         Reg.FAN_SPEED_MID_SUPPLY,
        #         RegisterAccess.READ_WRITE_STATUS,
        #     ),
        #     U16Register(
        #         Reg.FAN_SPEED_MID_EXHAUST,
        #         RegisterAccess.READ_WRITE_STATUS,
        #     ),
        #     U16Register(
        #         Reg.FAN_SPEED_HIGH_SUPPLY,
        #         RegisterAccess.READ_WRITE_STATUS,
        #     ),
        #     U16Register(
        #         Reg.FAN_SPEED_HIGH_EXHAUST,
        #         RegisterAccess.READ_WRITE_STATUS,
        #     ),
        #     FloatRegister(
        #         Reg.FROST_PROTECTION_PREHEATER_SETPOINT,
        #         RegisterAccess.READ_WRITE_STATUS,
        #     ),
        #     FloatRegister(
        #         Reg.PREHEATER_SETPOINT,
        #         RegisterAccess.READ_WRITE_STATUS,
        #     ),
        #     FloatRegister(
        #         Reg.FREE_VENTILATION_HEATING_SETPOINT,
        #         RegisterAccess.READ_WRITE_STATUS,
        #     ),
        #     FloatRegister(
        #         Reg.FREE_VENTILATION_COOLING_OFFSET,
        #         RegisterAccess.READ_WRITE_STATUS,
        #     ),
        # ]
        # self._add_registers(vmd_registers)

    # def __str__(self) -> str:
    #     prompt = str(re.sub(r"_", "-", self.__module__.upper()))
    #     return f"{prompt}@{self.slave_id}"

    async def capabilities(self) -> Result[VMDCapabilities] | None:
        # not all fans support capabilities register call, must return basics
        return Result(VMDCapabilities(), None)

    def print_data(self, res) -> None:
        print("Node data")
        print("---------")
        print(f"    {'Product ID:': <25}{res['product_id']} (0x{int(res['product_id'].value):08X})")
        print(f"    {'Product Name:': <25}{res['product_name']}")
        print(f"    {'Software version:': <25}{res['sw_version']}")
        print(f"    {'RF address:': <25}{res['rf_address']}")
        print("")

        print("Device data")
        print("---------")
        print(f"    {'RF comm status:': <25}{res['rf_comm_status']}")
        print(f"    {'Battery status:': <25}{res['battery_status']}")
        print(f"    {'Fault status:': <25}{res['fault_status']}")
        print(f"    {'Bound status:': <25}{res['bound_status']}")
        print(f"    {'Value error status:': <25}{res['value_error_status']}")
        print("")

        print("----------------")
