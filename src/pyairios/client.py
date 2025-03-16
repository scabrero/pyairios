"""Async client for the Airios BRDB-02R13 Modbus gateway."""

from __future__ import annotations

import datetime
import logging
import typing as t
from dataclasses import dataclass

import pymodbus.client as modbusClient
from pymodbus.client.mixin import ModbusClientMixin
from pymodbus.exceptions import ConnectionException as ModbusConnectionException
from pymodbus.exceptions import ModbusException, ModbusIOException
from pymodbus.pdu import ExceptionResponse, ModbusPDU
from pymodbus.pdu.register_message import (
    WriteMultipleRegistersResponse,
    WriteSingleRegisterResponse,
)

from .constants import ValueStatusFlags, ValueStatusSource
from .exceptions import (
    AiriosAcknowledgeException,
    AiriosConnectionException,
    AiriosConnectionInterruptedException,
    AiriosException,
    AiriosIOException,
    AiriosReadException,
    AiriosSlaveBusyException,
    AiriosSlaveFailureException,
    AiriosWriteException,
)
from .registers import RegisterAccess, RegisterBase, Result, ResultStatus

LOGGER = logging.getLogger(__name__)

T = t.TypeVar("T")


@dataclass
class AiriosBaseTransport:
    """Base class to define the bridge transport."""


@dataclass
class AiriosTcpTransport(AiriosBaseTransport):
    """Parameters for the TCP transport."""

    host: str = "192.168.0.207"
    port: int = 502


@dataclass
class AiriosRtuTransport(AiriosBaseTransport):
    """Parameters for the serial transport."""

    device: str = "/dev/ttyACM0"
    baudrate: int = 19200
    data_bits: int = 8
    parity: str = "E"
    stop_bits: int = 1


