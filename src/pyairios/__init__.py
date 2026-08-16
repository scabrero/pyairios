"""The Airios RF bridge API entrypoint."""

import logging
from typing import cast

from pyairios.client import (
    AiriosBaseTransport,
    AiriosRtuTransport,
    AiriosTcpTransport,
    AsyncAiriosModbusClient,
    AsyncAiriosModbusRtuClient,
    AsyncAiriosModbusTcpClient,
)
from pyairios.constants import AiriosDeviceType, BindingStatus, ProductId
from pyairios.data_model import AiriosData, AiriosDeviceData
from pyairios.device import AiriosDevice, AiriosBoundDeviceInfo
from pyairios.bridge import AiriosBridge
from pyairios.exceptions import AiriosException, AiriosInvalidArgumentException
from pyairios.models.brdg_02r13 import DEFAULT_DEVICE_ID as BRDG02R13_DEFAULT_DEVICE_ID
from pyairios.models.factory import factory
from pyairios.properties import AiriosBridgeProperty as bp
from pyairios.registers import Result

LOGGER = logging.getLogger(__name__)


class Airios:
    """The Airios RF bridge API."""

    _client: AsyncAiriosModbusClient
    _bridge: AiriosBridge
    _bridge_address: int

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
        self._bridge_address = device_id

    async def bridge(self) -> AiriosBridge:
        """Return cached bridge instance or get one from the factory."""
        if self._bridge:
            return self._bridge
        dev = await factory.get_device(self._bridge_address, self._client)
        if dev.pr_type() != AiriosDeviceType.RF_BRIDGE:
            raise AiriosInvalidArgumentException(
                f"Device at address {self._bridge_address} is not a RF bridge"
            )
        self._bridge = cast(AiriosBridge, dev)
        return self._bridge

    async def nodes(self) -> list[AiriosBoundDeviceInfo]:
        """Get the list of bound nodes."""
        bridge = await self.bridge()
        return await bridge.nodes()

    async def node(self, device_id: int) -> AiriosDevice:
        """Get a node instance by its Modbus device ID."""
        bridge = await self.bridge()
        return await bridge.node(device_id)

    async def bind_status(self) -> Result[BindingStatus]:
        """Get the bind status."""
        bridge = await self.bridge()
        return await bridge.get(bp.ACTUAL_BINDING_STATUS)

    async def bind_controller(
        self,
        device_id: int,
        product_id: ProductId,
        product_serial: int | None = None,
    ) -> bool:
        """Bind a new controller to the bridge."""
        bridge = await self.bridge()
        return await bridge.bind_controller(device_id, product_id, product_serial)

    async def bind_accessory(
        self,
        controller_device_id: int,
        device_id: int,
        product_id: ProductId,
    ) -> bool:
        """Bind a new accessory to the bridge."""
        bridge = await self.bridge()
        return await bridge.bind_accessory(controller_device_id, device_id, product_id)

    async def unbind(self, device_id: int) -> bool:
        """Remove a bound node from the bridge by its Modbus device ID."""
        bridge = await self.bridge()
        return await bridge.unbind(device_id)

    async def fetch(self, *, all_props=True, with_status=True) -> AiriosData:
        """Get the data from all nodes at once."""
        data: dict[int, AiriosDeviceData] = {}

        bridge = await self.bridge()
        brdg_data = await bridge.fetch(all_props=all_props, with_status=with_status)
        data[bridge.device_id] = brdg_data

        for bound in await bridge.nodes():
            dev = await factory.get_device_by_product_id(
                bound.product_id,
                bound.modbus_address,
                bridge.client,
            )
            data[bound.modbus_address] = await dev.fetch(
                all_props=all_props, with_status=with_status
            )

        return AiriosData(bridge_key=bridge.device_id, nodes=data)

    async def connect(self) -> bool:
        """Establish underlying Modbus connection."""
        return await self._client.connect()

    def close(self) -> None:
        """Close underlying Modbus connection."""
        return self._client.close()
