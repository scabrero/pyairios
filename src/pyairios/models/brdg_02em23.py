"""Airios BRDG-02EM23 Ethernet RF bridge implementation."""

from __future__ import annotations

import datetime
import logging

from pyairios.bridge import AiriosBridge
from pyairios.client import AsyncAiriosModbusClient
from pyairios.constants import (
    AiriosDeviceType,
    ProductId,
)

DEFAULT_DEVICE_ID = 1

LOGGER = logging.getLogger(__name__)


def pr_id() -> ProductId:
    """
    Get product_id for model BRDG-02EM23.
    Named as is to discern from product_id register.
    :return: unique int
    """
    return ProductId.BRDG_02EM23


def pr_type() -> AiriosDeviceType:
    """
    Get the device type.
    """
    return AiriosDeviceType.RF_BRIDGE


def pr_description() -> list[str]:
    """
    Get description of product(s) using BRDG-02EM23.
    Human-readable text, used in e.g. HomeAssistant Binding UI.
    """
    return ["Airios Ethernet RF Gateway"]


def pr_instantiate(device_id: int, client: AsyncAiriosModbusClient) -> BRDG02EM23:
    """Get a new device instance. Used by the device factory to instantiate by product ID."""
    return BRDG02EM23(device_id, client)


def datetime_register(value: int) -> datetime.datetime:
    """Decode register bytes to value."""
    if value == 0xFFFFFFFF:
        raise ValueError("Unknown")
    return datetime.datetime.fromtimestamp(value, tz=datetime.timezone.utc)


class BRDG02EM23(AiriosBridge):
    """Represents a BRDG-02EM23 TCP RF bridge."""

    def __str__(self) -> str:
        return f"BRDG-02EM23@{self.device_id}"

    def pr_id(self) -> ProductId:
        return pr_id()

    def pr_type(self) -> AiriosDeviceType:
        return pr_type()

    def pr_description(self) -> list[str]:
        return pr_description()
