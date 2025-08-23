"""Airios VMN-05LM02 Siber 4 button Remote implementation."""

from __future__ import annotations

import logging
import re
from typing import List

from pyairios.client import AsyncAiriosModbusClient
from pyairios.constants import VMDRequestedVentilationSpeed
from pyairios.data_model import AiriosDeviceData

# from pyairios.data_model import VMN05LM02Data
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


class VMN05LM02Data(AiriosDeviceData):
    """VMN-05LM02 remote node data."""

    requested_ventilation_speed: Result[VMDRequestedVentilationSpeed] | None


def product_id() -> int:
    # for key VMN_05LM02
    return 0x0001C83E


class VmnNode(AiriosDevice):
    """Represents a VMN-05LM02 Siber 4 button remote node."""

    def __init__(self, slave_id: int, client: AsyncAiriosModbusClient) -> None:
        """Initialize the VMN-05LM02 node instance."""
        super().__init__(slave_id, client)
        LOGGER.debug(f"Starting Siber Remote VmnNode({slave_id})")
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

    async def fetch_vmn_data(self) -> VMN05LM02Data:  # pylint: disable=duplicate-code
        """Get the node device data at once."""

        return VMN05LM02Data(
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

    def print_data(self, res) -> None:
        """
        Print labels + states for this particular model, including VMD base fields

        :param res: the result retrieved earlier by CLI using fetch_vmd_data()
        :return: no confirmation, outputs to serial monitor
        """
        # super().print_data(res)  # no superclass set up yet
        print("VMN-02LM11 data")
        print("----------------")
        print(f"    {'Requested ventilation speed:': <40}{res['requested_ventilation_speed']}")
