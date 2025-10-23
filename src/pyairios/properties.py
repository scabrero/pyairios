"""Airios devices properties."""

from enum import Enum, auto


class AiriosBaseProperty(Enum):
    """Base property class."""


class AiriosDeviceProperty(AiriosBaseProperty):
    """Generic device properties."""

    # The RAMSES-II RF address, also used as node serial number.
    RF_ADDRESS = auto()

    # This is the value assigned to the virtual node instance created by the bridge when
    # a device is bound. The actual received product ID from the real RF node is available
    # as RECEIVED_PRODUCT_ID property.
    PRODUCT_ID = auto()

    # The node software version.
    SOFTWARE_VERSION = auto()

    # The node OEM number. All nodes in the RF network must use the same value.
    OEM_NUMBER = auto()

    # The RF capabilities. The value depends on the specific device.
    RF_CAPABILITIES = auto()

    # The node manufacture date.
    MANUFACTURE_DATE = auto()

    # The node software build date.
    SOFTWARE_BUILD_DATE = auto()

    # The node product name.
    PRODUCT_NAME = auto()

    RF_LAST_SEEN = auto()
    RF_COMM_STATUS = auto()
    BATTERY_STATUS = auto()
    FAULT_STATUS = auto()


class AiriosNodeProperty(AiriosBaseProperty):
    """Node properties."""

    # This is the value received from the bound node. If it does not match register
    # NODE_PRODUCT_ID a wrong product is bound.
    RECEIVED_PRODUCT_ID = auto()
    VALUE_ERROR_STATUS = auto()
    RF_LAST_RSSI = auto()
    BOUND_STATUS = auto()


class AiriosBridgeProperty(AiriosBaseProperty):
    """RF bridge properties."""

    CUSTOMER_PRODUCT_ID = auto()
    UTC_TIME = auto()
    LOCAL_TIME = auto()
    UPTIME = auto()
    DAYLIGHT_SAVING_TYPE = auto()
    TIMEZONE_OFFSET = auto()
    OEM_CODE = auto()
    MODBUS_EVENTS = auto()
    RESET_DEVICE = auto()
    CUSTOMER_SPECIFIC_NODE_ID = auto()
    SERIAL_PARITY = auto()
    SERIAL_STOP_BITS = auto()
    SERIAL_BAUDRATE = auto()
    MODBUS_DEVICE_ID = auto()
    MESSAGES_SEND_CURRENT_HOUR = auto()
    MESSAGES_SEND_LAST_HOUR = auto()
    RF_LOAD_CURRENT_HOUR = auto()
    RF_LOAD_LAST_HOUR = auto()
    BINDING_PRODUCT_ID = auto()
    BINDING_PRODUCT_SERIAL = auto()
    BINDING_COMMAND = auto()
    CREATE_NODE = auto()
    FIRST_ADDRESS_TO_ASSIGN = auto()
    REMOVE_NODE = auto()
    ACTUAL_BINDING_STATUS = auto()
    NUMBER_OF_NODES = auto()
    ADDRESS_NODE_1 = auto()
    ADDRESS_NODE_2 = auto()
    ADDRESS_NODE_3 = auto()
    ADDRESS_NODE_4 = auto()
    ADDRESS_NODE_5 = auto()
    ADDRESS_NODE_6 = auto()
    ADDRESS_NODE_7 = auto()
    ADDRESS_NODE_8 = auto()
    ADDRESS_NODE_9 = auto()
    ADDRESS_NODE_10 = auto()
    ADDRESS_NODE_11 = auto()
    ADDRESS_NODE_12 = auto()
    ADDRESS_NODE_13 = auto()
    ADDRESS_NODE_14 = auto()
    ADDRESS_NODE_15 = auto()
    ADDRESS_NODE_16 = auto()
    ADDRESS_NODE_17 = auto()
    ADDRESS_NODE_18 = auto()
    ADDRESS_NODE_19 = auto()
    ADDRESS_NODE_20 = auto()
    ADDRESS_NODE_21 = auto()
    ADDRESS_NODE_22 = auto()
    ADDRESS_NODE_23 = auto()
    ADDRESS_NODE_24 = auto()
    ADDRESS_NODE_25 = auto()
    ADDRESS_NODE_26 = auto()
    ADDRESS_NODE_27 = auto()
    ADDRESS_NODE_28 = auto()
    ADDRESS_NODE_29 = auto()
    ADDRESS_NODE_30 = auto()
    ADDRESS_NODE_31 = auto()
    ADDRESS_NODE_32 = auto()


