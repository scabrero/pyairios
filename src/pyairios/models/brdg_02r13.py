"""Airios BRDG-02R13 RF bridge implementation."""

from __future__ import annotations

import datetime
import logging
from datetime import timedelta
from typing import List

from pyairios.client import AsyncAiriosModbusClient
from pyairios.constants import (
    AiriosDeviceType,
    Baudrate,
    BindingMode,
    BindingStatus,
    ModbusEvents,
    Parity,
    ProductId,
    ResetMode,
    RFLoad,
    RFSentMessages,
    SerialConfig,
    StopBits,
)
from pyairios.device import AiriosDevice, AiriosBoundDeviceInfo
from pyairios.exceptions import (
    AiriosBindingException,
    AiriosException,
    AiriosInvalidArgumentException,
)
from pyairios.models.factory import factory
from pyairios.properties import AiriosBridgeProperty as bp
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

DEFAULT_DEVICE_ID = 207

LOGGER = logging.getLogger(__name__)


def pr_id() -> ProductId:
    """
    Get product_id for model BRDG-02R13.
    Named as is to discern from product_id register.
    :return: unique int
    """
    return ProductId.BRDG_02R13


def pr_type() -> AiriosDeviceType:
    """
    Get the device type.
    """
    return AiriosDeviceType.RF_BRIDGE


def pr_description() -> list[str]:
    """
    Get description of product(s) using BRDG-02R13.
    Human-readable text, used in e.g. HomeAssistant Binding UI.
    """
    return ["Airios RS485 RF Gateway"]


def pr_instantiate(device_id: int, client: AsyncAiriosModbusClient) -> BRDG02R13:
    """Get a new device instance. Used by the device factory to instantiate by product ID."""
    return BRDG02R13(device_id, client)


def datetime_register(value: int) -> datetime.datetime:
    """Decode register bytes to value."""
    if value == 0xFFFFFFFF:
        raise ValueError("Unknown")
    return datetime.datetime.fromtimestamp(value, tz=datetime.timezone.utc)


