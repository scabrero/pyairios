"""Register definitions."""

from dataclasses import dataclass
import datetime
import typing as t
import struct
from enum import Flag, IntEnum, auto
from abc import abstractmethod

from pymodbus.payload import BinaryPayloadBuilder, BinaryPayloadDecoder

from .constants import ValueStatusFlags, ValueStatusSource
from .exceptions import AiriosDecodeError, AiriosInvalidArgumentException, AiriosNotImplemented

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
    decode_function_name: t.Callable
    encode_function_name: t.Callable


class RegisterBase(t.Generic[T]):
    """Base class for register definitions."""

    description: RegisterDescription

    def __init__(self, description: RegisterDescription) -> None:
        """Initialize the register instance."""
        self.description = description

    @abstractmethod
    def decode(self, decoder: BinaryPayloadDecoder) -> T:
        """Decode register bytes to value."""
        raise AiriosNotImplemented

    @abstractmethod
    def encode(self, value: T, encoder: BinaryPayloadBuilder) -> None:
        """Encode value to register bytes."""
        raise AiriosNotImplemented


class StringRegister(RegisterBase[str]):
    """String register."""

    def __init__(self, address: RegisterAddress, length: int, access: RegisterAccess) -> None:
        """Initialize the StringRegister instance."""
        description = RegisterDescription(
            address,
            length,
            access,
            decode_function_name=BinaryPayloadDecoder.decode_string,
            encode_function_name=BinaryPayloadBuilder.add_string,
        )
        super().__init__(description)

    def decode(self, decoder: BinaryPayloadDecoder) -> str:
        """Decode register bytes to value."""
        str_bytes = t.cast(
            bytes, self.description.decode_function_name(decoder, self.description.length * 2)
        )
        try:
            result = str_bytes.decode("utf-8")
        except UnicodeDecodeError as err:
            raise AiriosDecodeError from err
        return result.rstrip("\0")

    def encode(self, value: str, encoder: BinaryPayloadBuilder) -> None:
        """Encode value to register bytes."""
        if not isinstance(value, str):
            raise AiriosInvalidArgumentException(f"Unsupported type {type(value)}")
        self.description.encode_function_name(encoder, value)


class NumberRegister(RegisterBase[T]):
    """Base class for number registers."""

    def decode(self, decoder: BinaryPayloadDecoder) -> T:
        """Decode register bytes to value."""
        result: T = t.cast(T, self.description.decode_function_name(decoder))
        return result

    def encode(self, value: T, encoder: BinaryPayloadBuilder) -> None:
        """Encode value to register bytes."""
        if isinstance(value, int):
            int_value = value
        elif isinstance(value, float):
            int_value = int(value)
        else:
            raise AiriosInvalidArgumentException(f"Unsupported type {type(value)}")
        self.description.encode_function_name(encoder, int_value)


class U16Register(NumberRegister[int]):
    """Unsigned 16-bit register."""

    def __init__(self, address: RegisterAddress, access: RegisterAccess) -> None:
        """Initialize the U16Register instance."""
        description = RegisterDescription(
            address,
            1,
            access,
            decode_function_name=BinaryPayloadDecoder.decode_16bit_uint,
            encode_function_name=BinaryPayloadBuilder.add_16bit_uint,
        )
        super().__init__(description)


class I16Register(NumberRegister[int]):
    """Signed 16-bit register."""

    def __init__(self, address: RegisterAddress, access: RegisterAccess) -> None:
        """Initialize the I16Register instance."""
        description = RegisterDescription(
            address,
            1,
            access,
            decode_function_name=BinaryPayloadDecoder.decode_16bit_int,
            encode_function_name=BinaryPayloadBuilder.add_16bit_int,
        )
        super().__init__(description)


class U32Register(NumberRegister[int]):
    """Unsigned 32-bit register."""

    def __init__(self, address: RegisterAddress, access: RegisterAccess) -> None:
        """Initialize the U32Register instance."""
        description = RegisterDescription(
            address,
            2,
            access,
            decode_function_name=BinaryPayloadDecoder.decode_32bit_uint,
            encode_function_name=BinaryPayloadBuilder.add_32bit_uint,
        )
        super().__init__(description)


class FloatRegister(NumberRegister[float]):
    """Float register."""

    def __init__(self, address: RegisterAddress, access: RegisterAccess) -> None:
        """Initialize the FloatRegister instance."""
        description = RegisterDescription(
            address,
            2,
            access,
            decode_function_name=BinaryPayloadDecoder.decode_32bit_float,
            encode_function_name=BinaryPayloadBuilder.add_32bit_float,
        )
        super().__init__(description)


class DateRegister(RegisterBase[datetime.date]):
    """Date register."""

    def __init__(self, address: RegisterAddress, access: RegisterAccess) -> None:
        """Initialize the DateRegister instance."""
        description = RegisterDescription(
            address,
            2,
            access,
            decode_function_name=BinaryPayloadDecoder.decode_32bit_uint,
            encode_function_name=BinaryPayloadBuilder.add_32bit_uint,
        )
        super().__init__(description)

    def decode(self, decoder: BinaryPayloadDecoder) -> datetime.date:
        """Decode register bytes to value."""
        value: int = t.cast(int, self.description.decode_function_name(decoder))

        if value == 0xFFFFFFFF:
            return datetime.date.min

        buf = value.to_bytes(4, "big")
        (day, month, year) = struct.unpack(">BBH", buf)
        return datetime.date(year, month, day)

    def encode(self, value: datetime.date, encoder: BinaryPayloadBuilder) -> None:
        """Encode value to register bytes."""

        buf = struct.pack(">BBH", value.day, value.month, value.year)
        ival = int.from_bytes(buf, byteorder="big")
        self.description.encode_function_name(encoder, ival)


class DateTimeRegister(RegisterBase[datetime.datetime]):
    """DateTime register."""

    def __init__(self, address: RegisterAddress, access: RegisterAccess) -> None:
        """Initialize the DateTimeRegister instance."""
        description = RegisterDescription(
            address,
            2,
            access,
            decode_function_name=BinaryPayloadDecoder.decode_32bit_uint,
            encode_function_name=BinaryPayloadBuilder.add_32bit_uint,
        )
        super().__init__(description)

    def decode(self, decoder: BinaryPayloadDecoder) -> datetime.datetime:
        """Decode register bytes to value."""
        value: int = t.cast(int, self.description.decode_function_name(decoder))

        if value == 0xFFFFFFFF:
            return datetime.datetime.min

        return datetime.datetime.fromtimestamp(value, tz=datetime.timezone.utc)

    def encode(self, value: datetime.datetime, encoder: BinaryPayloadBuilder) -> None:
        """Encode value to register bytes."""

        ts: float = value.replace(tzinfo=datetime.timezone.utc).timestamp()
        ival: int = int(ts)
        self.description.encode_function_name(encoder, ival)


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
