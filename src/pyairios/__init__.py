"""The Airios RF bridge API entrypoint."""

from .brdg_02r13 import BRDG02R13
from .brdg_02r13 import DEFAULT_SLAVE_ID as BRDG02R13_DEFAULT_SLAVE_ID
from .client import (
    AiriosBaseTransport,
    AsyncAiriosModbusClient,
    AsyncAiriosModbusRtuClient,
    AsyncAiriosModbusTcpClient,
    AiriosRtuTransport,
    AiriosTcpTransport,
)
from .constants import BindingStatus, ProductId
from .data_model import AiriosBoundNodeInfo, AiriosData, AiriosNodeData
from .exceptions import AiriosException
from .node import AiriosNode
from .vmd_02rps78 import VMD02RPS78
from .vmn_05lm02 import VMN05LM02


class Airios:
    """The Airios RF bridge API."""

    bridge: BRDG02R13

    def __init__(
        self, transport: AiriosBaseTransport, slave_id: int = BRDG02R13_DEFAULT_SLAVE_ID
    ) -> None:
        """Initialize the API instance."""
        client: AsyncAiriosModbusClient | None = None
        if isinstance(transport, AiriosTcpTransport):
            transport.__class__ = AiriosTcpTransport
            client = AsyncAiriosModbusTcpClient(transport)
        elif isinstance(transport, AiriosRtuTransport):
            transport.__class__ = AiriosRtuTransport
            client = AsyncAiriosModbusRtuClient(transport)
        else:
            raise AiriosException(f"Unknown trasport {transport}")
        self.bridge = BRDG02R13(slave_id, client)

    async def nodes(self) -> list[AiriosBoundNodeInfo]:
        """Get the list of bound nodes."""
        return await self.bridge.nodes()

    async def node(self, slave_id: int) -> AiriosNode:
        """Get a node intance by its Modbus slave ID."""
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

        for node in await self.bridge.nodes():
            if node.product_id == ProductId.VMD_02RPS78:
                vmd = VMD02RPS78(node.slave_id, self.bridge.client)
                vmd_data = await vmd.fetch_vmd_data()
                data[node.slave_id] = vmd_data
            if node.product_id == ProductId.VMN_05LM02:
                vmn = VMN05LM02(node.slave_id, self.bridge.client)
                vmn_data = await vmn.fetch_vmn_data()
                data[node.slave_id] = vmn_data

        return AiriosData(bridge_rf_address=bridge_rf_address, nodes=data)
