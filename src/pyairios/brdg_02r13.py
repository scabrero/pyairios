"""Airios BRDG-02R13 RF bridge implementation."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List

from .client import AsyncAiriosModbusClient
from .constants import (
    Baudrate,
    BindingMode,
    BindingStatus,
    ModbusEvents,
    Parity,
    ProductId,
    ResetMode,
    StopBits,
)
from .data_model import AiriosBoundNodeInfo, BRDG02R13Data
from .exceptions import (
    AiriosBindingException,
    AiriosException,
    AiriosInvalidArgumentException,
)
from .node import AiriosNode
from .node import Reg as NodeReg
from .registers import (
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
from .vmd_02rps78 import VMD02RPS78
from .vmn_05lm02 import VMN05LM02

DEFAULT_SLAVE_ID = 207

_LOGGER = logging.getLogger(__name__)


@dataclass
class RFLoad:
    """RF load."""

    load_current_hour: float
    """The RF load in the current hour (%)."""
    load_last_hour: float
    """The RF load in the last hour (%)."""


@dataclass
class RFSentMessages:
    """RF sent messages."""

    messages_current_hour: int
    """Messages sent in the current hour."""
    messages_last_hour: int
    """Messages sent in the last hour."""


@dataclass
class SerialConfig:
    """Serial config."""

    baudrate: Baudrate
    stop_bits: StopBits
    parity: Parity


class Reg(RegisterAddress):
    """Register set for BRDG-02R13 RF bridge."""

    CUSTOMER_PRODUCT_ID = 40023
    UTC_TIME = 41015
    LOCAL_TIME = 41017
    UPTIME = 41019
    DAYLIGHT_SAVING_TYPE = 41021
    TIMEZONE_OFFSET = 41022
    OEM_CODE = 41101
    MODBUS_EVENTS = 41103
    RESET_DEVICE = 41107
    CUSTOMER_SPECIFIC_NODE_ID = 41108
    SERIAL_PARITY = 41998
    SERIAL_STOP_BITS = 41999
    SERIAL_BAUDRATE = 42000
    SLAVE_ADDRESS = 42001
    MESSAGES_SEND_CURRENT_HOUR = 42100
    MESSAGES_SEND_LAST_HOUR = 42101
    RF_LOAD_CURRENT_HOUR = 42102
    RF_LOAD_LAST_HOUR = 42104
    BINDING_PRODUCT_ID = 43000
    BINDING_PRODUCT_SERIAL = 43002
    BINDING_COMMAND = 43004
    CREATE_NODE = 43005
    FIRST_ADDRESS_TO_ASSIGN = 43006
    REMOVE_NODE = 43399
    ACTUAL_BINDING_STATUS = 43900
    NUMBER_OF_NODES = 43901
    ADDRESS_NODE_1 = 43902
    ADDRESS_NODE_2 = 43903
    ADDRESS_NODE_3 = 43904
    ADDRESS_NODE_4 = 43905
    ADDRESS_NODE_5 = 43906
    ADDRESS_NODE_6 = 43907
    ADDRESS_NODE_7 = 43908
    ADDRESS_NODE_8 = 43909
    ADDRESS_NODE_9 = 43910
    ADDRESS_NODE_10 = 43911
    ADDRESS_NODE_11 = 43912
    ADDRESS_NODE_12 = 43913
    ADDRESS_NODE_13 = 43914
    ADDRESS_NODE_14 = 43915
    ADDRESS_NODE_15 = 43916
    ADDRESS_NODE_16 = 43917
    ADDRESS_NODE_17 = 43918
    ADDRESS_NODE_18 = 43919
    ADDRESS_NODE_19 = 43920
    ADDRESS_NODE_20 = 43921
    ADDRESS_NODE_21 = 43922
    ADDRESS_NODE_22 = 43923
    ADDRESS_NODE_23 = 43924
    ADDRESS_NODE_24 = 43925
    ADDRESS_NODE_25 = 43926
    ADDRESS_NODE_26 = 43927
    ADDRESS_NODE_27 = 43928
    ADDRESS_NODE_28 = 43929
    ADDRESS_NODE_29 = 43930
    ADDRESS_NODE_30 = 43931
    ADDRESS_NODE_31 = 43932
    ADDRESS_NODE_32 = 43933


class BRDG02R13(AiriosNode):
    """Represents a BRDG-02R13 RF bridge."""

    def __init__(self, slave_id: int, client: AsyncAiriosModbusClient) -> None:
        """Initialize the BRDG-02R13 RF bridge instance."""

        super().__init__(slave_id, client)
        brdg_registers: List[RegisterBase] = [
            U16Register(Reg.CUSTOMER_PRODUCT_ID, RegisterAccess.READ | RegisterAccess.WRITE),
            DateTimeRegister(Reg.UTC_TIME, RegisterAccess.READ | RegisterAccess.WRITE),
            DateTimeRegister(Reg.LOCAL_TIME, RegisterAccess.READ),
            U32Register(Reg.UPTIME, RegisterAccess.READ),
            U16Register(Reg.DAYLIGHT_SAVING_TYPE, RegisterAccess.READ | RegisterAccess.WRITE),
            U16Register(Reg.TIMEZONE_OFFSET, RegisterAccess.READ | RegisterAccess.WRITE),
            U16Register(Reg.OEM_CODE, RegisterAccess.READ | RegisterAccess.WRITE),
            U16Register(Reg.MODBUS_EVENTS, RegisterAccess.READ | RegisterAccess.WRITE),
            U16Register(Reg.RESET_DEVICE, RegisterAccess.WRITE),
            StringRegister(Reg.CUSTOMER_SPECIFIC_NODE_ID, 10, RegisterAccess.WRITE),
            U16Register(Reg.SERIAL_PARITY, RegisterAccess.READ | RegisterAccess.WRITE),
            U16Register(Reg.SERIAL_STOP_BITS, RegisterAccess.READ | RegisterAccess.WRITE),
            U16Register(Reg.SERIAL_BAUDRATE, RegisterAccess.READ | RegisterAccess.WRITE),
            U16Register(Reg.SLAVE_ADDRESS, RegisterAccess.READ | RegisterAccess.WRITE),
            U16Register(Reg.MESSAGES_SEND_CURRENT_HOUR, RegisterAccess.READ),
            U16Register(Reg.MESSAGES_SEND_LAST_HOUR, RegisterAccess.READ),
            FloatRegister(Reg.RF_LOAD_CURRENT_HOUR, RegisterAccess.READ),
            FloatRegister(Reg.RF_LOAD_LAST_HOUR, RegisterAccess.READ),
            U32Register(Reg.BINDING_PRODUCT_ID, RegisterAccess.READ | RegisterAccess.WRITE),
            U32Register(Reg.BINDING_PRODUCT_SERIAL, RegisterAccess.READ | RegisterAccess.WRITE),
            U16Register(Reg.BINDING_COMMAND, RegisterAccess.WRITE),
            U16Register(Reg.CREATE_NODE, RegisterAccess.WRITE),
            U16Register(Reg.FIRST_ADDRESS_TO_ASSIGN, RegisterAccess.READ | RegisterAccess.WRITE),
            U16Register(Reg.REMOVE_NODE, RegisterAccess.WRITE),
            U16Register(Reg.ACTUAL_BINDING_STATUS, RegisterAccess.READ),
            U16Register(Reg.NUMBER_OF_NODES, RegisterAccess.READ),
            U16Register(Reg.ADDRESS_NODE_1, RegisterAccess.READ),
            U16Register(Reg.ADDRESS_NODE_2, RegisterAccess.READ),
            U16Register(Reg.ADDRESS_NODE_3, RegisterAccess.READ),
            U16Register(Reg.ADDRESS_NODE_4, RegisterAccess.READ),
            U16Register(Reg.ADDRESS_NODE_5, RegisterAccess.READ),
            U16Register(Reg.ADDRESS_NODE_6, RegisterAccess.READ),
            U16Register(Reg.ADDRESS_NODE_7, RegisterAccess.READ),
            U16Register(Reg.ADDRESS_NODE_8, RegisterAccess.READ),
            U16Register(Reg.ADDRESS_NODE_9, RegisterAccess.READ),
            U16Register(Reg.ADDRESS_NODE_10, RegisterAccess.READ),
            U16Register(Reg.ADDRESS_NODE_11, RegisterAccess.READ),
            U16Register(Reg.ADDRESS_NODE_12, RegisterAccess.READ),
            U16Register(Reg.ADDRESS_NODE_13, RegisterAccess.READ),
            U16Register(Reg.ADDRESS_NODE_14, RegisterAccess.READ),
            U16Register(Reg.ADDRESS_NODE_15, RegisterAccess.READ),
            U16Register(Reg.ADDRESS_NODE_16, RegisterAccess.READ),
            U16Register(Reg.ADDRESS_NODE_17, RegisterAccess.READ),
            U16Register(Reg.ADDRESS_NODE_18, RegisterAccess.READ),
            U16Register(Reg.ADDRESS_NODE_19, RegisterAccess.READ),
            U16Register(Reg.ADDRESS_NODE_20, RegisterAccess.READ),
            U16Register(Reg.ADDRESS_NODE_21, RegisterAccess.READ),
            U16Register(Reg.ADDRESS_NODE_22, RegisterAccess.READ),
            U16Register(Reg.ADDRESS_NODE_23, RegisterAccess.READ),
            U16Register(Reg.ADDRESS_NODE_24, RegisterAccess.READ),
            U16Register(Reg.ADDRESS_NODE_25, RegisterAccess.READ),
            U16Register(Reg.ADDRESS_NODE_26, RegisterAccess.READ),
            U16Register(Reg.ADDRESS_NODE_27, RegisterAccess.READ),
            U16Register(Reg.ADDRESS_NODE_28, RegisterAccess.READ),
            U16Register(Reg.ADDRESS_NODE_29, RegisterAccess.READ),
            U16Register(Reg.ADDRESS_NODE_30, RegisterAccess.READ),
            U16Register(Reg.ADDRESS_NODE_31, RegisterAccess.READ),
            U16Register(Reg.ADDRESS_NODE_32, RegisterAccess.READ),
        ]
        self._add_registers(brdg_registers)

    def __str__(self) -> str:
        return f"BRDG-02R13@{self.slave_id}"

    async def bind_controller(
        self,
        slave_id: int,
        product_id: ProductId,
        product_serial: int | None = None,
    ) -> bool:
        """Bind a new controller to the bridge."""
        if slave_id < 2 or slave_id > 247:
            raise AiriosInvalidArgumentException(
                f"Modbus slave address {slave_id} out of range 2-247"
            )

        if slave_id == self.slave_id:
            raise AiriosInvalidArgumentException(f"Modbus slave address {slave_id} already in use")

        mode = BindingMode.ABORT
        ok = await self.client.set_register(self.regmap[Reg.BINDING_COMMAND], mode, self.slave_id)
        if not ok:
            raise AiriosBindingException("Failed to reset binding status")

        result = await self.client.get_register(
            self.regmap[Reg.ACTUAL_BINDING_STATUS], self.slave_id
        )
        if result is None or result.value is None:
            raise AiriosBindingException("Failed to determine current binding status")
        if result.value != 0:
            raise AiriosBindingException(f"Bridge not ready for binding: {result.value}")

        mode = BindingMode.OUTGOING_SINGLE_PRODUCT
        if product_serial is not None:
            mode = BindingMode.OUTGOING_SINGLE_PRODUCT_PLUS_SERIAL

        ok = await self.client.set_register(
            self.regmap[Reg.BINDING_PRODUCT_ID], product_id, self.slave_id
        )
        if not ok:
            raise AiriosBindingException("Failed to configure binding product ID")

        ok = await self.client.set_register(self.regmap[Reg.CREATE_NODE], slave_id, self.slave_id)
        if not ok:
            raise AiriosBindingException(f"Failed to create node for slave id {slave_id}")

        if product_serial is not None:
            ok = await self.client.set_register(
                self.regmap[Reg.BINDING_PRODUCT_SERIAL], product_serial, self.slave_id
            )
            if not ok:
                raise AiriosBindingException("Failed to configure binding product serial")

        value = ((slave_id & 0xFF) << 8) | mode
        return await self.client.set_register(
            self.regmap[Reg.BINDING_COMMAND], value, self.slave_id
        )

    async def bind_status(self) -> BindingStatus:
        """Get the bind status."""
        result = await self.client.get_register(
            self.regmap[Reg.ACTUAL_BINDING_STATUS], self.slave_id
        )
        if result is None or result.value is None:
            return BindingStatus.NOT_AVAILABLE
        return BindingStatus(result.value)

    async def unbind(self, slave_id: int) -> bool:
        """Remove a bound node from the bridge by its Modbus slave ID."""
        return await self.client.set_register(self.regmap[Reg.REMOVE_NODE], slave_id, self.slave_id)

    async def bind_accessory(
        self,
        controller_slave_id: int,
        slave_id: int,
        product_id: ProductId,
    ) -> bool:
        """Bind a new accessory to the bridge."""
        if controller_slave_id < 2 or controller_slave_id > 247:
            raise AiriosInvalidArgumentException(
                f"Modbus slave address {controller_slave_id} out of range 2-247"
            )

        if slave_id < 2 or slave_id > 247:
            raise AiriosInvalidArgumentException(
                f"Modbus slave address {slave_id} out of range 2-247"
            )

        if slave_id == self.slave_id:
            raise AiriosInvalidArgumentException(f"Modbus slave address {slave_id} already in use")

        mode: BindingMode = BindingMode.ABORT
        ok = await self.client.set_register(self.regmap[Reg.BINDING_COMMAND], mode, self.slave_id)
        if not ok:
            raise AiriosBindingException("Failed to reset binding status")

        result = await self.client.get_register(
            self.regmap[Reg.ACTUAL_BINDING_STATUS], self.slave_id
        )
        if result is None or result.value is None:
            raise AiriosBindingException("Failed to determine current binding status")
        if result.value != 0:
            raise AiriosBindingException(f"Bridge not ready for binding: {result.value}")

        ok = await self.client.set_register(
            self.regmap[Reg.BINDING_PRODUCT_ID], product_id, self.slave_id
        )
        if not ok:
            raise AiriosBindingException("Failed to configure binding product ID")

        ok = await self.client.set_register(self.regmap[Reg.CREATE_NODE], slave_id, self.slave_id)
        if not ok:
            raise AiriosBindingException(f"Failed to create node for slave id {slave_id}")

        mode = BindingMode.INCOMING_ON_EXISTING_NODE
        value = ((slave_id & 0xFF) << 8) | mode
        return await self.client.set_register(
            self.regmap[Reg.BINDING_COMMAND], value, self.slave_id
        )

    async def nodes(self) -> List[AiriosBoundNodeInfo]:
        """Get the list of bound nodes."""

        reg_descs: List[RegisterBase] = [
            self.regmap[Reg.ADDRESS_NODE_1],
            self.regmap[Reg.ADDRESS_NODE_2],
            self.regmap[Reg.ADDRESS_NODE_3],
            self.regmap[Reg.ADDRESS_NODE_4],
            self.regmap[Reg.ADDRESS_NODE_5],
            self.regmap[Reg.ADDRESS_NODE_6],
            self.regmap[Reg.ADDRESS_NODE_7],
            self.regmap[Reg.ADDRESS_NODE_8],
            self.regmap[Reg.ADDRESS_NODE_9],
            self.regmap[Reg.ADDRESS_NODE_10],
            self.regmap[Reg.ADDRESS_NODE_11],
            self.regmap[Reg.ADDRESS_NODE_12],
            self.regmap[Reg.ADDRESS_NODE_13],
            self.regmap[Reg.ADDRESS_NODE_14],
            self.regmap[Reg.ADDRESS_NODE_15],
            self.regmap[Reg.ADDRESS_NODE_16],
            self.regmap[Reg.ADDRESS_NODE_17],
            self.regmap[Reg.ADDRESS_NODE_18],
            self.regmap[Reg.ADDRESS_NODE_19],
            self.regmap[Reg.ADDRESS_NODE_20],
            self.regmap[Reg.ADDRESS_NODE_21],
            self.regmap[Reg.ADDRESS_NODE_22],
            self.regmap[Reg.ADDRESS_NODE_23],
            self.regmap[Reg.ADDRESS_NODE_24],
            self.regmap[Reg.ADDRESS_NODE_25],
            self.regmap[Reg.ADDRESS_NODE_26],
            self.regmap[Reg.ADDRESS_NODE_27],
            self.regmap[Reg.ADDRESS_NODE_28],
            self.regmap[Reg.ADDRESS_NODE_29],
            self.regmap[Reg.ADDRESS_NODE_30],
            self.regmap[Reg.ADDRESS_NODE_31],
            self.regmap[Reg.ADDRESS_NODE_32],
        ]

        nodes: List[AiriosBoundNodeInfo] = []
        for item in reg_descs:
            result = await self.client.get_register(item, self.slave_id)
            if result is None or result.value is None:
                continue
            slave_id = result.value
            if slave_id == 0:
                continue

            result = await self.client.get_register(self.regmap[NodeReg.PRODUCT_ID], slave_id)
            if result is None or result.value is None:
                continue
            try:
                product_id = ProductId(result.value)
            except ValueError:
                _LOGGER.warning("Unknown product ID %s", result.value)
                continue
            else:
                product_id = ProductId(result.value)

            result = await self.client.get_register(self.regmap[NodeReg.RF_ADDRESS], slave_id)
            if result is None or result.value is None:
                continue
            rf_address = result.value

            info = AiriosBoundNodeInfo(
                slave_id=slave_id, product_id=product_id, rf_address=rf_address
            )
            nodes.append(info)
        return nodes

    async def node(self, slave_id: int) -> AiriosNode:
        """Get a node intance by its Modbus slave ID."""

        if slave_id == self.slave_id:
            return self

        for node in await self.nodes():
            if node.slave_id != slave_id:
                continue
            if node.product_id == ProductId.VMD_02RPS78:
                return VMD02RPS78(node.slave_id, self.client)
            if node.product_id == ProductId.VMN_05LM02:
                return VMN05LM02(node.slave_id, self.client)

        raise AiriosException(f"Node {slave_id} not found")

    async def rf_load_current_hour(self) -> Result[float]:
        """Get the RF load in the current hour (%)."""
        return await self.client.get_register(self.regmap[Reg.RF_LOAD_CURRENT_HOUR], self.slave_id)

    async def rf_load_last_hour(self) -> Result[float]:
        """Get the RF load in the last hour (%)."""
        return await self.client.get_register(self.regmap[Reg.RF_LOAD_LAST_HOUR], self.slave_id)

    async def rf_load(self) -> RFLoad:
        """Get the RF load."""
        r1 = await self.rf_load_current_hour()
        r2 = await self.rf_load_last_hour()
        return RFLoad(load_current_hour=r1.value, load_last_hour=r2.value)

    async def rf_sent_messages_current_hour(self) -> Result[int]:
        """Get the RF sent messages in the current hour."""
        return await self.client.get_register(
            self.regmap[Reg.MESSAGES_SEND_CURRENT_HOUR], self.slave_id
        )

    async def rf_sent_messages_last_hour(self) -> Result[int]:
        """Get the RF sent messages in the last hour."""
        return await self.client.get_register(
            self.regmap[Reg.MESSAGES_SEND_LAST_HOUR], self.slave_id
        )

    async def rf_sent_messages(self) -> RFSentMessages:
        """Get the RF sent messages."""
        r1 = await self.rf_sent_messages_current_hour()
        r2 = await self.rf_sent_messages_last_hour()
        return RFSentMessages(messages_current_hour=r1.value, messages_last_hour=r2.value)

    async def serial_config(self) -> SerialConfig:
        """Get the serial configuration."""
        result = await self.client.get_register(self.regmap[Reg.SERIAL_BAUDRATE], self.slave_id)
        baudrate: Baudrate = Baudrate(result.value)
        result = await self.client.get_register(self.regmap[Reg.SERIAL_PARITY], self.slave_id)
        parity: Parity = Parity(result.value)
        result = await self.client.get_register(self.regmap[Reg.SERIAL_STOP_BITS], self.slave_id)
        stopbits: StopBits = StopBits(result.value)
        return SerialConfig(baudrate=baudrate, stop_bits=stopbits, parity=parity)

    async def set_serial_config(self, config: SerialConfig) -> bool:
        """Set the serial configuration."""
        assert await self.client.set_register(
            self.regmap[Reg.SERIAL_BAUDRATE], config.baudrate, self.slave_id
        )
        assert await self.client.set_register(
            self.regmap[Reg.SERIAL_PARITY], config.parity, self.slave_id
        )
        assert await self.client.set_register(
            self.regmap[Reg.SERIAL_STOP_BITS], config.stop_bits, self.slave_id
        )
        return True

    async def modbus_events(self) -> Result[ModbusEvents]:
        """Modbus event responses via special Modbus functions."""
        result = await self.client.get_register(self.regmap[Reg.MODBUS_EVENTS], self.slave_id)
        return Result(ModbusEvents(result.value), result.status)

    async def power_on_time(self) -> Result[timedelta]:
        """Time since last power on or reset."""
        res = await self.client.get_register(self.regmap[Reg.UPTIME], self.slave_id)
        return Result(timedelta(seconds=res.value), res.status)

    async def reset(self, mode: ResetMode) -> bool:
        """Reset the bridge."""
        return await self.client.set_register(self.regmap[Reg.RESET_DEVICE], mode, self.slave_id)

    async def utc_time(self) -> Result[datetime]:
        """Get the UTC time."""
        return await self.client.get_register(self.regmap[Reg.UTC_TIME], self.slave_id)

    async def fetch_bridge(self) -> BRDG02R13Data:  # pylint: disable=duplicate-code
        """Fetch all bridge data at once."""

        return BRDG02R13Data(
            slave_id=self.slave_id,
            rf_address=await self._safe_fetch(self.node_rf_address),
            product_id=await self._safe_fetch(self.node_product_id),
            sw_version=await self._safe_fetch(self.node_software_version),
            product_name=await self._safe_fetch(self.node_product_name),
            rf_comm_status=await self._safe_fetch(self.node_rf_comm_status),
            battery_status=await self._safe_fetch(self.node_battery_status),
            fault_status=await self._safe_fetch(self.node_fault_status),
            rf_sent_messages_last_hour=await self._safe_fetch(self.rf_sent_messages_last_hour),
            rf_sent_messages_current_hour=await self._safe_fetch(
                self.rf_sent_messages_current_hour
            ),
            rf_load_last_hour=await self._safe_fetch(self.rf_load_last_hour),
            rf_load_current_hour=await self._safe_fetch(self.rf_load_current_hour),
            power_on_time=await self._safe_fetch(self.power_on_time),
        )