class AiriosVMDProperty(AiriosBaseProperty):
    """VMD devices properties."""

    CURRENT_VENTILATION_SPEED = auto()
    FAN_SPEED_EXHAUST = auto()
    FAN_SPEED_SUPPLY = auto()
    ERROR_CODE = auto()
    VENTILATION_SPEED_OVERRIDE_REMAINING_TIME = auto()

    TEMPERATURE_INLET = auto()
    """Incoming air temperature before heat exchanger."""

    TEMPERATURE_OUTLET = auto()
    """Outgoing air temperature after the heat exchanger."""

    TEMPERATURE_EXHAUST = auto()
    """Outgoing air temperature before the heat exchanger."""

    TEMPERATURE_SUPPLY = auto()
    """Incoming air temperature after heat exchanger."""

    PREHEATER = auto()
    FILTER_DIRTY = auto()
    DEFROST = auto()
    BYPASS_POSITION = auto()
    HUMIDITY_INDOOR = auto()
    HUMIDITY_OUTDOOR = auto()
    FLOW_INLET = auto()
    FLOW_OUTLET = auto()
    AIR_QUALITY = auto()
    AIR_QUALITY_BASIS = auto()
    CO2_LEVEL = auto()
    CO2_CONTROL_SETPOINT = auto()
    POSTHEATER = auto()
    CAPABILITIES = auto()
    FILTER_REMAINING_DAYS = auto()
    FILTER_DURATION = auto()
    FILTER_REMAINING_PERCENT = auto()
    FAN_RPM_EXHAUST = auto()
    FAN_RPM_SUPPLY = auto()
    BYPASS_MODE = auto()
    BYPASS_STATUS = auto()
    REQUESTED_VENTILATION_SPEED = auto()
    OVERRIDE_TIME_SPEED_LOW = auto()
    OVERRIDE_TIME_SPEED_MID = auto()
    OVERRIDE_TIME_SPEED_HIGH = auto()
    REQUESTED_BYPASS_MODE = auto()
    FILTER_RESET = auto()
    FAN_SPEED_AWAY_SUPPLY = auto()
    FAN_SPEED_AWAY_EXHAUST = auto()
    FAN_SPEED_LOW_SUPPLY = auto()
    FAN_SPEED_LOW_EXHAUST = auto()
    FAN_SPEED_MID_SUPPLY = auto()
    FAN_SPEED_MID_EXHAUST = auto()
    FAN_SPEED_HIGH_SUPPLY = auto()
    FAN_SPEED_HIGH_EXHAUST = auto()
    FROST_PROTECTION_PREHEATER_SETPOINT = auto()
    PREHEATER_SETPOINT = auto()
    FREE_VENTILATION_HEATING_SETPOINT = auto()
    FREE_VENTILATION_COOLING_OFFSET = auto()

    VENTILATION_MODE = auto()
    REQUESTED_VENTILATION_MODE = auto()
    VENTILATION_SUB_MODE = auto()
    REQUESTED_VENTILATION_SUB_MODE = auto()
    TEMP_VENTILATION_MODE = auto()
    REQUESTED_TEMP_VENTILATION_MODE = auto()
    TEMP_VENTILATION_SUB_MODE = auto()
    REQUESTED_TEMP_VENTILATION_SUB_MODE = auto()
    BASIC_VENTILATION_ENABLE = auto()
    BASIC_VENTILATION_LEVEL = auto()
    TEMP_OVERRIDE_DURATION = auto()
    PRODUCT_VARIANT = auto()
    SYSTEM_VENTILATION_CONFIGURATION = auto()


class AiriosVMNProperty(AiriosBaseProperty):
    """VMN devices properties."""

    REQUESTED_VENTILATION_SPEED = auto()
