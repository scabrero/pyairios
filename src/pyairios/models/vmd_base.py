"""Airios VMD-BASE controller implementation."""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field

from pyairios.constants import VMDCapabilities, ValueStatusSource, ValueStatusFlags
from pyairios.device import AiriosDevice
from pyairios.registers import (
    RegisterAddress,
    Result,
    ResultStatus,
)


@dataclass
class VMDPresetFansSpeeds:
    """Preset fan speeds."""

    # this must load from vmd_base to prevent None error
    exhaust_fan_speed: Result[int] = field()
    """Exhaust fan speed (%)"""
    supply_fan_speed: Result[int] = field()
    """Supply fan speed (%)"""

    def __post_init__(self):
        if self.exhaust_fan_speed is None:
            self.exhaust_fan_speed = Result(-1)
        if self.supply_fan_speed is None:
            self.supply_fan_speed = Result(-1)


class Reg(RegisterAddress):
    """Register set for VMD-BASE controller node."""


def pr_id() -> int:
    """
    Get product_id for model VMD- models.
    Named as is to discern from node.product_id register.
    :return: unique int
    """
    # base class, should not be called
    return 0x0


def product_descr() -> str | tuple[str, ...]:
    """
    Get description of product(s) using VMD_xxxx.
    Human-readable text, used in e.g. HomeAssistant Binding UI.
    :return: string or tuple of strings, starting with manufacturer
    """
    # base class, should not be called
    return "-"


class VmdBase(AiriosDevice):
    """Base class for VMD-xxx controller nodes."""

    # no VMD-common registers found, leave here as example for new models that do
    # def __init__(self, slave_id: int, client: AsyncAiriosModbusClient) -> None:
    #     """Initialize the VMD-x controller node instance."""
    #     super().__init__(slave_id, client)

    #     vmd_registers: List[RegisterBase] = [
    #         U16Register(Reg.CURRENT_VENTILATION_SPEED, RegisterAccess.READ_STATUS),
    #         ...
    #     ]
    #     self._add_registers(vmd_registers)

    async def capabilities(self) -> Result[VMDCapabilities] | None:
        """Get the ventilation unit capabilities.
        If Capabilities register not supported on model, must simulate"""
        # not all fans support capabilities register call, must return basics
        _caps = VMDCapabilities.NO_CAPABLE
        return Result(
            _caps,
            ResultStatus(
                datetime.timedelta(1000), ValueStatusSource.UNKNOWN, ValueStatusFlags.VALID
            ),
        )

    def print_base_data(self, res) -> None:
        """
        Print shared VMD labels + states, in CLI.

        :return: no confirmation, outputs to serial monitor
        """
        print("Node data")
        print("---------")
        print(f"    {'Product ID:': <25}{res['product_id']} (0x{res['product_id']:08X})")
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
