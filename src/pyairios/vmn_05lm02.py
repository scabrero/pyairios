"""Airios VMN-05LM02 remote implementation."""

from __future__ import annotations

from typing import List

from .client import AsyncAiriosModbusClient
from .constants import VMDRequestedVentilationSpeed
from .data_model import VMN05LM02Data
from .device import AiriosDevice
from .registers import (
    RegisterAccess,
    RegisterAddress,
    RegisterBase,
    Result,
    U16Register,
)


class Reg(RegisterAddress):
    """Register set for VMN-05LM02 remote node."""

    REQUESTED_VENTILATION_SPEED = 41000


class VMN05LM02(AiriosDevice):
    """Represents a VMN-05LM02 remote node."""

    def __init__(self, slave_id: int, client: AsyncAiriosModbusClient) -> None:
        """Initialize the VMN-05LM02 node instance."""
        super().__init__(slave_id, client)
        vmn_registers: List[RegisterBase] = [
            U16Register(
                Reg.REQUESTED_VENTILATION_SPEED, RegisterAccess.READ | RegisterAccess.STATUS
            ),
        ]
        self._add_registers(vmn_registers)

    def __str__(self) -> str:
        return f"VMN-05LM02@{self.slave_id}"

    async def requested_ventilation_speed(self) -> Result[VMDRequestedVentilationSpeed]:
        """Get the requested ventilation speed."""
        regdesc = self.regmap[Reg.REQUESTED_VENTILATION_SPEED]
        result = await self.client.get_register(regdesc, self.slave_id)
        return Result(VMDRequestedVentilationSpeed(result.value), result.status)

    async def fetch_vmn_data(self) -> VMN05LM02Data:  # pylint: disable=duplicate-code
        """Get the node device data at once."""

        return VMN05LM02Data(
            slave_id=self.slave_id,
            rf_address=await self._safe_fetch(self.node_rf_address),
            product_id=await self._safe_fetch(self.node_product_id),
            sw_version=await self._safe_fetch(self.node_software_version),
            product_name=await self._safe_fetch(self.node_product_name),
            rf_comm_status=await self._safe_fetch(self.node_rf_comm_status),
            battery_status=await self._safe_fetch(self.node_battery_status),
            fault_status=await self._safe_fetch(self.node_fault_status),
            bound_status=await self._safe_fetch(self.device_bound_status),
            value_error_status=await self._safe_fetch(self.device_value_error_status),
            requested_ventilation_speed=await self._safe_fetch(self.requested_ventilation_speed),
        )
