"""Register definitions."""

import datetime
import struct
import typing as t
from dataclasses import dataclass
from enum import Flag, IntEnum, auto

from pymodbus.client.mixin import ModbusClientMixin

from .constants import ValueStatusFlags, ValueStatusSource
from .exceptions import AiriosDecodeError, AiriosInvalidArgumentException

T = t.TypeVar("T")


class RegisterAddress(IntEnum):
    """The register address base class."""


class RegisterAccess(Flag):
    """Register access flags."""

    READ = auto()
    WRITE = auto()
    STATUS = auto()


@dataclass(frozen=True)
class RegisterDescription:
    """Register description."""

    address: RegisterAddress
    length: int
    access: RegisterAccess


class RegisterBase(t.Generic[T]):
    """Base class for register definitions."""

    description: RegisterDescription
    datatype: ModbusClientMixin.DATATYPE

    def __init__(self, description: RegisterDescription) -> None:
        """Initialize the register instance."""
        self.description = description

    def decode(self, registers: list[int]) -> T:
        """Decode register bytes to value."""
        return ModbusClientMixin.convert_from_registers(
            registers, self.datatype, word_order="little"
        )  # type: ignore

    def encode(self, value: T) -> list[int]:
        """Encode value to register bytes."""
        return ModbusClientMixin.convert_to_registers(value, self.datatype, word_order="little")  # type: ignore


class StringRegister(RegisterBase[str]):
    """String register."""

    datatype = ModbusClientMixin.DATATYPE.STRING

    def __init__(self, address: RegisterAddress, length: int, access: RegisterAccess) -> None:
        """Initialize the StringRegister instance."""
        description = RegisterDescription(address, length, access)
        super().__init__(description)

    def decode(self, registers: list[int]) -> str:
        """Decode register bytes to value."""

        def registers_to_bytearray(registers: list[int]) -> bytearray:
            """Convert registers to bytes."""
            b = bytearray()
            for x in registers:
                b.extend(x.to_bytes(2, "big"))
            return b

        b = registers_to_bytearray(registers)

        # remove trailing null bytes
        trailing_nulls_begin = len(b)
        while trailing_nulls_begin > 0 and b[trailing_nulls_begin - 1] == 0:
            trailing_nulls_begin -= 1

        b = b[:trailing_nulls_begin]

        try:
            result = b.decode("utf-8")
        except UnicodeDecodeError as err:
            raise AiriosDecodeError from err
        return result

    def encode(self, value: str) -> list[int]:
        return ModbusClientMixin.convert_to_registers(value, self.datatype, word_order="little")


class NumberRegister(RegisterBase[T]):
    """Base class for number registers."""

    def decode(self, registers: list[int]) -> T:
        """Decode register bytes to value."""
        result: T = t.cast(
            T,
            ModbusClientMixin.convert_from_registers(registers, self.datatype, word_order="little"),
        )
        return result

    def encode(self, value: T) -> list[int]:
        """Encode value to register bytes."""
        if isinstance(value, int):
            int_value = value
        elif isinstance(value, float):
            int_value = int(value)
        elif isinstance(value, bool):
            int_value = int(value)
        else:
            raise AiriosInvalidArgumentException(f"Unsupported type {type(value)}")
        return ModbusClientMixin.convert_to_registers(int_value, self.datatype, word_order="little")


class U16Register(NumberRegister[int]):
    """Unsigned 16-bit register."""

    datatype = ModbusClientMixin.DATATYPE.UINT16

    def __init__(self, address: RegisterAddress, access: RegisterAccess) -> None:
        """Initialize the U16Register instance."""
        description = RegisterDescription(address, 1, access)
        super().__init__(description)


class I16Register(NumberRegister[int]):
    """Signed 16-bit register."""

    datatype = ModbusClientMixin.DATATYPE.INT16

    def __init__(self, address: RegisterAddress, access: RegisterAccess) -> None:
        """Initialize the I16Register instance."""
        description = RegisterDescription(address, 1, access)
        super().__init__(description)


class U32Register(NumberRegister[int]):
    """Unsigned 32-bit register."""

    datatype = ModbusClientMixin.DATATYPE.UINT32

    def __init__(self, address: RegisterAddress, access: RegisterAccess) -> None:
        """Initialize the U32Register instance."""
        description = RegisterDescription(address, 2, access)
        super().__init__(description)


class FloatRegister(NumberRegister[float]):
    """Float register."""

    datatype = ModbusClientMixin.DATATYPE.FLOAT32

    def __init__(self, address: RegisterAddress, access: RegisterAccess) -> None:
        """Initialize the FloatRegister instance."""
        description = RegisterDescription(address, 2, access)
        super().__init__(description)


class DateRegister(RegisterBase[datetime.date]):
    """Date register."""

    datatype = ModbusClientMixin.DATATYPE.UINT32

    def __init__(self, address: RegisterAddress, access: RegisterAccess) -> None:
        """Initialize the DateRegister instance."""
        description = RegisterDescription(address, 2, access)
        super().__init__(description)

    def decode(self, registers: list[int]) -> datetime.date:
        """Decode register bytes to value."""
        value: int = t.cast(int, super().decode(registers))

        if value == 0xFFFFFFFF:
            return datetime.date.min

        buf = value.to_bytes(4, "big")
        (day, month, year) = struct.unpack(">BBH", buf)
        return datetime.date(year, month, day)

    def encode(self, value: datetime.date) -> list[int]:
        """Encode value to register bytes."""

        buf = struct.pack(">BBH", value.day, value.month, value.year)
        ival = int.from_bytes(buf, byteorder="big")
        return ModbusClientMixin.convert_to_registers(ival, self.datatype, word_order="little")


class DateTimeRegister(RegisterBase[datetime.datetime]):
    """DateTime register."""

    datatype = ModbusClientMixin.DATATYPE.UINT32

    def __init__(self, address: RegisterAddress, access: RegisterAccess) -> None:
        """Initialize the DateTimeRegister instance."""
        description = RegisterDescription(address, 2, access)
        super().__init__(description)

    def decode(self, registers: list[int]) -> datetime.datetime:
        """Decode register bytes to value."""
        value: int = t.cast(int, super().decode(registers))

        if value == 0xFFFFFFFF:
            return datetime.datetime.min

        return datetime.datetime.fromtimestamp(value, tz=datetime.timezone.utc)

    def encode(self, value: datetime.datetime) -> list[int]:
        """Encode value to register bytes."""

        ts: float = value.replace(tzinfo=datetime.timezone.utc).timestamp()
        ival: int = int(ts)
        return ModbusClientMixin.convert_to_registers(ival, self.datatype, word_order="little")


@dataclass
class ResultStatus:
    """Metadata associated to a register value."""

    age: datetime.timedelta
    source: ValueStatusSource
    flags: ValueStatusFlags

    def __str__(self) -> str:
        return f"value is {self.age} old, last seen from {self.source}, flags: {self.flags}"


@dataclass
class Result(t.Generic[T]):
    """Register read result."""

    value: T
    status: ResultStatus | None

    def __init__(self, value: T, status: ResultStatus | None = None) -> None:
        super().__init__()
        self.value = value
        self.status = status

    def __str__(self) -> str:
        if isinstance(self.value, str):
            return f"{self.value}"
        if isinstance(self.value, datetime.date):
            return f"{self.value.isoformat()}"
        if isinstance(self.value, datetime.datetime):
            return f"{self.value.isoformat()}"
        if isinstance(self.value, float):
            return f"{self.value:.04f}"
        if isinstance(self.value, int):
            return f"{self.value}"
        return f"{self.value}"
