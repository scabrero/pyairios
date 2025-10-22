"""Airios VMN-05LM02 remote implementation."""

from __future__ import annotations

import logging
from typing import List

from pyairios.client import AsyncAiriosModbusClient
from pyairios.constants import VMDRequestedVentilationSpeed
from pyairios.node import AiriosNode
from pyairios.properties import AiriosVMNProperty as dp
from pyairios.registers import (
    RegisterAccess,
    RegisterBase,
    Result,
    U16Register,
)

LOGGER = logging.getLogger(__name__)


class VMN05LM02(AiriosNode):
    """Represents a VMN-05LM02 remote node."""

    def __init__(self, device_id: int, client: AsyncAiriosModbusClient) -> None:
        """Initialize the VMN-05LM02 node instance."""
        super().__init__(device_id, client)
        vmn_registers: List[RegisterBase] = [
            U16Register(
                dp.REQUESTED_VENTILATION_SPEED, 41000, RegisterAccess.READ | RegisterAccess.STATUS
            ),
        ]
        self._add_registers(vmn_registers)

    def __str__(self) -> str:
        return f"VMN-05LM02@{self.device_id}"

    async def requested_ventilation_speed(self) -> Result[VMDRequestedVentilationSpeed]:
        """Get the requested ventilation speed."""
        regdesc = self.regmap[dp.REQUESTED_VENTILATION_SPEED]
        result = await self.client.get_register(regdesc, self.device_id)
        return Result(VMDRequestedVentilationSpeed(result.value), result.status)
