"""Airios VMD-07RPS13 ClimaRad Ventura V1 controller implementation."""

from __future__ import annotations

import logging
import math

# import re
# from dataclasses import dataclass, field
from typing import List

from pyairios.client import AsyncAiriosModbusClient
from pyairios.constants import (
    VMDBypassPosition,
    VMDErrorCode,
    VMDHeater,
    VMDHeaterStatus,
    VMDSensorStatus,
    VMDTemperature,
    VMDVentilationMode,
    VMDCapabilities,
)
from pyairios.data_model import AiriosDeviceData
from pyairios.exceptions import AiriosInvalidArgumentException
from pyairios.models.vmd_base import VmdBase
from pyairios.node import _safe_fetch
from pyairios.registers import (
    FloatRegister,
    RegisterAccess,
    RegisterAddress,
    RegisterBase,
    Result,
    U16Register,
)

LOGGER = logging.getLogger(__name__)


# Linking the registers:
#   Reg:
#       model set of RF Bridge register addresses, by named address keyword
#   VMD07RPS13Data:
#       model dict of register address + Result type by name (formerly in data_model.py)
#   vmdNode.vmd_registers:
#       instance list of register type (size) + name key from Reg + access R/W


class Reg(RegisterAddress):  # only override or add differences in VMD_BASE
    """The Register set for VMD-07RPS13 ClimaRad Ventura V1 controller node."""

    # numbers after "#" are from oem docs
    SYSTEM_VENT_CONFIG = 42021

    VENTILATION_MODE = 41100  # 1,R, uint8, "Main Room Ventilation Mode"
    VENTILATION_SUB_MODE = 41101  # 1, R, uint8, "Main Room Ventilation Sub Mode"
    VENTILATION_SUB_MODE_EXH = 41102  # R, uint8, Main Room Vent. Sub Mode Cont. Exh.

    TEMP_VENTILATION_MODE = 41103  # 1,R, uint8, "Main Room Ventilation Mode"
    TEMP_VENTILATION_SUB_MODE = 41104  # 1, R, uint8, "Main Room Ventilation Sub Mode"
    # TEMP_VENTILATION_SUB_MODE_EXH = 41105  # R, uint8, Main Room Vent. Sub Mode Cont. Exh.

    REQ_VENTILATION_MODE = 41120  # 1,RW, uint8, "Main Room Ventilation Mode"
    REQ_VENTILATION_SUB_MODE = 41121  # 1, RW, uint8, "Main Room Ventilation Sub Mode"
    REQ_VENTILATION_SUB_MODE_EXH = 41122  # 1, R, uint8, "Main Room Ventilation Sub Mode"
    REQ_TEMP_VENTILATION_MODE = 41123  # 1,RW, uint8, "Main Room Temp.Ventilation Mode"
    REQ_TEMP_VENTILATION_SUB_MODE = 41124  # 1, RW, uint8, "Main Room Temp.Ventilation Sub Mode"
    # REQ_TEMP_VENTILATION_SUB_MODE_EXH = (
    #     41125  # RW, uint8, Main Room Temp. Vent. Sub Mode Cont. Exh.
    # )

    FAN_SPEED_EXHAUST = 41019  # 9 #
    FAN_SPEED_SUPPLY = 41020  # 10 # confirmed in CLI
    ERROR_CODE = 41032  # 23 #
    TEMPERATURE_INDOOR = 41005  # 12 # main room exhaust temp
    TEMPERATURE_OUTDOOR = 41003  # inlet temp
    TEMPERATURE_EXHAUST = 41005  # same as TEMP_INDOOR?
    TEMPERATURE_SUPPLY = 41003  # same as TEMP_OUTDOOR?
    HUMIDITY_INDOOR = 41007  # 15 # main room exh hum
    HUMIDITY_OUTDOOR = 41002
    FLOW_INLET = 41024
    FLOW_OUTLET = 41026
    CO2_LEVEL = 41008  # 17 # main room co2
    CO2_CONTROL_SETPOINT = 42011
    POST_HEATER_DEMAND = 41023
    FILTER_REMAINING_DAYS = 41028
    FILTER_DURATION = 41029
    FILTER_DIRTY = 41017
    FILTER_REMAINING_PERCENT = 41030  # Air Filter Time Percent
    BYPASS_POSITION = 41015  # 28 #
    ROOM_INSTANCE = 41126  # 1, RW, uint8, "Room instance"
    SET_PERSON_PRESENT = 41150  # 1, RW, uint8, "Set Person Present"
    FILTER_RESET = 41151
    BASIC_VENTILATION_ENABLE = 42000
    BASIC_VENTILATION_LEVEL = 42001
    PRODUCT_VARIANT = 42010  # 1,RW, uint8, "Product Variant"
    OVERRIDE_TIME_MANUAL = 42009  # 115 # "Temporary Override Duration"


