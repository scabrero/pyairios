"""The Airios RF bridge API entrypoint."""

import logging

from pyairios.models.brdg_02r13 import BRDG02R13
from pyairios.models.brdg_02r13 import DEFAULT_SLAVE_ID as BRDG02R13_DEFAULT_SLAVE_ID

from .client import (
    AiriosBaseTransport,
    AiriosRtuTransport,
    AiriosTcpTransport,
    AsyncAiriosModbusClient,
    AsyncAiriosModbusRtuClient,
    AsyncAiriosModbusTcpClient,
)
from .constants import BindingStatus, ProductId
from .data_model import AiriosBoundNodeInfo, AiriosData, AiriosNodeData
from .exceptions import AiriosException
from .node import AiriosNode

LOGGER = logging.getLogger(__name__)


class Airios:
    """The Airios RF bridge API."""

    _client: AsyncAiriosModbusClient
    bridge: BRDG02R13

    def __init__(
        self, transport: AiriosBaseTransport, slave_id: int = BRDG02R13_DEFAULT_SLAVE_ID
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
        self.bridge = BRDG02R13(slave_id, self._client)

    def get_product_ids(self) -> dict[str, str]:
        """Get the dict of installed product_ids."""
        return self.bridge.get_product_ids()

    async def nodes(self) -> list[AiriosBoundNodeInfo]:
        """Get the list of bound nodes."""
        return await self.bridge.nodes()

    async def node(self, slave_id: int) -> AiriosNode:
        """Get a node instance by its Modbus slave ID."""
        return await self.bridge.node(slave_id)

    async def bind_status(self) -> BindingStatus:
        """Get the bind status."""
        return await self.bridge.bind_status()

    async def bind_controller(
        self,
        slave_id: int,
        product_id: ProductId,
        product_serial: int | None = None,
    ) -> bool:
        """Bind a new controller to the bridge."""
        return await self.bridge.bind_controller(slave_id, product_id, product_serial)

    async def bind_accessory(
        self,
        controller_slave_id: int,
        slave_id: int,
        product_id: ProductId,
    ) -> bool:
        """Bind a new accessory to the bridge."""
        return await self.bridge.bind_accessory(controller_slave_id, slave_id, product_id)

    async def unbind(self, slave_id: int) -> bool:
        """Remove a bound node from the bridge by its Modbus slave ID."""
        return await self.bridge.unbind(slave_id)

    async def fetch(self) -> AiriosData:
        """Get the data from all nodes at once."""
        data: dict[int, AiriosNodeData] = {}

        brdg_data = await self.bridge.fetch_bridge()
        if brdg_data["rf_address"] is None:
            raise AiriosException("Failed to fetch node RF address")
        bridge_rf_address = brdg_data["rf_address"].value
        data[self.bridge.slave_id] = brdg_data

        for _node in await self.bridge.nodes():  # this info is in the model class files
            # lookup node model family by key # compare to cli.py
            for key, _id in self.bridge.get_product_ids():  # index of ids by model_key (names)
                if _node.product_id == _id:
                    LOGGER.debug(f"Start matching init for: {key}")
                    if key.startswith("VMD"):
                        # this is only necessary because every "family" has a different node class name
                        # TODO refactor by renaming every node class the same?
                        vmd = self.bridge.modules[key].VmdNode(_node.slave_id, self.bridge.client)
                        vmd_data = await vmd.fetch_vmd_data()
                        data[_node.slave_id] = vmd_data
                    if key.startswith("VMN"):
                        vmn = self.bridge.modules[key].VmnNode(_node.slave_id, self.bridge.client)
                        vmn_data = await vmn.fetch_vmn_data()
                        data[_node.slave_id] = vmn_data
                    # new Airios 'families' would be added to this filter

        return AiriosData(bridge_rf_address=bridge_rf_address, nodes=data)

    async def connect(self) -> bool:
        """Establish underlying Modbus connection."""
        return await self._client.connect()

    def close(self) -> None:
        """Close underlying Modbus connection."""
        return self._client.close()
