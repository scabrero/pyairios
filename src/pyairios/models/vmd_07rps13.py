"""Airios VMD-07RPS13 ClimaRad Ventura V1 controller implementation."""

from __future__ import annotations

import datetime
import logging
import math
from typing import List

from pyairios.client import AsyncAiriosModbusClient
from pyairios.constants import (
    ValueStatusFlags,
    ValueStatusSource,
    VMDBypassPosition,
    VMDCapabilities,
    VMDErrorCode,
    VMDHeater,
    VMDHeaterStatus,
    VMDSensorStatus,
    VMDTemperature,
    VMDVentilationMode,
    VMDVentilationSpeed,
)
from pyairios.data_model import AiriosDeviceData
from pyairios.exceptions import AiriosInvalidArgumentException
from pyairios.models.vmd_base import VmdBase
from pyairios.node import _safe_fetch
from pyairios.registers import (
    FloatRegister,
    RegisterAddress,
    RegisterBase,
    Result,
    ResultStatus,
    U8Register,
    U16Register,
)

LOGGER = logging.getLogger(__name__)


# Linking the registers:
#   Reg:
#       model set of RF Bridge register addresses, by named address keyword
#   Data:
#       model dict of register address + Result type by name (formerly in data_model.py)
#   Node.vmd_registers:
#       instance list of register type (size) + name key from Reg + access R/W


class Reg(RegisterAddress):  # only override or add differences in VMD_BASE
    """The Register set for VMD-07RPS13 ClimaRad Ventura V1 controller node."""

    # numbers between "#" are from oem docs
    # R
    BYPASS_POSITION = 41015  # 28 # 1, RO, uint8, "Bypass Position"
    CO2_LEVEL = 41008  # 17 # 1, RO, uint16, "Main Room Exhaust CO2 Level"
    ERROR_CODE = 41032  # 23 #  1, RO, uint8, "Error Code"
    FAN_SPEED_EXHAUST = 41019  # 9 # 1, RO, uint8, "Main Room Fan speed Exhaust"
    FAN_SPEED_SUPPLY = 41020  # 10 # 1, RO, uint8 "Main Room Fan speed Inlet"
    FILTER_DIRTY = 41017  # 1, RO, uint8, "Filter Dirty"
    FILTER_DURATION = 41029  # 1, RO, uint16, "Air Filter Time Duration"
    FILTER_REMAINING_DAYS = 41028  # 1, RO, uint16, "Air Filter Time Remaining"
    FILTER_REMAINING_PERCENT = 41030  # 1, RO, uint8, "Air Filter Time Percent"
    FLOW_INLET = 41024  # L=2, RO, float, "Inlet Flow level"
    FLOW_OUTLET = 41026  # L=2, RO, float, "Outlet Flow level"
    HUMIDITY_INDOOR = 41007  # 15 # 1, RO, uint8, "Main Room Exhaust Humidity Level"
    HUMIDITY_OUTDOOR = 41002  # 1, RO, uint8, "Outlet Humidity"
    INLET_FLOW = 41024  # 2, RO, float, "Inlet Flow level"
    OUTLET_FLOW = 41026  # 2, RO, float, "Outlet Flow level"
    POST_HEATER_DEMAND = 41023  # 1, RO, uint8, "Postheater Demand"
    TEMPERATURE_EXHAUST = 41005  # 12 # L=2, RO, float, "Main Room Exhaust Temperature"
    TEMPERATURE_INLET = 41003  # L=2, RO, float, "Inlet Temperature"
    TEMPERATURE_OUTLET = 41000  #  L=2, RO, float, "Outlet Temperature"
    TEMP_VENT_MODE = 41103  # 1,R, uint8, "Main Room Ventilation Mode"
    TEMP_VENT_SUB_MODE = 41104  # 1, R, uint8, "Main Room Ventilation Sub Mode"
    VENT_MODE = 41100  # 1, R, uint8, "Main Room Ventilation Mode"
    VENT_SUB_MODE = 41101  # 1, R, uint8, "Main Room Ventilation Sub Mode"
    VENT_SUB_MODE_EXH = 41102  # R, uint8, Main Room Vent. Sub Mode Cont. Exh.
    # R/W
    BASIC_VENT_ENABLE = 42000  # 1, RW, uint8, "Basic Ventilation Enable"
    BASIC_VENT_LEVEL = 42001  # 1, RW, uint8, "Basic Ventilation Level"
    CO2_CONTROL_SETPOINT = 42011  # 1, RW, uint16, "CO2 Control Setpoint"
    FILTER_RESET = 41151  # 1, RW, uint8, "Reset Air Filter Timer"
    OVERRIDE_TIME_MANUAL = 42009  # 115 # RW, uint16 "Temporary Override Duration"
    PRODUCT_VARIANT = 42010  # 1,RW, uint8, "Product Variant" = 0?
    REQ_TEMP_VENT_MODE = 41123  # 1,RW, uint8, "Main Room Temp.Ventilation Mode"
    REQ_TEMP_VENT_SUB_MODE = 41124  # 1, RW, uint8, "Main Room Vent. Sub Mode"
    # REQ_TEMP_VENT_SUB_MODE_EXH = (41125  # RW, uint8, Main Room Temp. Vent. Sub Mode Cont. Exh.)
    REQ_VENT_MODE = 41120  # 1,RW, uint8, "Main Room Ventilation Mode"
    REQ_VENT_SUB_MODE = 41121  # 1, RW, uint8, "Main Room Ventilation Sub Mode"
    # REQ_VENT_SUB_MODE_EXH = 41122  # 1, R, uint8, "Main Room Vent. Sub Mode Cont. Exh."
    # ROOM_INSTANCE = 41126  # 1, RW, uint8, "Room instance" send before setting REQ_xxx
    SET_PERSON_PRESENT = 41150  # 1, RW, uint8, "Set Person Present"
    SYSTEM_VENT_CONFIG = 42021  # 1, RW, uint8, "System Ventilation Configuration"


