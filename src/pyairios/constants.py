"""Constants and datay types used by this library."""

from dataclasses import dataclass
from enum import Flag, IntEnum, auto
import datetime


class ProductId(IntEnum):
    """The product ID is a unique product identifier.

    The value is composed by three fields, poduct type + sub ID + manufacturer ID.
    """

    BRDG_02R13 = 0x0001C849
    VMD_02RPS78 = 0x0001C892
    VMN_05LM02 = 0x0001C83E
    VMN_02LM11 = 0x0001C852

    def __str__(self) -> str:
        if self.value == self.BRDG_02R13:
            return "BRDG-02R13"
        if self.value == self.VMD_02RPS78:
            return "VMD-02RPS78"
        if self.value == self.VMN_05LM02:
            return "VMN-05LM02"
        if self.value == self.VMN_02LM11:
            return "VMN-02LM11"
        raise ValueError(f"Unknown product ID value {self.value}")


class BoundStatus(IntEnum):
    """RF device bound status."""

    NO_CHANGE = 0
    """No change in bound status."""
    REBOUND = 1
    """Device is re-bound to the same controller."""
    NEW_BOUND = 2
    """Device is bound for the first time to the controller."""

    def __str__(self) -> str:
        if self.value == self.NO_CHANGE:
            return "no_change"
        if self.value == self.REBOUND:
            return "rebound"
        if self.value == self.NEW_BOUND:
            return "new_bound"
        raise ValueError(f"Unknown bound status value {self.value}")


class RFCommStatus(IntEnum):
    """Node RF Communication status."""

    NO_ERROR = 0
    """No error."""
    ERROR = 1
    """No data received for 30 minutes."""

    def __str__(self) -> str:
        if self.value == self.NO_ERROR:
            return "no_error"
        if self.value == self.ERROR:
            return "error"
        raise ValueError(f"Unknown RF comm status {self.value}")


@dataclass
class BatteryStatus:
    """Node battery status."""

    available: bool
    """False means unknown or no battery present."""
    low: bool
    """True if battery is low. Meaningfull only if available is true."""


@dataclass
class FaultStatus:
    """Node fault status."""

    available: bool
    """False means unknown or device does not support faults."""
    fault: bool
    """True if faults are active. Meaningfull only if available is true."""


class ValueErrorStatus(IntEnum):
    """RF device value error status.

    This is when a value is out of range due to a broken sensor for example.
    """

    NO_ERROR = 0
    """No active value errors."""
    ERROR = 1
    """One or more value errors are active."""

    def __str__(self) -> str:
        if self.value == self.NO_ERROR:
            return "no_error"
        if self.value == self.ERROR:
            return "error"
        raise ValueError(f"Unknown value error status {self.value}")


@dataclass
class RFStats:
    """RF node statistics."""

    @dataclass
    class Record:  # pylint: disable=too-many-instance-attributes
        """RF statistic record."""

        device_id: int
        averate: int
        """Average received signal strength margin  of RF beacon (dB)."""
        stddev: float
        """Standard deviation of received signal strength margin of RF beacon (.1 dB)."""
        minimum: int
        """Lowest received signal strength (dB)."""
        maximum: int
        """Maximum received signal strength (dB)."""
        missed: int
        """Missed messages (%)."""
        received: int
        """Received beacons counter."""
        age: datetime.timedelta
        """Time since last beacon."""

    records: list[Record]


class BindingMode(IntEnum):
    """Binding mode."""

    OUTGOING_SINGLE_PRODUCT = 0x0003
    """Binds a controller."""
    OUTGOING_SINGLE_PRODUCT_PLUS_SERIAL = 0x0004
    """Binds a controller by RF address (serial number)."""
    INCOMING_ON_EXISTING_NODE = 0x0014
    """Abort an ongoing bind."""
    ABORT = 0x00C8