class BRDG02R13(AiriosDevice):
    """Represents a BRDG-02R13 RF bridge."""

    def __init__(self, device_id: int, client: AsyncAiriosModbusClient) -> None:
        """Initialize the BRDG-02R13 RF bridge instance."""

        super().__init__(device_id, client)
        brdg_registers: List[RegisterBase] = [
            U16Register(bp.CUSTOMER_PRODUCT_ID, 40023, RegisterAccess.READ | RegisterAccess.WRITE),
            U32Register(
                bp.UTC_TIME,
                41015,
                RegisterAccess.READ | RegisterAccess.WRITE,
                result_adapter=datetime_register,
            ),
            U32Register(
                bp.LOCAL_TIME,
                41017,
                RegisterAccess.READ,
                result_adapter=datetime_register,
            ),
            U32Register(bp.UPTIME, 41019, RegisterAccess.READ),
            U16Register(bp.DAYLIGHT_SAVING_TYPE, 41021, RegisterAccess.READ | RegisterAccess.WRITE),
            U16Register(bp.TIMEZONE_OFFSET, 41022, RegisterAccess.READ | RegisterAccess.WRITE),
            U16Register(bp.OEM_CODE, 41101, RegisterAccess.READ | RegisterAccess.WRITE),
            U16Register(bp.MODBUS_EVENTS, 41103, RegisterAccess.READ | RegisterAccess.WRITE),
            U16Register(bp.RESET_DEVICE, 41107, RegisterAccess.WRITE),
            StringRegister(bp.CUSTOMER_SPECIFIC_NODE_ID, 41108, 10, RegisterAccess.WRITE),
            U16Register(bp.SERIAL_PARITY, 41998, RegisterAccess.READ | RegisterAccess.WRITE),
            U16Register(bp.SERIAL_STOP_BITS, 41999, RegisterAccess.READ | RegisterAccess.WRITE),
            U16Register(bp.SERIAL_BAUDRATE, 42000, RegisterAccess.READ | RegisterAccess.WRITE),
            U16Register(bp.MODBUS_DEVICE_ID, 42001, RegisterAccess.READ | RegisterAccess.WRITE),
            U16Register(bp.MESSAGES_SEND_CURRENT_HOUR, 42100, RegisterAccess.READ),
            U16Register(bp.MESSAGES_SEND_LAST_HOUR, 42101, RegisterAccess.READ),
            FloatRegister(bp.RF_LOAD_CURRENT_HOUR, 42102, RegisterAccess.READ),
            FloatRegister(bp.RF_LOAD_LAST_HOUR, 42104, RegisterAccess.READ),
            U32Register(bp.BINDING_PRODUCT_ID, 43000, RegisterAccess.READ | RegisterAccess.WRITE),
            U32Register(
                bp.BINDING_PRODUCT_SERIAL, 43002, RegisterAccess.READ | RegisterAccess.WRITE
            ),
            U16Register(bp.BINDING_COMMAND, 43004, RegisterAccess.WRITE),
            U16Register(
                bp.CREATE_NODE,
                43005,
                RegisterAccess.WRITE,
                min_value=2,
                max_value=247,
            ),
            U16Register(
                bp.FIRST_ADDRESS_TO_ASSIGN, 43006, RegisterAccess.READ | RegisterAccess.WRITE
            ),
            U16Register(bp.REMOVE_NODE, 43399, RegisterAccess.WRITE),
            U16Register(
                bp.ACTUAL_BINDING_STATUS, 43900, RegisterAccess.READ, result_type=BindingStatus
            ),
            U16Register(bp.NUMBER_OF_NODES, 43901, RegisterAccess.READ),
            U16Register(bp.ADDRESS_NODE_1, 43902, RegisterAccess.READ),
            U16Register(bp.ADDRESS_NODE_2, 43903, RegisterAccess.READ),
            U16Register(bp.ADDRESS_NODE_3, 43904, RegisterAccess.READ),
            U16Register(bp.ADDRESS_NODE_4, 43905, RegisterAccess.READ),
            U16Register(bp.ADDRESS_NODE_5, 43906, RegisterAccess.READ),
            U16Register(bp.ADDRESS_NODE_6, 43907, RegisterAccess.READ),
            U16Register(bp.ADDRESS_NODE_7, 43908, RegisterAccess.READ),
            U16Register(bp.ADDRESS_NODE_8, 43909, RegisterAccess.READ),
            U16Register(bp.ADDRESS_NODE_9, 43910, RegisterAccess.READ),
            U16Register(bp.ADDRESS_NODE_10, 43911, RegisterAccess.READ),
            U16Register(bp.ADDRESS_NODE_11, 43912, RegisterAccess.READ),
            U16Register(bp.ADDRESS_NODE_12, 43913, RegisterAccess.READ),
            U16Register(bp.ADDRESS_NODE_13, 43914, RegisterAccess.READ),
            U16Register(bp.ADDRESS_NODE_14, 43915, RegisterAccess.READ),
            U16Register(bp.ADDRESS_NODE_15, 43916, RegisterAccess.READ),
            U16Register(bp.ADDRESS_NODE_16, 43917, RegisterAccess.READ),
            U16Register(bp.ADDRESS_NODE_17, 43918, RegisterAccess.READ),
            U16Register(bp.ADDRESS_NODE_18, 43919, RegisterAccess.READ),
            U16Register(bp.ADDRESS_NODE_19, 43920, RegisterAccess.READ),
            U16Register(bp.ADDRESS_NODE_20, 43921, RegisterAccess.READ),
            U16Register(bp.ADDRESS_NODE_21, 43922, RegisterAccess.READ),
            U16Register(bp.ADDRESS_NODE_22, 43923, RegisterAccess.READ),
            U16Register(bp.ADDRESS_NODE_23, 43924, RegisterAccess.READ),
            U16Register(bp.ADDRESS_NODE_24, 43925, RegisterAccess.READ),
            U16Register(bp.ADDRESS_NODE_25, 43926, RegisterAccess.READ),
            U16Register(bp.ADDRESS_NODE_26, 43927, RegisterAccess.READ),
            U16Register(bp.ADDRESS_NODE_27, 43928, RegisterAccess.READ),
            U16Register(bp.ADDRESS_NODE_28, 43929, RegisterAccess.READ),
            U16Register(bp.ADDRESS_NODE_29, 43930, RegisterAccess.READ),
            U16Register(bp.ADDRESS_NODE_30, 43931, RegisterAccess.READ),
            U16Register(bp.ADDRESS_NODE_31, 43932, RegisterAccess.READ),
            U16Register(bp.ADDRESS_NODE_32, 43933, RegisterAccess.READ),
        ]
        self._add_registers(brdg_registers)

    def __str__(self) -> str:
        return f"BRDG-02R13@{self.device_id}"

    def pr_id(self) -> ProductId:
        return pr_id()

    def pr_type(self) -> AiriosDeviceType:
        return pr_type()

    def pr_description(self) -> list[str]:
        return pr_description()

    async def bind_controller(
        self,
        device_id: int,
        product_id: ProductId,
        product_serial: int | None = None,
    ) -> bool:
        """Bind a new controller to the bridge."""
        if device_id < 2 or device_id > 247:
            raise AiriosInvalidArgumentException(f"Modbus device id {device_id} out of range 2-247")

        if device_id == self.device_id:
            raise AiriosInvalidArgumentException(f"Modbus device id {device_id} already in use")

        mode = BindingMode.ABORT
        ok = await self.client.set_register(self.regmap[bp.BINDING_COMMAND], mode, self.device_id)
        if not ok:
            raise AiriosBindingException("Failed to reset binding status")

        result = await self.client.get_register(
            self.regmap[bp.ACTUAL_BINDING_STATUS], self.device_id
        )
        if result is None or result.value is None:
            raise AiriosBindingException("Failed to determine current binding status")
        if result.value != 0:
            raise AiriosBindingException(f"Bridge not ready for binding: {result.value}")

        mode = BindingMode.OUTGOING_SINGLE_PRODUCT
        if product_serial is not None:
            mode = BindingMode.OUTGOING_SINGLE_PRODUCT_PLUS_SERIAL

        ok = await self.client.set_register(
            self.regmap[bp.BINDING_PRODUCT_ID], product_id, self.device_id
        )
        if not ok:
            raise AiriosBindingException("Failed to configure binding product ID")

        ok = await self.client.set_register(self.regmap[bp.CREATE_NODE], device_id, self.device_id)
        if not ok:
            raise AiriosBindingException(f"Failed to create node for device id {device_id}")

        if product_serial is not None:
            ok = await self.client.set_register(
                self.regmap[bp.BINDING_PRODUCT_SERIAL], product_serial, self.device_id
            )
            if not ok:
                raise AiriosBindingException("Failed to configure binding product serial")

        value = ((device_id & 0xFF) << 8) | mode
        return await self.client.set_register(
            self.regmap[bp.BINDING_COMMAND], value, self.device_id
        )

    async def bind_status(self) -> BindingStatus:
        """Get the bind status."""
        result = await self.client.get_register(
            self.regmap[bp.ACTUAL_BINDING_STATUS], self.device_id
        )
        if result is None or result.value is None:
            return BindingStatus.NOT_AVAILABLE
        return BindingStatus(result.value)

    async def unbind(self, device_id: int) -> bool:
        """Remove a bound node from the bridge by its Modbus device ID."""
        return await self.client.set_register(
            self.regmap[bp.REMOVE_NODE], device_id, self.device_id
        )

    async def bind_accessory(
        self,
        controller_device_id: int,
        device_id: int,
        product_id: ProductId,
    ) -> bool:
        """Bind a new accessory to the bridge."""
        if controller_device_id < 2 or controller_device_id > 247:
            raise AiriosInvalidArgumentException(
                f"Modbus device id {controller_device_id} out of range 2-247"
            )

        if device_id < 2 or device_id > 247:
            raise AiriosInvalidArgumentException(f"Modbus device id {device_id} out of range 2-247")

        if device_id == self.device_id:
            raise AiriosInvalidArgumentException(f"Modbus device id {device_id} already in use")

        mode: BindingMode = BindingMode.ABORT
        ok = await self.client.set_register(self.regmap[bp.BINDING_COMMAND], mode, self.device_id)
        if not ok:
            raise AiriosBindingException("Failed to reset binding status")

        result = await self.client.get_register(
            self.regmap[bp.ACTUAL_BINDING_STATUS], self.device_id
        )
        if result is None or result.value is None:
            raise AiriosBindingException("Failed to determine current binding status")
        if result.value != 0:
            raise AiriosBindingException(f"Bridge not ready for binding: {result.value}")

        ok = await self.client.set_register(
            self.regmap[bp.BINDING_PRODUCT_ID], product_id, self.device_id
        )
        if not ok:
            raise AiriosBindingException("Failed to configure binding product ID")

        ok = await self.client.set_register(self.regmap[bp.CREATE_NODE], device_id, self.device_id)
        if not ok:
            raise AiriosBindingException(f"Failed to create node for device id {device_id}")

        mode = BindingMode.INCOMING_ON_EXISTING_NODE
        value = ((device_id & 0xFF) << 8) | mode
        return await self.client.set_register(
            self.regmap[bp.BINDING_COMMAND], value, self.device_id
        )

    async def nodes(self) -> List[AiriosBoundDeviceInfo]:
        """Get the list of bound nodes."""

        reg_descs: List[RegisterBase] = [
            self.regmap[bp.ADDRESS_NODE_1],
            self.regmap[bp.ADDRESS_NODE_2],
            self.regmap[bp.ADDRESS_NODE_3],
            self.regmap[bp.ADDRESS_NODE_4],
            self.regmap[bp.ADDRESS_NODE_5],
            self.regmap[bp.ADDRESS_NODE_6],
            self.regmap[bp.ADDRESS_NODE_7],
            self.regmap[bp.ADDRESS_NODE_8],
            self.regmap[bp.ADDRESS_NODE_9],
            self.regmap[bp.ADDRESS_NODE_10],
            self.regmap[bp.ADDRESS_NODE_11],
            self.regmap[bp.ADDRESS_NODE_12],
            self.regmap[bp.ADDRESS_NODE_13],
            self.regmap[bp.ADDRESS_NODE_14],
            self.regmap[bp.ADDRESS_NODE_15],
            self.regmap[bp.ADDRESS_NODE_16],
            self.regmap[bp.ADDRESS_NODE_17],
            self.regmap[bp.ADDRESS_NODE_18],
            self.regmap[bp.ADDRESS_NODE_19],
            self.regmap[bp.ADDRESS_NODE_20],
            self.regmap[bp.ADDRESS_NODE_21],
            self.regmap[bp.ADDRESS_NODE_22],
            self.regmap[bp.ADDRESS_NODE_23],
            self.regmap[bp.ADDRESS_NODE_24],
            self.regmap[bp.ADDRESS_NODE_25],
            self.regmap[bp.ADDRESS_NODE_26],
            self.regmap[bp.ADDRESS_NODE_27],
            self.regmap[bp.ADDRESS_NODE_28],
            self.regmap[bp.ADDRESS_NODE_29],
            self.regmap[bp.ADDRESS_NODE_30],
            self.regmap[bp.ADDRESS_NODE_31],
            self.regmap[bp.ADDRESS_NODE_32],
        ]

        values = await self.client.get_multiple(reg_descs, self.device_id)

        nodes: List[AiriosBoundDeviceInfo] = []
        for item in values.values():
            device_id = item.value
            if device_id == 0:
                continue

            result = await self.client.get_register(self.regmap[dp.PRODUCT_ID], device_id)
            if result is None or result.value is None:
                continue
            try:
                product_id = ProductId(result.value)
            except ValueError:
                LOGGER.warning("Unknown product ID %s", result.value)
                continue
            else:
                product_id = ProductId(result.value)

            result = await self.client.get_register(self.regmap[dp.RF_ADDRESS], device_id)
            if result is None or result.value is None:
                continue
            rf_address = result.value

            dev = await factory.get_device_by_product_id(product_id, device_id, self.client)

            info = AiriosBoundDeviceInfo(
                modbus_address=device_id,
                product_id=product_id,
                rf_address=rf_address,
                type=dev.pr_type(),
                description=dev.pr_description(),
            )
            nodes.append(info)
        return nodes

    async def node(self, device_id: int) -> AiriosDevice:
        """Get a node instance by its Modbus device ID."""

        if device_id == self.device_id:
            return self

        for node in await self.nodes():
            if node.modbus_address != device_id:
                continue
            return await factory.get_device_by_product_id(
                node.product_id, node.modbus_address, self.client
            )

        raise AiriosException(f"Node {device_id} not found")

    async def rf_load_current_hour(self) -> Result[float]:
        """Get the RF load in the current hour (%)."""
        return await self.client.get_register(self.regmap[bp.RF_LOAD_CURRENT_HOUR], self.device_id)

    async def rf_load_last_hour(self) -> Result[float]:
        """Get the RF load in the last hour (%)."""
        return await self.client.get_register(self.regmap[bp.RF_LOAD_LAST_HOUR], self.device_id)

    async def rf_load(self) -> RFLoad:
        """Get the RF load."""
        r1 = await self.rf_load_current_hour()
        r2 = await self.rf_load_last_hour()
        return RFLoad(load_current_hour=r1.value, load_last_hour=r2.value)

    async def rf_sent_messages_current_hour(self) -> Result[int]:
        """Get the RF sent messages in the current hour."""
        return await self.client.get_register(
            self.regmap[bp.MESSAGES_SEND_CURRENT_HOUR], self.device_id
        )

    async def rf_sent_messages_last_hour(self) -> Result[int]:
        """Get the RF sent messages in the last hour."""
        return await self.client.get_register(
            self.regmap[bp.MESSAGES_SEND_LAST_HOUR], self.device_id
        )

    async def rf_sent_messages(self) -> RFSentMessages:
        """Get the RF sent messages."""
        r1 = await self.rf_sent_messages_current_hour()
        r2 = await self.rf_sent_messages_last_hour()
        return RFSentMessages(messages_current_hour=r1.value, messages_last_hour=r2.value)

    async def serial_config(self) -> SerialConfig:
        """Get the serial configuration."""
        result = await self.client.get_register(self.regmap[bp.SERIAL_BAUDRATE], self.device_id)
        baudrate: Baudrate = Baudrate(result.value)
        result = await self.client.get_register(self.regmap[bp.SERIAL_PARITY], self.device_id)
        parity: Parity = Parity(result.value)
        result = await self.client.get_register(self.regmap[bp.SERIAL_STOP_BITS], self.device_id)
        stopbits: StopBits = StopBits(result.value)
        return SerialConfig(baudrate=baudrate, stop_bits=stopbits, parity=parity)

    async def set_serial_config(self, config: SerialConfig) -> bool:
        """Set the serial configuration."""
        return (
            await self.client.set_register(
                self.regmap[bp.SERIAL_BAUDRATE],
                config.baudrate,
                self.device_id,
            )
            and await self.client.set_register(
                self.regmap[bp.SERIAL_PARITY],
                config.parity,
                self.device_id,
            )
            and await self.client.set_register(
                self.regmap[bp.SERIAL_STOP_BITS],
                config.stop_bits,
                self.device_id,
            )
        )

    async def modbus_events(self) -> Result[ModbusEvents]:
        """Modbus event responses via special Modbus functions."""
        result = await self.client.get_register(self.regmap[bp.MODBUS_EVENTS], self.device_id)
        return Result(ModbusEvents(result.value), result.status)

    async def set_modbus_events(self, value: ModbusEvents) -> bool:
        """Set Modbus event responses via special Modbus functions."""
        return await self.client.set_register(self.regmap[bp.MODBUS_EVENTS], value, self.device_id)

    async def power_on_time(self) -> Result[timedelta]:
        """Time since last power on or reset."""
        res = await self.client.get_register(self.regmap[bp.UPTIME], self.device_id)
        return Result(timedelta(seconds=res.value), res.status)

    async def reset(self, mode: ResetMode) -> bool:
        """Reset the bridge."""
        return await self.client.set_register(self.regmap[bp.RESET_DEVICE], mode, self.device_id)

    async def utc_time(self) -> Result[datetime.datetime]:
        """Get the UTC time."""
        return await self.client.get_register(self.regmap[bp.UTC_TIME], self.device_id)

    async def oem_code(self) -> Result[int]:
        """Set the bridge OEM code."""
        return await self.client.get_register(self.regmap[bp.OEM_CODE], self.device_id)

    async def set_oem_code(self, code: int) -> bool:
        """Set the OEM code.

        It must be set to the matching code before binding a product.
        """
        return await self.client.set_register(self.regmap[bp.OEM_CODE], code, self.device_id)