class VMD07RPS13Data(AiriosDeviceData):
    """
    VMD-07RPS13 ClimaRad Ventura V1C/V1D/V1X node data.
    source: ClimaRad Modbus Registers Specs 2024
    """

    error_code: Result[VMDErrorCode] | None
    system_ventilation_config: Result[int] | None
    ventilation_mode: Result[int] | None
    ventilation_sub_mode_exh: Result[int] | None
    ventilation_sub_mode: Result[int] | None
    temp_ventilation_mode: Result[int] | None
    temp_ventilation_sub_mode: Result[int] | None
    temp_ventilation_sub_mode_exh: Result[int] | None
    exhaust_fan_speed: Result[int] | None
    supply_fan_speed: Result[int] | None
    indoor_air_temperature: Result[VMDTemperature] | None
    outdoor_air_temperature: Result[VMDTemperature] | None
    exhaust_air_temperature: Result[VMDTemperature] | None
    supply_air_temperature: Result[VMDTemperature] | None
    filter_dirty: Result[int] | None
    filter_remaining_days: Result[int] | None
    bypass_position: Result[VMDBypassPosition] | None
    product_variant: Result[int] | None
    # postheater: Result[VMDHeater] | None
    co2_level: Result[int] | None
    co2_control_setpoint: Result[int] | None
    basic_ventilation_enable: Result[int] | None


def product_id() -> int:
    # for key VMD_07RPS13
    return 0x0001C883


def product_description() -> str:
    # for key VMD_07RPS13
    return "ClimaRad Ventura V1"


