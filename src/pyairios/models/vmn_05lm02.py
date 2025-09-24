"""Airios VMN-05LM02 remote implementation."""

from __future__ import annotations

import logging
import re
from typing import List

from pyairios.client import AsyncAiriosModbusClient
from pyairios.constants import VMDRequestedVentilationSpeed
from pyairios.data_model import AiriosDeviceData
from pyairios.device import AiriosDevice
from pyairios.node import _safe_fetch
from pyairios.registers import (
    RegisterAccess,
    RegisterAddress,
    RegisterBase,
    Result,
    U16Register,
)

LOGGER = logging.getLogger(__name__)


class Reg(RegisterAddress):
    """Register set for VMN-05LM02 remote node."""

    REQUESTED_VENTILATION_SPEED = 41000


class NodeData(AiriosDeviceData):
    """VMN-05LM02 remote node data."""

    requested_ventilation_speed: Result[VMDRequestedVentilationSpeed] | None


def pr_id() -> int:
    """
    Get product_id for model VMN_05LM02.
    Named as is to discern from node.product_id register.
    :return: unique int
    """
    return 0x0001C83E


def product_descr() -> str | tuple[str, ...]:
    """
    Get description of product(s) using VMN_05LM02.
    Human-readable text, used in e.g. HomeAssistant Binding UI.
    :return: string or tuple of strings, starting with manufacturer
    """
    return "Siber 4 button Remote"


class Node(AiriosDevice):
    """Represents a VMN-05LM02 Siber 4 button remote node."""

    def __init__(self, slave_id: int, client: AsyncAiriosModbusClient) -> None:
        """Initialize the VMN-05LM02 node instance."""
        super().__init__(slave_id, client)
        LOGGER.debug("Starting Siber Remote Node(%s)", slave_id)
        vmn_registers: List[RegisterBase] = [
            U16Register(
                Reg.REQUESTED_VENTILATION_SPEED, RegisterAccess.READ | RegisterAccess.STATUS
            ),
        ]
        self._add_registers(vmn_registers)

    def __str__(self) -> str:
        prompt = str(re.sub(r"_", "-", self.__module__.upper()))
        return f"{prompt}@{self.slave_id}"

    async def requested_ventilation_speed(self) -> Result[VMDRequestedVentilationSpeed]:
        """Get the requested ventilation speed."""
        regdesc = self.regmap[Reg.REQUESTED_VENTILATION_SPEED]
        result = await self.client.get_register(regdesc, self.slave_id)
        return Result(VMDRequestedVentilationSpeed(result.value), result.status)

    async def fetch_node_data(self) -> NodeData:  # pylint: disable=duplicate-code
        """Get the node device data at once."""

        return NodeData(
            slave_id=self.slave_id,
            rf_address=await _safe_fetch(self.node_rf_address),
            product_id=await _safe_fetch(self.node_product_id),
            sw_version=await _safe_fetch(self.node_software_version),
            product_name=await _safe_fetch(self.node_product_name),
            rf_comm_status=await _safe_fetch(self.node_rf_comm_status),
            battery_status=await _safe_fetch(self.node_battery_status),
            fault_status=await _safe_fetch(self.node_fault_status),
            bound_status=await _safe_fetch(self.device_bound_status),
            value_error_status=await _safe_fetch(self.device_value_error_status),
            requested_ventilation_speed=await _safe_fetch(self.requested_ventilation_speed),
        )

    async def print_data(self) -> None:
        """
        Print labels + states for this particular model in CLI.

        :return: no confirmation, outputs to serial monitor
        """
        res = await self.fetch_node_data()  # customised per model

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

        # super().print_data(res)  # no superclass set up for VMN yet
        print("VMN-05LM02 data")
        print("----------------")
        print(f"    {'Requested ventilation speed:': <40}{res['requested_ventilation_speed']}")
