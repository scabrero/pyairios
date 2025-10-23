"""Airios device base class."""

from __future__ import annotations

import datetime
import logging
import struct
from enum import auto
from typing import Any, Dict, List

from pyairios.client import AsyncAiriosModbusClient
from pyairios.constants import BatteryStatus, FaultStatus, ProductId, RFCommStatus, RFStats
from pyairios.data_model import AiriosDeviceData
from pyairios.exceptions import AiriosAcknowledgeException, AiriosPropertyNotSupported
from pyairios.properties import AiriosBaseProperty
from pyairios.properties import AiriosDeviceProperty as dp
from pyairios.registers import (
    FloatRegister,
    RegisterAccess,
    RegisterBase,
    Result,
    StringRegister,
    U16Register,
    U32Register,
)

LOGGER = logging.getLogger(__name__)


class PrivProp(AiriosBaseProperty):
    """Private properties, not exposed to external API."""

    RF_STATS_INDEX = auto()
    RF_STATS_LENGTH = auto()
    RF_STATS_DEVICE = auto()
    RF_STATS_AVERAGE = auto()
    RF_STATS_STDDEV = auto()
    RF_STATS_MIN = auto()
    RF_STATS_MAX = auto()
    RF_STATS_MISSED = auto()
    RF_STATS_RECEIVED = auto()
    RF_STATS_AGE = auto()


def battery_status(value: Any) -> BatteryStatus:
    """Get the node battery status."""
    available = value != 0xFFFF
    low = False
    if available:
        low = value != 0
    return BatteryStatus(available, low)


def fault_status(value: Any) -> FaultStatus:
    """Get the node fault status."""
    available = value != 0xFFFF
    fault = value != 0
    return FaultStatus(available=available, fault=fault)


def date_register(value: int) -> datetime.date:
    """Decode register bytes to value."""
    if value == 0xFFFFFFFF:
        raise ValueError("Unknown")
    buf = value.to_bytes(4, "big")
    (day, month, year) = struct.unpack(">BBH", buf)
    return datetime.date(year, month, day)


