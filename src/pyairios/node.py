"""RF node implementation."""

import datetime
import logging
from typing import Callable, Dict, List

from .client import AsyncAiriosModbusClient
from .constants import BatteryStatus, FaultStatus, ProductId, RFCommStatus, RFStats
from .data_model import AiriosNodeData
from .exceptions import AiriosException
from .registers import (
    DateRegister,
    DateTimeRegister,
    FloatRegister,
    RegisterAccess,
    RegisterAddress,
    RegisterBase,
    Result,
    StringRegister,
    U16Register,
    U32Register,
)

_LOGGER = logging.getLogger(__name__)


class Reg(RegisterAddress):
    """Register set for RF nodes."""

    RF_ADDRESS = 40000
    PRODUCT_ID = 40002
    SOFTWARE_VERSION = 40004
    OEM_NUMBER = 40005
    RF_CAPABILITIES = 40006
    MANUFACTURE_DATE = 40007
    SOFTWARE_BUILD_DATE = 40009
    PRODUCT_NAME = 40011
    RECEIVED_PRODUCT_ID = 40021
    RF_COMM_STATUS = 40101
    BATTERY_STATUS = 40102
    FAULT_STATUS = 40103
    RF_STATS_INDEX = 40120
    RF_STATS_LENGTH = 40121
    RF_STATS_DEVICE = 40122
    RF_STATS_AVERAGE = 40124
    RF_STATS_STDDEV = 40125
    RF_STATS_MIN = 40127
    RF_STATS_MAX = 40128
    RF_STATS_MISSED = 40129
    RF_STATS_RECEIVED = 40130
    RF_STATS_AGE = 40131
    FAULT_HISTORY_INDEX = 40300
    FAULT_HISTORY_LENGTH = 40301
    FAULT_HISTORY_TIMESTAMP = 40302
    FAULT_HISTORY_FAULTCODE = 40304
    FAULT_HISTORY_STATUS_INFO = 40305
    FAULT_HISTORY_COMM_STATUS = 40307