class AsyncAiriosModbusClient:
    """The base class."""

    client: modbusClient.ModbusBaseClient

    def __init__(self, client: modbusClient.ModbusBaseClient) -> None:
        self.client = client

    def __del__(self):
        if hasattr(self, "client") and self.client.connected:
            LOGGER.debug("Closing modbus connection")
            self.client.close()

    async def _reconnect(self) -> None:
        try:
            if not self.client.connected:
                LOGGER.debug("Establishing modbus connection")
                await self.client.connect()
            if not self.client.connected:
                LOGGER.error("Failed to establish modbus connection")
                self.client.close()
                raise AiriosConnectionException
        except ModbusException as err:
            message = f"Failed to establish modbus connection: {err}"
            LOGGER.error(message)
            self.client.close()
            raise AiriosConnectionException from err

    async def _read_registers(self, register: int, length: int, slave: int) -> ModbusPDU:
        """Async read registers from device."""

        LOGGER.debug("Reading register %s with length %s from slave %s", register, length, slave)

        await self._reconnect()
        try:
            response = await self.client.read_holding_registers(register, count=length, slave=slave)
            if isinstance(response, ExceptionResponse):
                if response.exception_code == ExceptionResponse.SLAVE_BUSY:
                    message = (
                        "Got a SlaveBusy Modbus Exception while reading "
                        f"register {register} (length {length}) from slave {slave}"
                    )
                    LOGGER.info(message)
                    raise AiriosSlaveBusyException(message)

                if response.exception_code == ExceptionResponse.SLAVE_FAILURE:
                    message = (
                        "Got a SlaveFailure Modbus Exception while reading "
                        f"register {register} (length {length}) from slave {slave}"
                    )
                    LOGGER.info(message)
                    raise AiriosSlaveFailureException(message)

                if response.exception_code == ExceptionResponse.ACKNOWLEDGE:
                    message = (
                        f"Got ACK while reading register {register} (length {length}) "
                        f"from slave {slave}."
                    )
                    LOGGER.info(message)
                    raise AiriosAcknowledgeException(message)

                message = (
                    f"Got an error while reading register {register} "
                    f"(length {length}) from slave {slave}: {response}"
                )
                LOGGER.warning(message)
                raise AiriosReadException(message, modbus_exception_code=response.exception_code)

            if len(response.registers) != length:
                message = (
                    f"Mismatch between number of requested registers ({length}) "
                    f"and number of received registers ({len(response.registers)})"
                )
                LOGGER.error(message)
                raise AiriosSlaveBusyException(message)
        except ModbusIOException as err:
            message = f"Could not read register, I/O exception: {err}"
            LOGGER.error(message)
            self.client.close()
            raise AiriosIOException(message) from err
        except ModbusConnectionException as err:
            message = f"Could not read register, bad connection: {err}"
            LOGGER.error(message)
            self.client.close()
            raise AiriosConnectionInterruptedException(message) from err
        except ModbusException as err:
            message = f"Modbus exception reading register: {err}"
            LOGGER.error(message)
            raise AiriosException(message) from err
        return response

    async def _write_registers(self, register: int, value: list[int], slave: int) -> bool:
        """Async write registers to device."""

        LOGGER.debug("Writing register %s: %s to slave %s", register, value, slave)

        await self._reconnect()

        single_register = len(value) == 1
        try:
            if single_register:
                response = await self.client.write_register(
                    register,
                    value[0],
                    slave=slave,
                )
            else:
                response = await self.client.write_registers(
                    register,
                    value,
                    slave=slave,
                )
            if isinstance(response, ExceptionResponse):
                message = (
                    f"Failed to write value {value} to register {register}: "
                    f"{response.exception_code:02X}"
                )
                LOGGER.info(message)
                raise AiriosWriteException(message, modbus_exception_code=response.exception_code)
        except ModbusIOException as err:
            message = f"Could not write register, I/O exception: {err}"
            LOGGER.error(message)
            self.client.close()
            raise AiriosIOException(message) from err
        except ModbusConnectionException as err:
            message = f"Could not write register, bad connection: {err}"
            LOGGER.error(message)
            self.client.close()
            raise AiriosConnectionInterruptedException(message) from err
        except ModbusException as err:
            message = f"Could now write register: {err}"
            LOGGER.error(message)
            raise AiriosException(message) from err
        if single_register:
            assert isinstance(response, WriteSingleRegisterResponse)
            r1: bool = response.address == register and response.registers == [value[0]]
            return r1
        assert isinstance(response, WriteMultipleRegistersResponse)
        r2: bool = response.address == register and response.count == len(value)
        return r2

    async def get_register(self, regdesc: RegisterBase[T], slave: int) -> Result[T]:
        """Get a register from device."""

        if RegisterAccess.READ not in regdesc.description.access:
            LOGGER.warning("Attempt to read not readable register %s", regdesc)
            raise ValueError(f"Attempt to read not readable register {regdesc}")

        response = await self._read_registers(
            regdesc.description.address, regdesc.description.length, slave
        )

        value = regdesc.decode(response.registers)
        value_status = None

        if RegisterAccess.STATUS in regdesc.description.access:
            response = await self._read_registers(regdesc.description.address + 10000, 1, slave)
            tmp: int = t.cast(
                int,
                ModbusClientMixin.convert_from_registers(
                    response.registers, ModbusClientMixin.DATATYPE.UINT16, word_order="little"
                ),
            )
            if tmp is not None:
                age: int = tmp & 0x7F
                age_is_hours = (tmp >> 7) & 0x01
                flags: ValueStatusFlags = ValueStatusFlags((tmp >> 8) & 0xCF)
                source: ValueStatusSource = ValueStatusSource((tmp >> 12) & 0x03)

                if age_is_hours:
                    age *= 3600
                delta = datetime.timedelta(seconds=age)
                value_status = ResultStatus(delta, source, flags)

        return Result(value, value_status)

    async def set_register(self, register: RegisterBase[T], value: t.Any, slave: int) -> bool:
        """Write a register to the device."""

        if RegisterAccess.WRITE not in register.description.access:
            LOGGER.warning("Attempt to write not writable register %s", register)
            raise ValueError(f"Trying to write not writable register {register}")

        registers = register.encode(value)
        return await self._write_registers(register.description.address, registers, slave)


class AsyncAiriosModbusTcpClient(AsyncAiriosModbusClient):
    """Airios client using Modbus TCP transport."""

    def __init__(self, transport: AiriosTcpTransport) -> None:
        client = modbusClient.AsyncModbusTcpClient(transport.host, port=transport.port)
        super().__init__(client)


class AsyncAiriosModbusRtuClient(AsyncAiriosModbusClient):
    """Airios client using Modbus RTU transport."""

    def __init__(self, transport: AiriosRtuTransport) -> None:
        client = modbusClient.AsyncModbusSerialClient(
            transport.device,
            baudrate=transport.baudrate,
            bytesize=transport.data_bits,
            parity=transport.parity,
            stopbits=transport.stop_bits,
        )
        super().__init__(client)