class AiriosDevice:
    """Airios device base class."""

    client: AsyncAiriosModbusClient
    device_id: int
    registers: List[RegisterBase]
    regmap: Dict[AiriosBaseProperty, RegisterBase]

    def __init__(self, device_id: int, client: AsyncAiriosModbusClient) -> None:
        """Initialize the class instance."""
        self.client = client
        self.device_id = int(device_id)
        self.registers = []
        self.regmap = {}

        dev_registers: List[RegisterBase] = [
            U32Register(dp.RF_ADDRESS, 40000, RegisterAccess.READ),
            U32Register(dp.PRODUCT_ID, 40002, RegisterAccess.READ, result_type=ProductId),
            U16Register(dp.SOFTWARE_VERSION, 40004, RegisterAccess.READ),
            U16Register(dp.OEM_NUMBER, 40005, RegisterAccess.READ),
            U16Register(dp.RF_CAPABILITIES, 40006, RegisterAccess.READ),
            U32Register(
                dp.MANUFACTURE_DATE,
                40007,
                RegisterAccess.READ,
                result_adapter=date_register,
            ),
            U32Register(
                dp.SOFTWARE_BUILD_DATE,
                40009,
                RegisterAccess.READ,
                result_adapter=date_register,
            ),
            StringRegister(dp.PRODUCT_NAME, 40011, 10, RegisterAccess.READ),
            U16Register(dp.RF_LAST_SEEN, 40100, RegisterAccess.READ),
            U16Register(dp.RF_COMM_STATUS, 40101, RegisterAccess.READ, result_type=RFCommStatus),
            U16Register(
                dp.BATTERY_STATUS,
                40102,
                RegisterAccess.READ,
                result_adapter=battery_status,
            ),
            U16Register(
                dp.FAULT_STATUS,
                40103,
                RegisterAccess.READ,
                result_adapter=fault_status,
            ),
            U16Register(PrivProp.RF_STATS_INDEX, 40120, RegisterAccess.READ | RegisterAccess.WRITE),
            U16Register(PrivProp.RF_STATS_LENGTH, 40121, RegisterAccess.READ),
            U32Register(PrivProp.RF_STATS_DEVICE, 40122, RegisterAccess.READ),
            U16Register(PrivProp.RF_STATS_AVERAGE, 40124, RegisterAccess.READ),
            FloatRegister(PrivProp.RF_STATS_STDDEV, 40125, RegisterAccess.READ),
            U16Register(PrivProp.RF_STATS_MIN, 40127, RegisterAccess.READ),
            U16Register(PrivProp.RF_STATS_MAX, 40128, RegisterAccess.READ),
            U16Register(PrivProp.RF_STATS_MISSED, 40129, RegisterAccess.READ),
            U16Register(PrivProp.RF_STATS_RECEIVED, 40130, RegisterAccess.READ),
            U16Register(PrivProp.RF_STATS_AGE, 40131, RegisterAccess.READ),
        ]
        self._add_registers(dev_registers)

    def _add_registers(self, reglist: List[RegisterBase]):
        self.registers.extend(reglist)
        self.registers.sort(key=lambda x: x.description.address)
        self.regmap: Dict[AiriosBaseProperty, RegisterBase] = {
            regdesc.aproperty: regdesc for regdesc in self.registers
        }

    async def get(self, ap: AiriosBaseProperty) -> Any:
        """Get an Airios property."""
        if ap not in self.regmap:
            raise AiriosPropertyNotSupported(ap)
        regdesc = self.regmap[ap]
        return await self.client.get_register(regdesc, self.device_id)

    async def set(self, ap: AiriosBaseProperty, value: Any) -> bool:
        """Set an Airios property."""
        if ap not in self.regmap:
            raise AiriosPropertyNotSupported(ap)
        regdesc = self.regmap[ap]
        return await self.client.set_register(regdesc, value, self.device_id)

    async def fetch(self, *, all_props=True, with_status=True) -> AiriosDeviceData:
        """Fetch all data."""
        data: Dict[AiriosBaseProperty, Any] = {}

        if not with_status:
            it = filter(lambda x: RegisterAccess.READ in x.description.access, self.registers)
            rl = list(it)
            data = await self.client.get_multiple(rl, self.device_id)
        else:
            for reg in self.registers:
                if RegisterAccess.READ not in reg.description.access:
                    continue

                try:
                    data[reg.aproperty] = await self.client.get_register(reg, self.device_id)
                except AiriosAcknowledgeException as ex:
                    msg = f"Failed to fetch register {reg.aproperty}: {ex}"
                    LOGGER.info(msg)
                    continue
                except ValueError as ex:
                    msg = f"Failed to fetch register {reg.aproperty}: {ex}"
                    LOGGER.info(msg)
                    continue

        if not all_props:
            return data

        for ap in list(set(self.regmap.keys()) - set(data.keys())):
            # These are the properties not updated maybe due to Modbus Ack error.
            data[ap] = Result(None, None)

        return data

    async def device_rf_address(self) -> Result[int]:
        """Get the device RF address, also used as node serial number."""
        return await self.client.get_register(self.regmap[dp.RF_ADDRESS], self.device_id)

    async def device_product_id(self) -> Result[ProductId]:
        """Get the device product ID.

        This is the value assigned to the virtual device instance created by the bridge when
        a device is bound. The actual received product ID from the real RF device can is
        available in the RECEIVED_PRODUCT_ID register.
        """
        result = await self.client.get_register(self.regmap[dp.PRODUCT_ID], self.device_id)
        return Result(ProductId(result.value), None)

    async def device_software_version(self) -> Result[int]:
        """Get the device software version."""
        return await self.client.get_register(self.regmap[dp.SOFTWARE_VERSION], self.device_id)

    async def device_oem_number(self) -> Result[int]:
        """Get the device OEM number.

        It is 0x00 or 0xFF when not used.
        """
        return await self.client.get_register(self.regmap[dp.OEM_NUMBER], self.device_id)

    async def device_rf_capabilities(self) -> Result[int]:
        """Get the device RF capabilities.

        The value depends on the specific device.
        """
        return await self.client.get_register(self.regmap[dp.RF_CAPABILITIES], self.device_id)

    async def device_manufacture_date(self) -> Result[datetime.date]:
        """Get the device manufacture date."""
        return await self.client.get_register(self.regmap[dp.MANUFACTURE_DATE], self.device_id)

    async def device_software_build_date(self) -> Result[datetime.date]:
        """Get the device software build date."""
        return await self.client.get_register(self.regmap[dp.SOFTWARE_BUILD_DATE], self.device_id)

    async def device_product_name(self) -> Result[str]:
        """Get the device product name."""
        return await self.client.get_register(self.regmap[dp.PRODUCT_NAME], self.device_id)

    async def device_rf_comm_status(self) -> Result[RFCommStatus]:
        """Get the device RF communication status."""
        return await self.client.get_register(self.regmap[dp.RF_COMM_STATUS], self.device_id)

    async def device_battery_status(self) -> Result[BatteryStatus]:
        """Get the device battery status."""
        regdesc = self.regmap[dp.BATTERY_STATUS]
        result = await self.client.get_register(regdesc, self.device_id)
        available = result.value != 0xFFFF
        low = False
        if available:
            low = result.value != 0
        status = BatteryStatus(available, low)
        return Result(status, result.status)

    async def device_fault_status(self) -> Result[FaultStatus]:
        """Get the device fault status."""
        result = await self.client.get_register(self.regmap[dp.FAULT_STATUS], self.device_id)
        available = result.value != 0xFFFF
        fault = result.value != 0
        return Result(FaultStatus(available=available, fault=fault), result.status)

    async def device_clear_rf_stats(self) -> bool:
        """Clears the node RF stats."""
        return await self.client.set_register(
            self.regmap[PrivProp.RF_STATS_INDEX], 255, self.device_id
        )

    async def device_rf_stats(self) -> RFStats:
        """Get the node RF stats."""
        r = await self.client.get_register(self.regmap[PrivProp.RF_STATS_LENGTH], self.device_id)
        nrecs = r.value
        recs: list[RFStats.Record] = []
        for i in range(0, nrecs):
            ok = await self.client.set_register(
                self.regmap[PrivProp.RF_STATS_INDEX], i, self.device_id
            )
            if not ok:
                LOGGER.warning("Failed to write %d to RF stats index register", i)
                continue
            r = await self.client.get_register(
                self.regmap[PrivProp.RF_STATS_DEVICE], self.device_id
            )
            device_id: int = r.value
            r = await self.client.get_register(
                self.regmap[PrivProp.RF_STATS_AVERAGE], self.device_id
            )
            averate: int = r.value
            r = await self.client.get_register(
                self.regmap[PrivProp.RF_STATS_STDDEV], self.device_id
            )
            stddev: float = r.value
            r = await self.client.get_register(self.regmap[PrivProp.RF_STATS_MIN], self.device_id)
            minimum: int = r.value
            r = await self.client.get_register(self.regmap[PrivProp.RF_STATS_MAX], self.device_id)
            maximum: int = r.value
            r = await self.client.get_register(
                self.regmap[PrivProp.RF_STATS_MISSED], self.device_id
            )
            missed: int = r.value
            r = await self.client.get_register(
                self.regmap[PrivProp.RF_STATS_RECEIVED], self.device_id
            )
            received: int = r.value
            r = await self.client.get_register(self.regmap[PrivProp.RF_STATS_AGE], self.device_id)
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