class AiriosNode:
    """Represents a RF node."""

    client: AsyncAiriosModbusClient
    slave_id: int
    registers: List[RegisterBase] = []
    regmap: Dict[RegisterAddress, RegisterBase] = {}

    def __init__(self, slave_id: int, client: AsyncAiriosModbusClient) -> None:
        """Initialize the node class instance."""
        self.client = client
        self.slave_id = int(slave_id)
        node_registers: List[RegisterBase] = [
            U32Register(Reg.RF_ADDRESS, RegisterAccess.READ),
            U32Register(Reg.PRODUCT_ID, RegisterAccess.READ),
            U16Register(Reg.SOFTWARE_VERSION, RegisterAccess.READ),
            U16Register(Reg.OEM_NUMBER, RegisterAccess.READ),
            U16Register(Reg.RF_CAPABILITIES, RegisterAccess.READ),
            DateRegister(Reg.MANUFACTURE_DATE, RegisterAccess.READ),
            DateRegister(Reg.SOFTWARE_BUILD_DATE, RegisterAccess.READ),
            StringRegister(Reg.PRODUCT_NAME, 10, RegisterAccess.READ),
            U32Register(Reg.RECEIVED_PRODUCT_ID, RegisterAccess.READ),
            U16Register(Reg.RF_COMM_STATUS, RegisterAccess.READ),
            U16Register(Reg.BATTERY_STATUS, RegisterAccess.READ),
            U16Register(Reg.FAULT_STATUS, RegisterAccess.READ),
            U16Register(Reg.RF_STATS_INDEX, RegisterAccess.READ | RegisterAccess.WRITE),
            U16Register(Reg.RF_STATS_LENGTH, RegisterAccess.READ),
            U32Register(Reg.RF_STATS_DEVICE, RegisterAccess.READ),
            U16Register(Reg.RF_STATS_AVERAGE, RegisterAccess.READ),
            FloatRegister(Reg.RF_STATS_STDDEV, RegisterAccess.READ),
            U16Register(Reg.RF_STATS_MIN, RegisterAccess.READ),
            U16Register(Reg.RF_STATS_MAX, RegisterAccess.READ),
            U16Register(Reg.RF_STATS_MISSED, RegisterAccess.READ),
            U16Register(Reg.RF_STATS_RECEIVED, RegisterAccess.READ),
            U16Register(Reg.RF_STATS_AGE, RegisterAccess.READ),
            U16Register(Reg.FAULT_HISTORY_INDEX, RegisterAccess.READ | RegisterAccess.WRITE),
            U16Register(Reg.FAULT_HISTORY_LENGTH, RegisterAccess.READ | RegisterAccess.WRITE),
            DateTimeRegister(Reg.FAULT_HISTORY_TIMESTAMP, RegisterAccess.READ),
            U16Register(Reg.FAULT_HISTORY_FAULTCODE, RegisterAccess.READ),
            U32Register(Reg.FAULT_HISTORY_STATUS_INFO, RegisterAccess.READ),
            U16Register(Reg.FAULT_HISTORY_COMM_STATUS, RegisterAccess.READ),
        ]
        self._add_registers(node_registers)

    def _add_registers(self, reglist: List[RegisterBase]):
        self.registers.extend(reglist)
        self.regmap: Dict[RegisterAddress, RegisterBase] = {
            regdesc.description.address: regdesc for regdesc in self.registers
        }

    async def node_rf_address(self) -> Result[int]:
        """Get the node RF address, also used as node serial number."""
        return await self.client.get_register(self.regmap[Reg.RF_ADDRESS], self.slave_id)

    async def node_product_id(self) -> Result[ProductId]:
        """Get the node product ID.

        This is the value assigned to the virtual node instance created by the bridge when
        a device is bound. The actual received product ID from the real RF node can is
        available in the RECEIVED_PRODUCT_ID register.
        """
        result = await self.client.get_register(self.regmap[Reg.PRODUCT_ID], self.slave_id)
        return Result(ProductId(result.value), None)

    async def node_software_version(self) -> Result[int]:
        """Get the node software version."""
        return await self.client.get_register(self.regmap[Reg.SOFTWARE_VERSION], self.slave_id)

    async def node_oem_number(self) -> Result[int]:
        """Get the node OEM number.

        It is 0x00 or 0xFF when not used.
        """
        return await self.client.get_register(self.regmap[Reg.OEM_NUMBER], self.slave_id)

    async def node_rf_capabilities(self) -> Result[int]:
        """Get the node RF capabilities.

        The value depends on the specific device.
        """
        return await self.client.get_register(self.regmap[Reg.RF_CAPABILITIES], self.slave_id)

    async def node_manufacture_date(self) -> Result[datetime.date]:
        """Get the node manufacture date."""
        return await self.client.get_register(self.regmap[Reg.MANUFACTURE_DATE], self.slave_id)

    async def node_software_build_date(self) -> Result[datetime.date]:
        """Get the node software build date."""
        return await self.client.get_register(self.regmap[Reg.SOFTWARE_BUILD_DATE], self.slave_id)

    async def node_product_name(self) -> Result[str]:
        """Get the node product name."""
        return await self.client.get_register(self.regmap[Reg.PRODUCT_NAME], self.slave_id)

    async def node_received_product_id(self) -> Result[ProductId]:
        """Get the received product ID.

        This is the value received from the bound node. If it does not match register
        NODE_PRODUCT_ID a wrong product is bound.
        """
        result = await self.client.get_register(self.regmap[Reg.RECEIVED_PRODUCT_ID], self.slave_id)
        return Result(ProductId(result.value), result.status)

    async def node_rf_comm_status(self) -> Result[RFCommStatus]:
        """Get the node RF communication status."""
        return await self.client.get_register(self.regmap[Reg.RF_COMM_STATUS], self.slave_id)

    async def node_battery_status(self) -> Result[BatteryStatus]:
        """Get the node battery status."""
        regdesc = self.regmap[Reg.BATTERY_STATUS]
        result = await self.client.get_register(regdesc, self.slave_id)
        available = result.value != 0xFFFF
        low = False
        if available:
            low = result.value != 0
        status = BatteryStatus(available, low)
        return Result(status, result.status)

    async def node_fault_status(self) -> Result[FaultStatus]:
        """Get the node fault status."""
        result = await self.client.get_register(self.regmap[Reg.FAULT_STATUS], self.slave_id)
        available = result.value != 0xFFFF
        fault = result.value != 0
        return Result(FaultStatus(available=available, fault=fault), result.status)

    async def node_clear_rf_stats(self) -> bool:
        """Clears the node RF stats."""
        return await self.client.set_register(self.regmap[Reg.RF_STATS_INDEX], 255, self.slave_id)

    async def node_rf_stats(self) -> RFStats:
        """Get the node RF stats."""
        r = await self.client.get_register(self.regmap[Reg.RF_STATS_LENGTH], self.slave_id)
        nrecs = r.value
        recs: list[RFStats.Record] = []
        for i in range(0, nrecs):
            ok = await self.client.set_register(self.regmap[Reg.RF_STATS_INDEX], i, self.slave_id)
            if not ok:
                _LOGGER.warning("Failed to write %d to RF stats index register", i)
                continue
            r = await self.client.get_register(self.regmap[Reg.RF_STATS_DEVICE], self.slave_id)
            device_id: int = r.value
            r = await self.client.get_register(self.regmap[Reg.RF_STATS_AVERAGE], self.slave_id)
            averate: int = r.value
            r = await self.client.get_register(self.regmap[Reg.RF_STATS_STDDEV], self.slave_id)
            stddev: float = r.value
            r = await self.client.get_register(self.regmap[Reg.RF_STATS_MIN], self.slave_id)
            minimum: int = r.value
            r = await self.client.get_register(self.regmap[Reg.RF_STATS_MAX], self.slave_id)
            maximum: int = r.value
            r = await self.client.get_register(self.regmap[Reg.RF_STATS_MISSED], self.slave_id)
            missed: int = r.value
            r = await self.client.get_register(self.regmap[Reg.RF_STATS_RECEIVED], self.slave_id)
            received: int = r.value
            r = await self.client.get_register(self.regmap[Reg.RF_STATS_AGE], self.slave_id)
            age = datetime.timedelta(minutes=r.value)
            rec = RFStats.Record(
                device_id=device_id,
                averate=averate,
                stddev=stddev,
                minimum=minimum,
                maximum=maximum,
                missed=missed,
                received=received,
                age=age,
            )
            recs.append(rec)
        return RFStats(records=recs)

    async def _safe_fetch(self, fetcher: Callable):
        try:
            result = await fetcher()
        except AiriosException:
            return None
        return result

    async def fetch_node(self) -> AiriosNodeData:  # pylint: disable=duplicate-code
        """Fetch relevant node data at once."""

        return AiriosNodeData(
            slave_id=self.slave_id,
            rf_address=await self._safe_fetch(self.node_rf_address),
            product_id=await self._safe_fetch(self.node_product_id),
            sw_version=await self._safe_fetch(self.node_software_version),
            product_name=await self._safe_fetch(self.node_product_name),
            rf_comm_status=await self._safe_fetch(self.node_rf_comm_status),
            battery_status=await self._safe_fetch(self.node_battery_status),
            fault_status=await self._safe_fetch(self.node_fault_status),
        )