class NodeData(AiriosDeviceData):
    """
    VMD-07RPS13 ClimaRad Ventura V1C/V1D/V1X node data.
    source: ClimaRad Modbus Registers Specs 2024
    """

    basic_ventilation_enable: Result[int] | None
    bypass_position: Result[VMDBypassPosition] | None
    co2_control_setpoint: Result[int] | None
    co2_level: Result[int] | None
    error_code: Result[VMDErrorCode] | None
    exhaust_air_temperature: Result[VMDTemperature] | None
    exhaust_fan_speed: Result[int] | None
    filter_dirty: Result[int] | None
    filter_remaining_days: Result[int] | None
    filter_remaining_percent: Result[int] | None
    indoor_air_temperature: Result[VMDTemperature] | None
    product_variant: Result[int] | None
    supply_air_temperature: Result[VMDTemperature] | None
    supply_fan_speed: Result[int] | None
    system_ventilation_config: Result[int] | None
    temp_ventilation_mode: Result[int] | None
    temp_ventilation_sub_mode: Result[int] | None
    ventilation_mode: Result[int] | None
    ventilation_sub_mode: Result[int] | None
    ventilation_speed: Result[int] | None  # required for HA fan


def pr_id() -> int:
    # for key VMD_07RPS13
    return 0x0001C883


def product_descr() -> str | tuple[str, ...]:
    # for key VMD_07RPS13
    return "ClimaRad Ventura V1"