class BindingStatus(IntEnum):
    """Bind result."""

    NOT_AVAILABLE = 0
    """No binding initialized."""
    OUTGOING_BINDING_INITIALIZED = 1
    """Outgoing binding in process."""
    OUTGOING_BINDING_COMPLETED = 2
    """Outgoing binding completed."""
    INCOMING_BINDING_ACTIVE = 3
    """Incoming binding in process."""
    INCOMING_BINDING_COMPLETED = 4
    """Incoming binding completed."""
    LEARNING_COMPLETED = 5
    """Learning completed."""
    INCOMING_AUTODETECT_WINDOW_CLOSED = 10
    """Incoming binding autodection window closed."""
    OUTGOING_BINDING_FAILED_NO_ANSWER = 100
    """Outgoing binding failed, no answer."""
    OUTGOING_BINDING_FAILED_INCOMPATIBLE_DEVICE = 101
    """Outgoing binding failed, incompatible device."""
    OUTGOING_BINDING_FAILED_NODE_LIST_FULL = 102
    """Outgoing binding failed, node list full."""
    OUTGOING_BINDING_FAILED_MODBUS_ADDR_INVALID = 103
    """Outgoing binding failed, modbus address invalid."""
    INCOMING_BINDING_WINDOW_CLOSED_WITHOUT_BINDING_A_PRODUCT = 104
    """Incoming binding failed, window closed without binding a product."""
    BINDING_FAILED_SERIAL_NUMBER_INVALID = 105
    """Binding failed, invalid serial number."""
    UNKNOWN_BINDING_COMMAND = 200
    """Binding failed, unknown binding command."""
    UNKNOWN_PRODUCT_TYPE = 201
    """Binding failed, unknown product type."""

    def __str__(self) -> str:  # pylint: disable=too-many-return-statements,too-many-branches
        if self.value == self.NOT_AVAILABLE:
            return "not_available"
        if self.value == self.OUTGOING_BINDING_INITIALIZED:
            return "outgoing_binding_initialized"
        if self.value == self.OUTGOING_BINDING_COMPLETED:
            return "outgoing_binding_completed"
        if self.value == self.INCOMING_BINDING_ACTIVE:
            return "incoming_binding_active"
        if self.value == self.INCOMING_BINDING_COMPLETED:
            return "incoming_binding_completed"
        if self.value == self.LEARNING_COMPLETED:
            return "learning_completed"
        if self.value == self.INCOMING_AUTODETECT_WINDOW_CLOSED:
            return "incoming_autodetect_window_closed"
        if self.value == self.OUTGOING_BINDING_FAILED_NO_ANSWER:
            return "outgoing_binding_failed_no_answer"
        if self.value == self.OUTGOING_BINDING_FAILED_INCOMPATIBLE_DEVICE:
            return "outgoing_binding_failed_incompatible_device"
        if self.value == self.OUTGOING_BINDING_FAILED_NODE_LIST_FULL:
            return "outgoing_binding_failed_no_list_full"
        if self.value == self.OUTGOING_BINDING_FAILED_MODBUS_ADDR_INVALID:
            return "outgoing_binding_failed_modbus_address_invalid"
        if self.value == self.INCOMING_BINDING_WINDOW_CLOSED_WITHOUT_BINDING_A_PRODUCT:
            return "incoming_binding_window_closed_without_binding_a_product"
        if self.value == self.BINDING_FAILED_SERIAL_NUMBER_INVALID:
            return "binding_failed_serial_number_invalid"
        if self.value == self.UNKNOWN_BINDING_COMMAND:
            return "unknown_binding_command"
        if self.value == self.UNKNOWN_PRODUCT_TYPE:
            return "unknown_product_type"
        raise ValueError(f"Unknown binding status value {self.value}")


class ModbusEvents(IntEnum):
    """Modbus events enumeration."""

    NO_EVENTS = 0
    """No modbus events are generated."""
    BRIDGE_EVENTS = 1
    """Modbus function 'bridge event' is sent to master when a value is changed."""
    NODE_EVENTS = 2
    """Modbus function 'node event' is sent to master when a value is changed."""
    DATA_EVENTS = 3
    """Modbus function 'data event' is sent to master when a value is changed."""

    def __str__(self):
        if self.value == self.NO_EVENTS:
            return "no_events"
        if self.value == self.BRIDGE_EVENTS:
            return "bridge_events"
        if self.value == self.NODE_EVENTS:
            return "node_events"
        if self.value == self.DATA_EVENTS:
            return "data_events"
        raise ValueError(f"Unknown modbus event value {self.value}")


class ResetMode(IntEnum):
    """Reset modes."""

    SOFT_RESET = 12345
    """Soft reset."""
    FACTORY_RESET = 56789
    """Factory reset"""


