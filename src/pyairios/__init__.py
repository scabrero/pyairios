"""The Airios RF bridge API entrypoint."""

import logging

from pyairios.client import (
    AiriosBaseTransport,
    AiriosRtuTransport,
    AiriosTcpTransport,
    AsyncAiriosModbusClient,
    AsyncAiriosModbusRtuClient,
    AsyncAiriosModbusTcpClient,
)
from pyairios.constants import BindingStatus, ProductId
from pyairios.data_model import AiriosBoundNodeInfo, AiriosData, AiriosDeviceData
from pyairios.device import AiriosDevice
from pyairios.exceptions import AiriosException
from pyairios.models.brdg_02r13 import BRDG02R13
from pyairios.models.brdg_02r13 import DEFAULT_DEVICE_ID as BRDG02R13_DEFAULT_DEVICE_ID
from pyairios.models.factory import factory
from pyairios.properties import AiriosBridgeProperty as bp

LOGGER = logging.getLogger(__name__)


class Airios:
    """The Airios RF bridge API."""

    _client: AsyncAiriosModbusClient
    bridge: BRDG02R13

    def __init__(
        self, transport: AiriosBaseTransport, device_id: int = BRDG02R13_DEFAULT_DEVICE_ID
    ) -> None:
        """Initialize the API instance."""
        if isinstance(transport, AiriosTcpTransport):
            transport.__class__ = AiriosTcpTransport
            self._client = AsyncAiriosModbusTcpClient(transport)
        elif isinstance(transport, AiriosRtuTransport):
            transport.__class__ = AiriosRtuTransport
            self._client = AsyncAiriosModbusRtuClient(transport)
        else:
            raise AiriosException(f"Unknown transport {transport}")
        self.bridge = BRDG02R13(device_id, self._client)

    async def nodes(self) -> list[AiriosBoundNodeInfo]:
        """Get the list of bound nodes."""
        return await self.bridge.nodes()

    async def node(self, device_id: int) -> AiriosDevice:
        """Get a node instance by its Modbus device ID."""
        return await self.bridge.node(device_id)

    async def bind_status(self) -> BindingStatus:
        """Get the bind status."""
        return await self.bridge.get(bp.ACTUAL_BINDING_STATUS)

    async def bind_controller(
        self,
        device_id: int,
        product_id: ProductId,
        product_serial: int | None = None,
    ) -> bool:
        """Bind a new controller to the bridge."""
        return await self.bridge.bind_controller(device_id, product_id, product_serial)

    async def bind_accessory(
        self,
        controller_device_id: int,
        device_id: int,
        product_id: ProductId,
    ) -> bool:
        """Bind a new accessory to the bridge."""
        return await self.bridge.bind_accessory(controller_device_id, device_id, product_id)

    async def unbind(self, device_id: int) -> bool:
        """Remove a bound node from the bridge by its Modbus device ID."""
        return await self.bridge.unbind(device_id)

    async def fetch(self, *, all_props=True, with_status=True) -> AiriosData:
        """Get the data from all nodes at once."""
        data: dict[int, AiriosDeviceData] = {}

        brdg_data = await self.bridge.fetch(all_props=all_props, with_status=with_status)

        for node_info in await self.bridge.nodes():
            node = await factory.get_device_by_product_id(
                node_info.product_id,
                node_info.device_id,
                self.bridge.client,
            )
            data[node_info.device_id] = await node.fetch(
                all_props=all_props, with_status=with_status
            )

        return AiriosData(bridge=brdg_data, nodes=data)

    async def connect(self) -> bool:
        """Establish underlying Modbus connection."""
        return await self._client.connect()

    def close(self) -> None:
        """Close underlying Modbus connection."""
        return self._client.close()
