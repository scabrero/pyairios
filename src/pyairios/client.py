"""Async client for the Airios BRDB-02R13 Modbus gateway."""

from __future__ import annotations

import asyncio
import datetime
import logging
import time
import typing as t
from dataclasses import dataclass

import pymodbus.client as modbusClient
from pymodbus.client.mixin import ModbusClientMixin
from pymodbus.constants import ExcCodes
from pymodbus.exceptions import ConnectionException as ModbusConnectionException
from pymodbus.exceptions import ModbusException, ModbusIOException
from pymodbus.pdu import ExceptionResponse, ModbusPDU
from pymodbus.pdu.register_message import (
    WriteMultipleRegistersResponse,
    WriteSingleRegisterResponse,
)

from pyairios.data_model import AiriosDeviceData

from .constants import ValueStatusFlags, ValueStatusSource
from .exceptions import (
    AiriosAcknowledgeException,
    AiriosConnectionException,
    AiriosConnectionInterruptedException,
    AiriosException,
    AiriosIOException,
    AiriosInvalidArgumentException,
    AiriosReadException,
    AiriosSlaveBusyException,
    AiriosSlaveFailureException,
    AiriosWriteException,
)
from .registers import RegisterAccess, RegisterBase, Result, ResultStatus

LOGGER = logging.getLogger(__name__)

T = t.TypeVar("T")