class Baudrate(IntEnum):
    """Serial port baudrate."""

    BAUD_300 = 0
    BAUD_600 = 1
    BAUD_1200 = 2
    BAUD_2400 = 3
    BAUD_4800 = 4
    BAUD_9600 = 5
    BAUD_19200 = 6
    BAUD_38400 = 7
    BAUD_57600 = 8
    BAUD_115200 = 9


class Parity(IntEnum):
    """Serial port parity."""

    PARITY_NONE = 0
    PARITY_ODD = 1
    PARITY_EVEN = 2


class StopBits(IntEnum):
    """Serial port stop bits."""

    STOP_0 = 0
    STOP_1 = 1


class VMDSensorStatus(IntEnum):
    """VMD sensor status."""

    UNAVAILABLE = auto()
    OK = auto()
    ERROR = auto()


class VMDHeaterStatus(IntEnum):
    """VMD heater status."""

    OK = 1
    UNAVAILABLE = 2


@dataclass
class VMDTemperature:
    """VMD temperature sample."""

    temperature: float
    status: VMDSensorStatus


@dataclass
class VMDHeater:
    """VMD heater state sample."""

    level: int
    status: VMDHeaterStatus


class VMDCapabilities(Flag):
    """Ventilation unit capabilities."""

    PRE_HEATER_AVAILABLE = 0x0001
    POST_HEATER_AVAILABLE = 0x0002
    RESERVED = 0x0004
    NIGHT_MODE_CAPABLE = 0x0008
    SPEED_10_CAPABLE = 0x0010
    SPEED_9_CAPABLE = 0x0020
    SPEED_8_CAPABLE = 0x0040
    SPEED_7_CAPABLE = 0x0080
    SPEED_6_CAPABLE = 0x0100
    SPEED_5_CAPABLE = 0x0200
    SPEED_4_CAPABLE = 0x0400
    AUTO_MODE_CAPABLE = 0x0800
    BOOST_MODE_CAPABLE = 0x1000
    TIMER_CAPABLE = 0x2000
    UNKNOWN = 0x4000
    OFF_CAPABLE = 0x8000


class VMDFaultStatus(IntEnum):
    """VMD fault status codes."""

    OK = 0
    FAN_FAILURE = 1


class VMDVentilationSpeed(IntEnum):
    """Ventilation unit speed preset."""

    OFF = 0
    LOW = 1
    MID = 2
    HIGH = 3
    OVERRIDE_LOW = 11
    OVERRIDE_MID = 12
    OVERRIDE_HIGH = 13
    AWAY = 21
    BOOST = 23
    AUTO = 24

    def __str__(self) -> str:  # pylint: disable=too-many-return-statements
        if self.value == self.OFF:
            return "Off"
        if self.value == self.LOW:
            return "Low"
        if self.value == self.MID:
            return "Mid"
        if self.value == self.HIGH:
            return "High"
        if self.value == self.OVERRIDE_LOW:
            return "Low (temporary override)"
        if self.value == self.OVERRIDE_MID:
            return "Mid (temporary override)"
        if self.value == self.OVERRIDE_HIGH:
            return "High (temporary override)"
        if self.value == self.AWAY:
            return "Away"
        if self.value == self.BOOST:
            return "Boost"
        if self.value == self.AUTO:
            return "Auto"
        raise ValueError(f"Unknown ventilation speed value {self.value}")


class VMDRequestedVentilationSpeed(IntEnum):
    """VMD Requested ventilation speed codes."""

    OFF = 0
    AWAY = 1
    LOW = 2
    MID = 3
    HIGH = 4
    AUTO = 5
    BOOST = 7

    def __str__(self) -> str:  # pylint: disable=too-many-return-statements
        if self.value == self.OFF:
            return "Off"
        if self.value == self.LOW:
            return "Low"
        if self.value == self.MID:
            return "Mid"
        if self.value == self.HIGH:
            return "High"
        if self.value == self.AWAY:
            return "Away"
        if self.value == self.BOOST:
            return "Boost"
        if self.value == self.AUTO:
            return "Auto"
        raise ValueError(f"Unknown requested ventilation speed value {self.value}")

    @classmethod
    def parse(cls, value: str):  # pylint: disable=too-many-return-statements
        """Instantiate by string."""
        if value.casefold() == "off".casefold():
            return cls(cls.OFF)
        if value.casefold() == "low".casefold():
            return cls(cls.LOW)
        if value.casefold() == "mid".casefold():
            return cls(cls.MID)
        if value.casefold() == "high".casefold():
            return cls(cls.HIGH)
        if value.casefold() == "away".casefold():
            return cls(cls.AWAY)
        if value.casefold() == "boost".casefold():
            return cls(cls.BOOST)
        if value.casefold() == "auto".casefold():
            return cls(cls.AUTO)
        raise ValueError(f"Unknown requested ventilation speed value {value}")