class Node(VmdBase):
    """Represents a VMD-07RPS13 Ventura V1 controller node. HACK in client to access WRITE"""

    def __init__(self, slave_id: int, client: AsyncAiriosModbusClient) -> None:
        """Initialize the VMD-07RPS13 Ventura controller node instance."""
        super().__init__(slave_id, client)
        LOGGER.debug(f"Starting Ventura Node({slave_id})")

        vmd_registers: List[RegisterBase] = [
            FloatRegister(Reg.TEMPERATURE_EXHAUST, self.read_status),
            FloatRegister(Reg.TEMPERATURE_INLET, self.read_status),
            FloatRegister(Reg.TEMPERATURE_OUTLET, self.read_status),
            # FloatRegister(Reg.TEMPERATURE_SUPPLY, self.read_status),
            U8Register(Reg.BASIC_VENT_ENABLE, self.read_write_status),
            U8Register(Reg.BASIC_VENT_LEVEL, self.read_write_status),
            U8Register(Reg.BYPASS_POSITION, self.read_status),
            U16Register(Reg.CO2_CONTROL_SETPOINT, self.read_write),
            U16Register(Reg.CO2_LEVEL, self.read_status),
            U8Register(Reg.ERROR_CODE, self.read_status),
            U8Register(Reg.FAN_SPEED_EXHAUST, self.read_status),
            U8Register(Reg.FAN_SPEED_SUPPLY, self.read_status),
            U8Register(Reg.FILTER_DIRTY, self.read_status),
            # U16Register(Reg.FILTER_DURATION, self.read_status),
            U16Register(Reg.FILTER_REMAINING_DAYS, self.read_status),
            U8Register(Reg.FILTER_REMAINING_PERCENT, self.read_status),
            U8Register(Reg.FILTER_RESET, self.write_status),
            U8Register(Reg.HUMIDITY_INDOOR, self.read_status),
            U8Register(Reg.HUMIDITY_OUTDOOR, self.read_status),
            U16Register(Reg.OVERRIDE_TIME_MANUAL, self.read_write),
            U8Register(Reg.POST_HEATER_DEMAND, self.read_status),
            U8Register(Reg.PRODUCT_VARIANT, self.read_write_status),  # UINT8?
            U8Register(Reg.REQ_TEMP_VENT_MODE, self.read_write_status),
            U8Register(Reg.REQ_TEMP_VENT_SUB_MODE, self.read_write_status),
            U8Register(Reg.REQ_VENT_MODE, self.read_write_status),
            U8Register(Reg.REQ_VENT_SUB_MODE, self.read_write_status),
            # U8Register(Reg.ROOM_INSTANCE, self.read_write_status),
            U8Register(Reg.SYSTEM_VENT_CONFIG, self.read_write_status),
            U8Register(Reg.TEMP_VENT_MODE, self.read_status),
            U8Register(Reg.TEMP_VENT_SUB_MODE, self.read_status),
            U8Register(Reg.VENT_MODE, self.read_status),
            U8Register(Reg.VENT_SUB_MODE, self.read_status),
        ]
        self._add_registers(vmd_registers)

    # getters and setters

    async def capabilities(self) -> Result[VMDCapabilities] | None:
        """Get the ventilation unit capabilities.
        Capabilities register not supported on VMD-07RPS13, so must simulate"""
        # Ventura capabilities:
        _caps = VMDCapabilities.NO_CAPABLE  #  | VMDCapabilities.AUTO_MODE_CAPABLE
        return Result(
            _caps,
            ResultStatus(
                datetime.timedelta(1000), ValueStatusSource.UNKNOWN, ValueStatusFlags.VALID
            ),
        )

    async def system_ventilation_configuration(self) -> Result[int]:
        """Get the system ventilation configuration status."""
        return await self.client.get_register(self.regmap[Reg.SYSTEM_VENT_CONFIG], self.slave_id)

    async def vent_mode(self) -> Result[int]:
        """Get the ventilation mode status. 0=Off, 1=Pause, 2=On, 3=Man1, 5=Man3, 8=Service"""
        # seen: 0 (with temp_vent_mode 3) | 1 = Pause | 2 = On (with vent_sub_mode 48)
        return await self.client.get_register(self.regmap[Reg.VENT_MODE], self.slave_id)

    async def rq_vent_mode(self) -> Result[int]:
        """Get the ventilation mode status. 0=Off, 2=On, 3=Man1, 5=Man3, 8=Service"""
        return await self.client.get_register(self.regmap[Reg.REQ_VENT_MODE], self.slave_id)

    async def set_rq_vent_mode(self, mode: int) -> bool:  # : VMDVentilationMode) -> bool:
        """Set the ventilation mode. 0=Off, 1=Pause, 2=On, 3=Man1, 5=Man3, 8=Service"""
        if mode == VMDVentilationMode.UNKNOWN:
            raise AiriosInvalidArgumentException(f"Invalid ventilation mode {mode}")
        return await self.client.set_register(self.regmap[Reg.REQ_VENT_MODE], mode, self.slave_id)

    async def rq_vent_sub_mode(self) -> Result[int]:
        """Get the ventilation mode status. 0=Off/Pause, 2=On, 3=Man1, 5=Man3, 8=Service"""
        return await self.client.get_register(self.regmap[Reg.REQ_VENT_SUB_MODE], self.slave_id)

    async def set_rq_vent_sub_mode(self, mode: int) -> bool:  # : VMDVentilationMode) -> bool:
        """Set the ventilation mode. 0=Off/Pause, 48=Auto"""
        if mode == VMDVentilationMode.UNKNOWN:
            raise AiriosInvalidArgumentException(f"Invalid ventilation mode {mode}")
        return await self.client.set_register(
            self.regmap[Reg.REQ_VENT_SUB_MODE], mode, self.slave_id
        )

    async def rq_temp_vent_mode(self) -> Result[int]:
        """Get the temp ventilation mode status. 0=Off, 1=Pause, 2=On, 3=Man1, 5=Man3, 8=Service"""
        return await self.client.get_register(self.regmap[Reg.REQ_TEMP_VENT_MODE], self.slave_id)

    async def set_rq_temp_vent_mode(self, mode: int) -> bool:  # : VMDVentilationMode) -> bool:
        """Set the temp ventilation mode. 0=Off, 1=Pause, 2=On, 3=Man1, 5=Man3, 8=Service"""
        if mode == VMDVentilationMode.UNKNOWN:
            raise AiriosInvalidArgumentException(f"Invalid ventilation mode {mode}")
        return await self.client.set_register(
            self.regmap[Reg.REQ_TEMP_VENT_MODE], mode, self.slave_id
        )

    async def rq_temp_vent_sub_mode(self) -> Result[int]:
        """Get the temp ventilation sub mode status. 0=Off/Pause, 201, ..."""
        return await self.client.get_register(
            self.regmap[Reg.REQ_TEMP_VENT_SUB_MODE], self.slave_id
        )

    async def set_rq_temp_vent_sub_mode(self, mode: int) -> bool:  # : VMDVentilationMode) -> bool:
        """Set the temp ventilation sub mode. 0=Off/Pause, 201, ..."""
        if mode == VMDVentilationMode.UNKNOWN:
            raise AiriosInvalidArgumentException(f"Invalid ventilation mode {mode}")
        return await self.client.set_register(
            self.regmap[Reg.REQ_TEMP_VENT_SUB_MODE], mode, self.slave_id
        )

    async def vent_sub_mode(self) -> Result[int]:
        """Get the ventilation sub mode status."""
        # seen: 0 | 48
        return await self.client.get_register(self.regmap[Reg.VENT_SUB_MODE], self.slave_id)

    async def temp_vent_mode(self) -> Result[int]:
        """Get the temporary ventilation mode status."""
        # seen: 0 (with Ventilation mode != 0) | 3
        return await self.client.get_register(self.regmap[Reg.TEMP_VENT_MODE], self.slave_id)

    async def temp_vent_sub_mode(self) -> Result[int]:
        """Get the temporary ventilation sub mode status."""
        # seen: 0 (with temp_vent_mode 3) | 201 | 202 | .. | 205
        return await self.client.get_register(self.regmap[Reg.TEMP_VENT_SUB_MODE], self.slave_id)

    # async def room_instance(self) -> Result[int]:
    #     """Get the room_instance: 1 = Main or 2 = Secondary"""
    #     return await self.client.get_register(self.regmap[Reg.ROOM_INSTANCE], self.slave_id)
    #
    # async def set_room_instance(self, mode: int) -> bool:
    #     """Set the room_instance: 1 = Main or 2 = Secondary"""
    #     return await self.client.set_register(
    #         self.regmap[Reg.ROOM_INSTANCE], mode, self.slave_id
    #     )

    async def bypass_position(self) -> Result[VMDBypassPosition]:
        """Get the bypass position."""
        regdesc = self.regmap[Reg.BYPASS_POSITION]
        result = await self.client.get_register(regdesc, self.slave_id)
        error = result.value > 120
        return Result(VMDBypassPosition(result.value, error), result.status)

    async def basic_vent_enable(self) -> Result[int]:
        """Get base ventilation enabled."""
        return await self.client.get_register(self.regmap[Reg.BASIC_VENT_ENABLE], self.slave_id)

    async def set_basic_vent_enable(self, mode: int) -> bool:
        """Set base ventilation enabled/disabled."""
        return await self.client.set_register(
            self.regmap[Reg.BASIC_VENT_ENABLE], mode, self.slave_id
        )

    async def basic_vent_level(self) -> Result[int]:
        """Get base ventilation level."""
        return await self.client.get_register(self.regmap[Reg.BASIC_VENT_LEVEL], self.slave_id)

    async def set_basic_vent_level(self, level: int) -> bool:
        """Set the base ventilation level."""
        return await self.client.set_register(
            self.regmap[Reg.BASIC_VENT_LEVEL], level, self.slave_id
        )

    async def ventilation_speed(self) -> Result[VMDVentilationSpeed]:
        """Get the ventilation unit active speed preset."""

        # Automatic:
        # Ventilation mode:        2
        # Ventilation sub mode:    48
        # Temp. Ventil. mode:      0
        # Temp. Ventil. sub mode:  0
        #
        # Pause:
        # Ventilation mode:        1
        # Ventilation sub mode:    0
        # Temp. Ventil. mode:      1
        # Temp. Ventil. sub mode:  0
        #
        # Manual/temp 1:
        # Ventilation mode:        0
        # Ventilation sub mode:    0
        # Temp. Ventil. mode:      3
        # Temp. Ventil. sub mode:  201
        #
        # Manual/temp 2:
        # Ventilation mode:        0
        # Ventilation sub mode:    0
        # Temp. Ventil. mode:      3
        # Temp. Ventil. sub mode:  202
        #
        # Ventilation mode:        0
        # Ventilation sub mode:    0
        # Temp. Ventil. mode:      3
        # Temp. Ventil. sub mode:  203
        #
        # Stand 5 == Boost >>
        # Ventilation mode:        0
        # Ventilation sub mode:    0
        # Temp. Ventil. mode:      3
        # Temp. Ventil. sub mode:  205

        mode = await self.client.get_register(self.regmap[Reg.VENT_MODE], self.slave_id)
        man_step = await self.client.get_register(
            self.regmap[Reg.TEMP_VENT_SUB_MODE], self.slave_id
        )
        speed = VMDVentilationSpeed.OFF
        if mode.value == 2:
            speed = VMDVentilationSpeed.AUTO
        elif mode.value == 1:
            speed = VMDVentilationSpeed.AWAY
        elif mode.value == 0:
            if man_step.value <= 202:
                speed = VMDVentilationSpeed.OVERRIDE_LOW
            elif man_step.value <= 203:
                speed = VMDVentilationSpeed.OVERRIDE_MID
            elif man_step.value <= 205:
                speed = VMDVentilationSpeed.OVERRIDE_HIGH
        return Result(speed, mode.status)

    async def product_variant(self) -> Result[int]:
        """Get the product variant."""
        regdesc = self.regmap[Reg.PRODUCT_VARIANT]
        return await self.client.get_register(regdesc, self.slave_id)

    async def co2_level(self) -> Result[int]:
        """Get the CO2 level (in ppm)."""
        regdesc = self.regmap[Reg.CO2_LEVEL]
        return await self.client.get_register(regdesc, self.slave_id)

    async def co2_setpoint(self) -> Result[int]:
        """Get the CO2 control setpoint (in ppm)."""
        regdesc = self.regmap[Reg.CO2_CONTROL_SETPOINT]
        return await self.client.get_register(regdesc, self.slave_id)

    async def set_co2_setpoint(self, setpnt: int) -> bool:
        """Set the CO2 control setpoint (in ppm)."""
        return await self.client.set_register(
            self.regmap[Reg.CO2_CONTROL_SETPOINT], setpnt, self.slave_id
        )

    async def filter_duration(self) -> Result[int]:
        """Get the filter duration (in days)."""
        return await self.client.get_register(self.regmap[Reg.FILTER_DURATION], self.slave_id)

    async def filter_remaining_days(self) -> Result[int]:
        """Get the filter remaining lifetime (in days)."""
        return await self.client.get_register(self.regmap[Reg.FILTER_REMAINING_DAYS], self.slave_id)

    async def filter_remaining_percent(self) -> Result[int]:
        """Get the filter remaining lifetime (in %)."""
        return await self.client.get_register(
            self.regmap[Reg.FILTER_REMAINING_PERCENT], self.slave_id
        )

    async def filter_reset(self) -> bool:
        """Reset the filter dirty status."""
        return await self.client.set_register(self.regmap[Reg.FILTER_RESET], 0, self.slave_id)

    async def filter_dirty(self) -> Result[int]:
        """Get the filter dirty status."""
        return await self.client.get_register(self.regmap[Reg.FILTER_DIRTY], self.slave_id)

    async def error_code(self) -> Result[VMDErrorCode]:
        """Get the ventilation unit error code."""
        regdesc = self.regmap[Reg.ERROR_CODE]
        result = await self.client.get_register(regdesc, self.slave_id)
        return Result(VMDErrorCode(result.value), result.status)

    async def indoor_humidity(self) -> Result[int]:
        """Get the indoor humidity (%)"""
        return await self.client.get_register(self.regmap[Reg.HUMIDITY_INDOOR], self.slave_id)

    async def outdoor_humidity(self) -> Result[int]:
        """Get the outdoor humidity (%)"""
        return await self.client.get_register(self.regmap[Reg.HUMIDITY_OUTDOOR], self.slave_id)

    async def exhaust_fan_speed(self) -> Result[int]:
        """Get the exhaust fan speed (%)"""
        return await self.client.get_register(self.regmap[Reg.FAN_SPEED_EXHAUST], self.slave_id)

    async def supply_fan_speed(self) -> Result[int]:
        """Get the supply fan speed (%)"""
        return await self.client.get_register(self.regmap[Reg.FAN_SPEED_SUPPLY], self.slave_id)

    async def indoor_air_temperature(self) -> Result[VMDTemperature]:
        """Get the indoor air temperature.

        This is exhaust temperature before the heat exchanger.
        """
        regdesc = self.regmap[Reg.TEMPERATURE_EXHAUST]
        result = await self.client.get_register(regdesc, self.slave_id)
        if math.isnan(result.value):
            status = VMDSensorStatus.UNAVAILABLE
        elif result.value < -273.0:
            status = VMDSensorStatus.ERROR
        else:
            status = VMDSensorStatus.OK
        return Result(VMDTemperature(round(result.value, 2), status), result.status)

    async def exhaust_air_temperature(self) -> Result[VMDTemperature]:
        """Get the exhaust air temperature.

        This is the exhaust temperature after the heat exchanger.
        """
        regdesc = self.regmap[Reg.TEMPERATURE_OUTLET]
        result = await self.client.get_register(regdesc, self.slave_id)
        if math.isnan(result.value):
            status = VMDSensorStatus.UNAVAILABLE
        elif result.value < -273.0:
            status = VMDSensorStatus.ERROR
        else:
            status = VMDSensorStatus.OK
        return Result(VMDTemperature(round(result.value, 2), status), result.status)

    async def supply_air_temperature(self) -> Result[VMDTemperature]:
        """Get the supply air temperature.

        This is the supply temperature after the heat exchanger.
        """
        regdesc = self.regmap[Reg.TEMPERATURE_EXHAUST]
        result = await self.client.get_register(regdesc, self.slave_id)
        if math.isnan(result.value):
            status = VMDSensorStatus.UNAVAILABLE
        elif result.value < -273.0:
            status = VMDSensorStatus.ERROR
        else:
            status = VMDSensorStatus.OK
        return Result(VMDTemperature(round(result.value, 2), status), result.status)

    async def postheater(self) -> Result[VMDHeater]:
        """Get the postheater level."""
        regdesc = self.regmap[Reg.POST_HEATER_DEMAND]
        result = await self.client.get_register(regdesc, self.slave_id)
        status = VMDHeaterStatus.UNAVAILABLE if result.value == 0xEF else VMDHeaterStatus.OK
        return Result(VMDHeater(result.value, status), result.status)

    async def fetch_node_data(self) -> NodeData:  # pylint: disable=duplicate-code
        """Fetch all controller data at once."""

        return NodeData(
            slave_id=self.slave_id,
            # node data from pyairios node
            rf_address=await _safe_fetch(self.node_rf_address),
            product_id=await _safe_fetch(self.node_product_id),
            sw_version=await _safe_fetch(self.node_software_version),
            product_name=await _safe_fetch(self.node_product_name),
            # device data
            rf_comm_status=await _safe_fetch(self.node_rf_comm_status),
            battery_status=await _safe_fetch(self.node_battery_status),
            fault_status=await _safe_fetch(self.node_fault_status),
            bound_status=await _safe_fetch(self.device_bound_status),
            value_error_status=await _safe_fetch(self.device_value_error_status),
            # VMD-07RPS13 data
            product_variant=await _safe_fetch(self.product_variant),
            error_code=await _safe_fetch(self.error_code),
            system_ventilation_config=await _safe_fetch(self.system_ventilation_configuration),
            ventilation_mode=await _safe_fetch(self.vent_mode),
            ventilation_sub_mode=await _safe_fetch(self.vent_sub_mode),
            # ventilation_sub_mode_exh=await _safe_fetch(self.vent_sub_mode_exh),  # failed
            temp_ventilation_mode=await _safe_fetch(self.temp_vent_mode),
            temp_ventilation_sub_mode=await _safe_fetch(self.temp_vent_sub_mode),
            # temp_ventilation_sub_mode_exh=await _safe_fetch(self.temp_vent_sub_mode_exh),  # failed
            exhaust_fan_speed=await _safe_fetch(self.exhaust_fan_speed),
            supply_fan_speed=await _safe_fetch(self.supply_fan_speed),
            indoor_air_temperature=await _safe_fetch(self.indoor_air_temperature),
            exhaust_air_temperature=await _safe_fetch(self.exhaust_air_temperature),
            supply_air_temperature=await _safe_fetch(self.supply_air_temperature),
            filter_dirty=await _safe_fetch(self.filter_dirty),
            filter_remaining_days=await _safe_fetch(self.filter_remaining_days),
            filter_remaining_percent=await _safe_fetch(self.filter_remaining_percent),
            bypass_position=await _safe_fetch(self.bypass_position),
            basic_ventilation_enable=await _safe_fetch(self.basic_vent_enable),
            co2_level=await _safe_fetch(self.co2_level),
            co2_control_setpoint=await _safe_fetch(self.co2_setpoint),
            ventilation_speed=await _safe_fetch(self.vent_speed_composite),
        )

    async def print_data(self) -> None:
        """
        Print labels + states for this particular model, including VMD base fields, in CLI.

        :return: no confirmation, outputs to serial monitor
        """

        res = await self.fetch_node_data()  # customised in model file

        super().print_data(res)

        print("VMD-07RPS13 data")
        print("----------------")
        print(f"    {'Product Variant:': <25}{res['product_variant']}")
        print(f"    {'Error code:': <25}{res['error_code']}")
        print("")
        print(f"    {'Ventilation mode:': <25}{res['ventilation_mode']}")
        print(f"    {'Ventilation sub mode:': <25}{res['ventilation_sub_mode']}")
        print(f"    {'Temp. Ventil. mode:': <25}{res['temp_ventilation_mode']}")
        print(f"    {'Temp. Ventil. sub mode:': <25}{res['temp_ventilation_sub_mode']}")
        #
        print(
            f"    {'Supply fan speed:': <25}{res['supply_fan_speed']}% "
            # f"({res['supply_fan_rpm']} RPM)"
        )
        print(
            f"    {'Exhaust fan speed:': <25}{res['exhaust_fan_speed']}% "
            # f"({res['exhaust_fan_rpm']} RPM)"
        )

        print(f"    {'Indoor temperature:': <25}{res['indoor_air_temperature']}")
        # print(f"    {'Outdoor temperature:': <25}{res['outdoor_air_temperature']}")
        print(f"    {'Exhaust temperature:': <25}{res['exhaust_air_temperature']}")
        print(f"    {'Supply temperature:': <25}{res['supply_air_temperature']}")

        print(f"    {'CO2 level:':<40}{res['co2_level']} ppm")

        print(f"    {'Filter dirty:': <25}{res['filter_dirty']}")
        print(f"    {'Filter remaining days:': <25}{res['filter_remaining_days']} days")
        print(f"    {'Filter remaining perc.:': <25}{res['filter_remaining_percent']}%")

        print(
            f"    {'Bypass position:': <25}{'Open ' if res == 1 else 'Closed '}{res['bypass_position']}"
        )
        print(f"    {'Base ventil. enabled:': <25}{res['basic_ventilation_enable']}")

        # print(f"    {'Postheater:': <25}{res['postheater']}")
        # print("")

        # print(f"    {'Preset speeds':<25}{'Supply':<10}{'Exhaust':<10}")
        # print(f"    {'-------------':<25}")
        # print(
        #     f"    {'High':<25}{str(res['preset_high_fan_speed_supply']) + ' %':<10}"
        #     f"{str(res['preset_high_fan_speed_exhaust']) + ' %':<10}"
        # )
        # print(
        #     f"    {'Mid':<25}{str(res['preset_medium_fan_speed_supply']) + ' %':<10}"
        #     f"{str(res['preset_medium_fan_speed_exhaust']) + ' %':<10}"
        # )
        # print(
        #     f"    {'Low':<25}{str(res['preset_low_fan_speed_supply']) + ' %':<10}"
        #     f"{str(res['preset_low_fan_speed_exhaust']) + ' %':<10}"
        # )
        # print(
        #     f"    {'Standby':<25}{str(res['preset_standby_fan_speed_supply']) + ' %':<10}"
        #     f"{str(res['preset_standby_fan_speed_exhaust']) + ' %':<10}"
        # )
        print("")

        print("    Setpoints")
        print("    ---------")
        print(f"    {'CO2 control setpoint:':<40}{res['co2_control_setpoint']} ppm")
        # print(
        #     f"    {'Free ventilation cooling offset:':<40}"
        #     f"{res['free_ventilation_cooling_offset']} K"
        # )