# Minimum time to wait between two commands sent to the device. If commands are sent too fast
# it will not respond. This happens when connected over USB.
MIN_TIME_BETWEEN_COMMANDS = 0.01


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
    ts: float
    lock: asyncio.Lock

    def __init__(self, client: modbusClient.ModbusBaseClient) -> None:
        self.client = client
        self.ts = 0
        self.lock = asyncio.Lock()

    def __del__(self):
        if hasattr(self, "client") and self.client.connected:
            LOGGER.debug("Closing modbus connection")
            self.client.close()

    async def _reconnect(self) -> bool:
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
        return self.client.connected

    async def _read_registers(self, register: int, length: int, device_id: int) -> ModbusPDU:
        """Async read registers from device."""

        async with self.lock:
            LOGGER.debug(
                "Reading register %s with length %s from device id %s",
                register,
                length,
                device_id,
            )

            await self._reconnect()
            try:
                elapsed = time.time() - self.ts
                if elapsed < MIN_TIME_BETWEEN_COMMANDS:
                    delay = MIN_TIME_BETWEEN_COMMANDS - elapsed
                    await asyncio.sleep(delay)

                response = await self.client.read_holding_registers(
                    register,
                    count=length,
                    device_id=device_id,
                )
                if isinstance(response, ExceptionResponse):
                    if response.exception_code == ExcCodes.DEVICE_BUSY:
                        message = (
                            "Got a SlaveBusy Modbus Exception while reading "
                            f"register {register} (length {length}) from device id {device_id}"
                        )
                        LOGGER.info(message)
                        raise AiriosSlaveBusyException(message)

                    if response.exception_code == ExcCodes.DEVICE_FAILURE:
                        message = (
                            "Got a SlaveFailure Modbus Exception while reading "
                            f"register {register} (length {length}) from device id {device_id}"
                        )
                        LOGGER.info(message)
                        raise AiriosSlaveFailureException(message)

                    if response.exception_code == ExcCodes.ACKNOWLEDGE:
                        message = (
                            f"Got ACK while reading register {register} (length {length}) "
                            f"from device id {device_id}."
                        )
                        LOGGER.info(message)
                        raise AiriosAcknowledgeException(message)

                    message = (
                        f"Got an error while reading register {register} "
                        f"(length {length}) from device id {device_id}: {response}"
                    )
                    LOGGER.warning(message)
                    raise AiriosReadException(
                        message, modbus_exception_code=response.exception_code
                    )

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
            finally:
                self.ts = time.time()
            return response

    async def _write_registers(self, register: int, value: list[int], device_id: int) -> bool:
        """Async write registers to device."""

        async with self.lock:
            LOGGER.debug("Writing register %s: %s to device id %s", register, value, device_id)

            await self._reconnect()

            single_register = len(value) == 1
            try:
                if single_register:
                    response = await self.client.write_register(
                        register,
                        value[0],
                        device_id=device_id,
                    )
                else:
                    response = await self.client.write_registers(
                        register,
                        value,
                        device_id=device_id,
                    )
                if isinstance(response, ExceptionResponse):
                    message = (
                        f"Failed to write value {value} to register {register}: "
                        f"{response.exception_code:02X}"
                    )
                    LOGGER.info(message)
                    raise AiriosWriteException(
                        message, modbus_exception_code=response.exception_code
                    )
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

    async def get_register(self, regdesc: RegisterBase[T], device_id: int) -> Result[T]:
        """Get a register from device."""

        if RegisterAccess.READ not in regdesc.description.access:
            LOGGER.warning("Attempt to read not readable register %s", regdesc)
            raise ValueError(f"Attempt to read not readable register {regdesc}")

        response = await self._read_registers(
            regdesc.description.address, regdesc.description.length, device_id
        )

        value = regdesc.decode(response.registers)
        if regdesc.result_adapter:
            value = regdesc.result_adapter(value)
        elif not isinstance(value, regdesc.result_type):
            value = regdesc.result_type(value)
        value_status = None

        if RegisterAccess.STATUS in regdesc.description.access:
            response = await self._read_registers(regdesc.description.address + 10000, 1, device_id)
            tmp: int = t.cast(
                int,
                ModbusClientMixin.convert_from_registers(
                    response.registers,
                    ModbusClientMixin.DATATYPE.UINT16,
                    word_order="little",
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

    async def get_multiple(
        self,
        regdesc: t.List[RegisterBase[T]],
        device_id: int,
    ) -> AiriosDeviceData:
        """Read multiple registers in one transaction. Does not fill Result.status"""
        if len(regdesc) == 0:
            msg = "Expected at least one register"
            raise AiriosInvalidArgumentException(msg)

        for r in regdesc:
            if RegisterAccess.READ not in r.description.access:
                LOGGER.warning("Attempt to read not readable register %s", r)
                raise ValueError(f"Attempt to read not readable register {r}")

        chunks = []
        chunk = [regdesc[0]]
        for i in range(1, len(regdesc)):
            prev = regdesc[i - 1].description
            curr = regdesc[i].description
            if prev.address + prev.length == curr.address:
                chunk.append(regdesc[i])
            else:
                chunks.append(chunk)
                chunk = [regdesc[i]]
        chunks.append(chunk)

        retval: AiriosDeviceData = {}
        for chunk in chunks:
            try:
                chunk_data = await self._get_chunk(chunk, device_id)
                retval.update(chunk_data)
            except AiriosAcknowledgeException as ex:
                msg = f"Failed to fetch registers chunk: {ex}"
                LOGGER.info(msg)
                continue
        return retval

    async def _get_chunk(
        self,
        chunk: t.List[RegisterBase[T]],
        device_id: int,
    ) -> AiriosDeviceData:
        retval: AiriosDeviceData = {}
        values = await self._get_multiple(chunk, device_id)
        for r, value in zip(chunk, values, strict=True):
            try:
                if r.result_adapter:
                    value = r.result_adapter(value)
                elif not isinstance(value, r.result_type):
                    value = r.result_type(value)
            except ValueError as ex:
                msg = f"Failed to fetch register {r.aproperty}: {ex}"
                LOGGER.info(msg)
                continue
            retval[r.aproperty] = Result(value, None)
        return retval

    async def _get_multiple(
        self,
        regdesc: t.List[RegisterBase[T]],
        device_id: int,
    ) -> t.List[T]:
        for i in range(1, len(regdesc)):
            prev = regdesc[i - 1].description
            curr = regdesc[i].description
            if prev.address + prev.length != curr.address:
                msg = (
                    f"Requested registers must be in monotonically increasing order, "
                    f"but {prev.address} + {prev.length} != {curr.address}!"
                )
                raise AiriosInvalidArgumentException(msg)

        start = regdesc[0].description
        end = regdesc[-1].description
        total_length = end.address + end.length - start.address
        LOGGER.debug("Reading %s registers starting from %s", total_length, start.address)

        response = await self._read_registers(start.address, total_length, device_id)

        values = []
        for r in regdesc:
            value = r.decode(
                response.registers[
                    r.description.address - start.address : r.description.address
                    - start.address
                    + r.description.length
                ]
            )
            values.append(value)
        return values

    async def set_register(self, register: RegisterBase[T], value: t.Any, device_id: int) -> bool:
        """Write a register to the device."""

        if RegisterAccess.WRITE not in register.description.access:
            LOGGER.warning("Attempt to write not writable register %s", register)
            raise ValueError(f"Trying to write not writable register {register}")

        registers = register.encode(value)
        return await self._write_registers(register.description.address, registers, device_id)

    async def connect(self) -> bool:
        """Establish underlying Modbus connection."""
        return await self._reconnect()

    def close(self) -> None:
        """Close underlying Modbus connection."""
        self.client.close()


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