class ValueStatusFlags(Flag):
    """Register value status flags."""

    VALID = 0x01
    """Data is valid. Invalid means never written/received."""
    ERROR = 0x02
    """Value has an error, for example a sensor error."""
    READ_PENDING = 0x04
    """Value has a read pending."""
    WRITE_PENDING = 0x08
    """Value has a write pending."""
    NEW_VALUE = 0x40
    """There is a new value cached in the bridge."""


class ValueStatusSource(IntEnum):
    """Register value source."""

    UNKNOWN = 0
    """Unknown, never written or received."""
    RF = 1
    """Value is from RF."""
    MODBUS = 2
    """Value is from Modbus interface."""

    def __str__(self) -> str:
        if self.value == self.UNKNOWN:
            return "Unknown"
        if self.value == self.RF:
            return "RF"
        if self.value == self.MODBUS:
            return "Modbus"
        raise ValueError(f"Unknown value source value {self.value}")


class VMDErrorCode(IntEnum):
    """Ventilation unit error codes."""

    NO_ERROR = 0
    NON_SPECIFIC_FAULT = 1
    EMERGENCY_STOP = 2
    FAN_1_ERROR = 3
    X22_SENSOR_ERROR = 4
    X23_SENSOR_ERROR = 5
    X21_SENSOR_ERROR = 6
    X20_SENSOR_ERROR = 7
    FAN_2_ERROR = 8
    BINDING_MODE_ACTIVE = 254
    IDENTIFICATION_ACTIVE = 255

    def __str__(self) -> str:  # pylint: disable=too-many-return-statements
        if self.value == self.NO_ERROR:
            return "no_error"
        if self.value == self.NON_SPECIFIC_FAULT:
            return "non_specific_fault"
        if self.value == self.EMERGENCY_STOP:
            return "emergency_stop"
        if self.value == self.FAN_1_ERROR:
            return "fan_1_error"
        if self.value == self.X22_SENSOR_ERROR:
            return "x22_sensor_error"
        if self.value == self.X23_SENSOR_ERROR:
            return "x23_sensor_error"
        if self.value == self.X21_SENSOR_ERROR:
            return "x21_sensor_error"
        if self.value == self.X20_SENSOR_ERROR:
            return "x20_sensor_error"
        if self.value == self.FAN_2_ERROR:
            return "fan_2_error"
        if self.value == self.BINDING_MODE_ACTIVE:
            return "binding_mode_active"
        if self.value == self.IDENTIFICATION_ACTIVE:
            return "identification_active"
        raise ValueError(f"Unknown error code {self.value}")


class VMDBypassMode(IntEnum):
    """VMD bypass mode codes."""

    CLOSE = 0
    OPEN = 100
    UNKNOWN = 239
    AUTO = 255

    def __str__(self) -> str:
        if self.value == self.CLOSE:
            return "closed"
        if self.value == self.OPEN:
            return "open"
        if self.value == self.UNKNOWN:
            return "unknown"
        if self.value == self.AUTO:
            return "auto"
        raise ValueError(f"Unknown bypass mode {self.value}")

    @classmethod
    def parse(cls, value: str):
        """Instantiate by string."""
        if value.casefold() == "close".casefold():
            return cls(cls.CLOSE)
        if value.casefold() == "open".casefold():
            return cls(cls.OPEN)
        if value.casefold() == "auto".casefold():
            return cls(cls.AUTO)
        raise ValueError(f"Unknown bypass mode {value}")


@dataclass
class VMDBypassPosition:
    """VMD bypass position sample."""

    position: int
    error: bool
