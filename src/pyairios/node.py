"""RF node implementation."""

import logging
import datetime
from enum import auto
from typing import List

from pyairios.client import AsyncAiriosModbusClient
from pyairios.constants import ProductId
from pyairios.device import AiriosDevice
from pyairios.properties import AiriosBaseProperty
from pyairios.properties import AiriosNodeProperty as np
from pyairios.registers import (
    I16Register,
    RegisterAccess,
    RegisterBase,
    Result,
    U8Register,
    U16Register,
    U32Register,
)

LOGGER = logging.getLogger(__name__)


class PrivProp(AiriosBaseProperty):
    """Private properties, not exposed to external API."""

    FAULT_HISTORY_INDEX = auto()
    FAULT_HISTORY_LENGTH = auto()
    FAULT_HISTORY_TIMESTAMP = auto()
    FAULT_HISTORY_FAULTCODE = auto()
    FAULT_HISTORY_STATUS_INFO = auto()
    FAULT_HISTORY_COMM_STATUS = auto()


def datetime_register(value: int) -> datetime.datetime:
    """Decode register bytes to value."""
    if value == 0xFFFFFFFF:
        raise ValueError("Unknown")
    return datetime.datetime.fromtimestamp(value, tz=datetime.timezone.utc)


class AiriosNode(AiriosDevice):
    """Represents a RF node."""

    def __init__(self, device_id: int, client: AsyncAiriosModbusClient) -> None:
        """Initialize the node class instance."""
        super().__init__(device_id, client)
        node_registers: List[RegisterBase] = [
            U32Register(np.RECEIVED_PRODUCT_ID, 40021, RegisterAccess.READ, result_type=ProductId),
            U16Register(np.VALUE_ERROR_STATUS, 40104, RegisterAccess.READ),
            I16Register(np.RF_LAST_RSSI, 40109, RegisterAccess.READ),
            U8Register(np.BOUND_STATUS, 40110, RegisterAccess.READ),
            U16Register(
                PrivProp.FAULT_HISTORY_INDEX,
                40300,
                RegisterAccess.READ | RegisterAccess.WRITE,
            ),
            U16Register(
                PrivProp.FAULT_HISTORY_LENGTH,
                40301,
                RegisterAccess.READ | RegisterAccess.WRITE,
            ),
            U32Register(
                PrivProp.FAULT_HISTORY_TIMESTAMP,
                40302,
                RegisterAccess.READ,
                result_adapter=datetime_register,
            ),
            U16Register(PrivProp.FAULT_HISTORY_FAULTCODE, 40304, RegisterAccess.READ),
            U32Register(PrivProp.FAULT_HISTORY_STATUS_INFO, 40305, RegisterAccess.READ),
            U16Register(PrivProp.FAULT_HISTORY_COMM_STATUS, 40307, RegisterAccess.READ),
        ]
        self._add_registers(node_registers)

    async def node_received_product_id(self) -> Result[ProductId]:
        """Get the received product ID.

        This is the value received from the bound node. If it does not match register
        NODE_PRODUCT_ID a wrong product is bound.
        """
        result = await self.client.get_register(self.regmap[np.RECEIVED_PRODUCT_ID], self.device_id)
        return Result(ProductId(result.value), result.status)
