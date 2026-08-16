"""Airios BRDG-02R13 RS485 RF bridge implementation."""

from __future__ import annotations

import datetime
import logging
from typing import List

from pyairios.bridge import AiriosBridge
from pyairios.client import AsyncAiriosModbusClient
from pyairios.constants import (
    AiriosDeviceType,
    Baudrate,
    Parity,
    ProductId,
    SerialConfig,
    StopBits,
)
from pyairios.properties import AiriosBridgeProperty as bp
from pyairios.registers import (
    RegisterAccess,
    RegisterBase,
    U16Register,
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


class BRDG02R13(AiriosBridge):
    """Represents a BRDG-02R13 RF bridge."""

    def __init__(self, device_id: int, client: AsyncAiriosModbusClient) -> None:
        """Initialize the BRDG-02R13 RF bridge instance."""

        super().__init__(device_id, client)
        brdg_registers: List[RegisterBase] = [
            U16Register(bp.SERIAL_PARITY, 41998, RegisterAccess.READ | RegisterAccess.WRITE),
            U16Register(bp.SERIAL_STOP_BITS, 41999, RegisterAccess.READ | RegisterAccess.WRITE),
            U16Register(bp.SERIAL_BAUDRATE, 42000, RegisterAccess.READ | RegisterAccess.WRITE),
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