class VmdNode(VmdBase):
    """Represents a VMD-07RPS13 Ventura V1 controller node."""

    def __init__(self, slave_id: int, client: AsyncAiriosModbusClient) -> None:
        """Initialize the VMD-07RPS13 Ventura controller node instance."""
        super().__init__(slave_id, client)
        LOGGER.debug(f"Starting Ventura VmdNode({slave_id})")
        vmd_registers: List[RegisterBase] = [
            U16Register(
                Reg.SYSTEM_VENT_CONFIG,
                RegisterAccess.WRITE | RegisterAccess.READ | RegisterAccess.STATUS,
            ),
            U16Register(Reg.VENTILATION_MODE, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.VENTILATION_SUB_MODE, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.TEMP_VENTILATION_MODE, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.TEMP_VENTILATION_SUB_MODE, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.FAN_SPEED_EXHAUST, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.FAN_SPEED_SUPPLY, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.ERROR_CODE, RegisterAccess.READ | RegisterAccess.STATUS),
            FloatRegister(Reg.TEMPERATURE_INDOOR, RegisterAccess.READ | RegisterAccess.STATUS),
            FloatRegister(Reg.TEMPERATURE_OUTDOOR, RegisterAccess.READ | RegisterAccess.STATUS),
            FloatRegister(Reg.TEMPERATURE_EXHAUST, RegisterAccess.READ | RegisterAccess.STATUS),
            FloatRegister(Reg.TEMPERATURE_SUPPLY, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.FILTER_DIRTY, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.BYPASS_POSITION, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.HUMIDITY_INDOOR, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.HUMIDITY_OUTDOOR, RegisterAccess.READ | RegisterAccess.STATUS),
            # FloatRegister(Reg.FLOW_INLET, RegisterAccess.READ | RegisterAccess.STATUS),
            # FloatRegister(Reg.FLOW_OUTLET, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.CO2_LEVEL, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.POST_HEATER_DEMAND, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.FILTER_REMAINING_DAYS, RegisterAccess.READ | RegisterAccess.STATUS),
            # U16Register(Reg.FILTER_DURATION, RegisterAccess.READ | RegisterAccess.STATUS),
            # U16Register(Reg.FILTER_REMAINING_PERCENT, RegisterAccess.READ | RegisterAccess.STATUS),
            # U16Register(Reg.FAN_RPM_EXHAUST, RegisterAccess.READ | RegisterAccess.STATUS),
            # U16Register(Reg.FAN_RPM_SUPPLY, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(
                Reg.PRODUCT_VARIANT,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),  # UINT8?
            U16Register(
                Reg.BASIC_VENTILATION_ENABLE,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),  # UINT8?
            U16Register(
                Reg.BASIC_VENTILATION_LEVEL,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            U16Register(Reg.OVERRIDE_TIME_MANUAL, RegisterAccess.READ | RegisterAccess.WRITE),
            U16Register(Reg.FILTER_RESET, RegisterAccess.WRITE | RegisterAccess.STATUS),
            U16Register(
                Reg.CO2_CONTROL_SETPOINT,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
        ]
        self._add_registers(vmd_registers)

    # getters and setters

    async def capabilities(self) -> Result[VMDCapabilities] | None:
        """Get the ventilation unit capabilities."""
        # regdesc = self.regmap[Reg.CAPABILITIES]
        # result = await self.client.get_register(regdesc, self.slave_id)
        # return Result(VMDCapabilities(result.value), result.status)
        # TODO create some other set of capabilities: mode, bypass, ...
        return None

    async def basic_ventilation_enable(self) -> Result[int]:
        """Get base ventilation enabled."""
        return await self.client.get_register(
            self.regmap[Reg.BASIC_VENTILATION_ENABLE], self.slave_id
        )

    async def set_basic_ventilation_enable(self, mode: int) -> bool:
        """Set base ventilation enabled/disabled."""
        return await self.client.set_register(
            self.regmap[Reg.BASIC_VENTILATION_ENABLE], mode, self.slave_id
        )

    async def set_basic_ventilation_level(self, level: int) -> bool:
        """Set the base ventilation level."""
        return await self.client.set_register(
            self.regmap[Reg.BASIC_VENTILATION_LEVEL], level, self.slave_id
        )

    # async def set_ventilation_speed_override_time(
    #     self, speed: VMDRequestedVentilationSpeed, minutes: int
    # ) -> bool:
    #     """Set the ventilation unit speed preset for a limited time."""
    #     if minutes > 18 * 60:
    #         raise AiriosInvalidArgumentException("Maximum speed override time is 18 hours")
    #     if speed == VMDRequestedVentilationSpeed.LOW:
    #         return await self.client.set_register(
    #             self.regmap[Reg.OVERRIDE_TIME_SPEED_LOW], minutes, self.slave_id
    #         )
    #     if speed == VMDRequestedVentilationSpeed.MID:
    #         return await self.client.set_register(
    #             self.regmap[Reg.OVERRIDE_TIME_SPEED_MID], minutes, self.slave_id
    #         )
    #     if speed == VMDRequestedVentilationSpeed.HIGH:
    #         return await self.client.set_register(
    #             self.regmap[Reg.OVERRIDE_TIME_SPEED_HIGH], minutes, self.slave_id
    #         )
    #     raise AiriosInvalidArgumentException(f"Invalid temporary override speed {speed}")

    async def system_ventilation_configuration(self) -> Result[int]:
        """Get the system ventilation configuration status."""
        return await self.client.get_register(self.regmap[Reg.SYSTEM_VENT_CONFIG], self.slave_id)

    async def ventilation_mode(self) -> Result[int]:
        """Get the ventilation mode status. 0=Off, 2=On, 3=Man1, 5=Man3, 8=Service"""
        return await self.client.get_register(self.regmap[Reg.VENTILATION_MODE], self.slave_id)

    async def set_ventilation_mode(self, mode: VMDVentilationMode) -> bool:
        """Set the ventilation mode. 0=Off, 2=On, 3=Man1, 5=Man3, 8=Service"""
        if mode == VMDVentilationMode.UNKNOWN:
            raise AiriosInvalidArgumentException(f"Invalid ventilation mode {mode}")
        return await self.client.set_register(
            self.regmap[Reg.REQ_VENTILATION_MODE], mode, self.slave_id
        )

    async def ventilation_sub_mode(self) -> Result[int]:
        """Get the ventilation sub mode status."""
        # seen: 48
        return await self.client.get_register(self.regmap[Reg.VENTILATION_SUB_MODE], self.slave_id)

    # async def ventilation_sub_mode_exh(self) -> Result[int]:  # error
    #     """Get the ventilation sub mode exhaust status."""
    #     return await self.client.get_register(self.regmap[Reg.VENTILATION_SUB_MODE_EXH], self.slave_id)

    async def temp_ventilation_mode(self) -> Result[int]:
        """Get the temporary ventilation mode status."""
        return await self.client.get_register(self.regmap[Reg.TEMP_VENTILATION_MODE], self.slave_id)

    async def temp_ventilation_sub_mode(self) -> Result[int]:
        """Get the temporary ventilation sub mode status."""
        return await self.client.get_register(
            self.regmap[Reg.TEMP_VENTILATION_SUB_MODE], self.slave_id
        )

    # async def temp_ventilation_sub_mode_exh(self) -> Result[int]:  # error
    #     """Get the temporary ventilation sub mode exhaust status."""
    #     return await self.client.get_register(
    #         self.regmap[Reg.TEMP_VENTILATION_SUB_MODE_EXH], self.slave_id
    #     )

    async def bypass_position(self) -> Result[VMDBypassPosition]:
        """Get the bypass position."""
        regdesc = self.regmap[Reg.BYPASS_POSITION]
        result = await self.client.get_register(regdesc, self.slave_id)
        error = result.value > 120
        return Result(VMDBypassPosition(result.value, error), result.status)

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

    async def filter_duration(self) -> Result[int]:
        """Get the filter duration (in days)."""
        return await self.client.get_register(self.regmap[Reg.FILTER_DURATION], self.slave_id)

    async def filter_remaining_days(self) -> Result[int]:
        """Get the filter remaining lifetime (in days)."""
        return await self.client.get_register(self.regmap[Reg.FILTER_REMAINING_DAYS], self.slave_id)

    async def filter_remaining(self) -> Result[int]:
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

        This is exhaust flow before the heat exchanger.
        """
        regdesc = self.regmap[Reg.TEMPERATURE_INDOOR]
        result = await self.client.get_register(regdesc, self.slave_id)
        if math.isnan(result.value):
            status = VMDSensorStatus.UNAVAILABLE
        elif result.value < -273.0:
            status = VMDSensorStatus.ERROR
        else:
            status = VMDSensorStatus.OK
        return Result(VMDTemperature(round(result.value, 2), status), result.status)

    async def outdoor_air_temperature(self) -> Result[VMDTemperature]:
        """Get the outdoor air temperature.

        This is the supply flow before the heat exchanger.
        """
        regdesc = self.regmap[Reg.TEMPERATURE_OUTDOOR]
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

        This is the exhaust flow after the heat exchanger.
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

    async def supply_air_temperature(self) -> Result[VMDTemperature]:
        """Get the supply air temperature.

        This is the supply flow after the heat exchanger.
        """
        regdesc = self.regmap[Reg.TEMPERATURE_SUPPLY]
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

    async def fetch_vmd_data(self) -> VMD07RPS13Data:  # pylint: disable=duplicate-code
        """Fetch all controller data at once."""

        return VMD07RPS13Data(
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
            ventilation_mode=await _safe_fetch(self.ventilation_mode),
            ventilation_sub_mode=await _safe_fetch(self.ventilation_sub_mode),
            # ventilation_sub_mode_exh=await _safe_fetch(self.ventilation_sub_mode_exh),  # failed
            temp_ventilation_mode=await _safe_fetch(self.temp_ventilation_mode),
            temp_ventilation_sub_mode=await _safe_fetch(self.temp_ventilation_sub_mode),
            # temp_ventilation_sub_mode_exh=await _safe_fetch(self.temp_ventilation_sub_mode_exh),  # failed
            exhaust_fan_speed=await _safe_fetch(self.exhaust_fan_speed),
            supply_fan_speed=await _safe_fetch(self.supply_fan_speed),
            indoor_air_temperature=await _safe_fetch(self.indoor_air_temperature),
            outdoor_air_temperature=await _safe_fetch(self.outdoor_air_temperature),
            exhaust_air_temperature=await _safe_fetch(self.exhaust_air_temperature),
            supply_air_temperature=await _safe_fetch(self.supply_air_temperature),
            filter_dirty=await _safe_fetch(self.filter_dirty),
            filter_remaining_days=await _safe_fetch(self.filter_remaining_days),
            bypass_position=await _safe_fetch(self.bypass_position),
            basic_ventilation_enable=await _safe_fetch(self.basic_ventilation_enable),
            # postheater=await _safe_fetch(self.postheater),
            co2_level=await _safe_fetch(self.co2_level),
            co2_control_setpoint=await _safe_fetch(self.co2_setpoint),
            # free_ventilation_cooling_offset=await _safe_fetch(self.free_ventilation_cooling_offset),
            # frost_protection_preheater_setpoint=await _safe_fetch(
            #     self.frost_protection_preheater_setpoint
            # ),
            # preset_high_fan_speed_supply=await _safe_fetch(self.preset_high_fan_speed_supply),
            # preset_high_fan_speed_exhaust=await _safe_fetch(self.preset_high_fan_speed_exhaust),
            # preset_medium_fan_speed_supply=await _safe_fetch(self.preset_medium_fan_speed_supply),
            # preset_medium_fan_speed_exhaust=await _safe_fetch(self.preset_medium_fan_speed_exhaust),
            # preset_low_fan_speed_supply=await _safe_fetch(self.preset_low_fan_speed_supply),
            # preset_low_fan_speed_exhaust=await _safe_fetch(self.preset_low_fan_speed_exhaust),
            # preset_standby_fan_speed_supply=await _safe_fetch(self.preset_standby_fan_speed_supply),
            # preset_standby_fan_speed_exhaust=await _safe_fetch(
            #     self.preset_standby_fan_speed_exhaust
            # ),
        )

    def print_data(self, res) -> None:
        """
        Print labels + states for this particular model, including VMD base fields

        :param res: the result retrieved earlier by CLI using fetch_vmd_data()
        :return: no confirmation, outputs to serial monitor
        """
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
            #    f"({res['exhaust_fan_rpm']} RPM)"
        )

        print(f"    {'Indoor temperature:': <25}{res['indoor_air_temperature']}")
        print(f"    {'Outdoor temperature:': <25}{res['outdoor_air_temperature']}")
        print(f"    {'Exhaust temperature:': <25}{res['exhaust_air_temperature']}")
        print(f"    {'Supply temperature:': <25}{res['supply_air_temperature']}")

        print(f"    {'CO2 level:':<40}{res['co2_level']} ppm")

        print(f"    {'Filter dirty:': <25}{res['filter_dirty']}")
        print(f"    {'Filter remaining days:': <25}{res['filter_remaining_days']} days")

        print(f"    {'Bypass position:': <25}{res['bypass_position']}")
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
