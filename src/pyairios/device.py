"""RF device implementation."""

from __future__ import annotations

from typing import List

from .client import AsyncAiriosModbusClient
from .constants import BoundStatus, ValueErrorStatus
from .data_model import AiriosDeviceData
from .node import AiriosNode
from .registers import (
    I16Register,
    RegisterAccess,
    RegisterAddress,
    RegisterBase,
    Result,
    U16Register,
)


class Reg(RegisterAddress):
    """Register set for RF devices."""

    RF_LAST_SEEN = 40100
    VALUE_ERROR_STATUS = 40104
    RF_LAST_RSSI = 40109
    BOUND_STATUS = 40110


class AiriosDevice(AiriosNode):
    """Represents a RF device."""

    def __init__(self, slave_id: int, client: AsyncAiriosModbusClient) -> None:
        """Initialize the device class instance."""
        super().__init__(slave_id, client)
        dev_registers: List[RegisterBase] = [
            U16Register(Reg.RF_LAST_SEEN, RegisterAccess.READ),
            U16Register(Reg.VALUE_ERROR_STATUS, RegisterAccess.READ),
            I16Register(Reg.RF_LAST_RSSI, RegisterAccess.READ),
            U16Register(Reg.BOUND_STATUS, RegisterAccess.READ),
        ]
        self._add_registers(dev_registers)

    async def device_bound_status(self) -> Result[BoundStatus]:
        """Get the device bound status."""
        result = await self.client.get_register(self.regmap[Reg.BOUND_STATUS], self.slave_id)
        return Result(BoundStatus(result.value), result.status)

    async def device_value_error_status(self) -> Result[ValueErrorStatus]:
        """Get the device value error status."""
        result = await self.client.get_register(self.regmap[Reg.VALUE_ERROR_STATUS], self.slave_id)
        return Result(ValueErrorStatus(result.value), result.status)

    async def fetch_device(self) -> AiriosDeviceData:  # pylint: disable=duplicate-code
        """Fetch the device data."""

        return AiriosDeviceData(
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
        )
