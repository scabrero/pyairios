"""Airios VMD-07RPS13 controller implementation."""

from __future__ import annotations

import logging
import math
from typing import List

from pyairios.client import AsyncAiriosModbusClient
from pyairios.constants import (
    ProductId,
    VMDBypassPosition,
    VMDCapabilities,
    VMDCO2Level,
    VMDErrorCode,
    VMDFlowLevel,
    VMDHeater,
    VMDHeaterStatus,
    VMDHumidity,
    VMDRequestedVentilationSpeed,
    VMDSensorStatus,
    VMDTemperature,
    VMDVentilationMode,
    VMDVentilationSpeed,
)
from pyairios.node import AiriosNode
from pyairios.properties import AiriosVMDProperty as vp
from pyairios.registers import (
    FloatRegister,
    RegisterAccess,
    RegisterBase,
    Result,
    U8Register,
    U16Register,
)

LOGGER = logging.getLogger(__name__)


def pr_id() -> ProductId:
    """
    Get product_id for model VMD_07RPS13.
    Named as is to discern from product_id register.
    """
    return ProductId.VMD_07RPS13


def pr_description() -> str | tuple[str, ...]:
    """
    Get description of product(s) using VMD_07RPS13.
    Human-readable text, used in e.g. HomeAssistant Binding UI.
    :return: string or tuple of strings, starting with manufacturer
    """
    return "ClimaRad Ventura V1"


def pr_instantiate(device_id: int, client: AsyncAiriosModbusClient) -> VMD07RPS13:
    """Get a new device instance. Used by the device factory to instantiate by product ID."""
    return VMD07RPS13(device_id, client)


def _temperature_adapter(value: float) -> VMDTemperature:
    if math.isnan(value):
        status = VMDSensorStatus.UNAVAILABLE
    elif value < -273.0:
        status = VMDSensorStatus.ERROR
    else:
        status = VMDSensorStatus.OK
    return VMDTemperature(value, status)


def _humidity_adapter(value: int) -> VMDHumidity:
    status = VMDSensorStatus.OK
    if value == 0xEF:
        status = VMDSensorStatus.UNAVAILABLE
    elif value == 0xF0:
        status = VMDSensorStatus.SHORT_CIRCUIT
    elif value == 0xF1:
        status = VMDSensorStatus.OPEN_CIRCUIT
    elif value == 0xF2:
        status = VMDSensorStatus.ERROR_UNAVAILABLE
    elif value == 0xF3:
        status = VMDSensorStatus.OVERFLOW
    elif value == 0xF4:
        status = VMDSensorStatus.UNDERFLOW
    elif value == 0xF5:
        status = VMDSensorStatus.UNRELIABLE
    elif 0xF6 <= value <= 0xFE:
        status = VMDSensorStatus.ERROR_RESERVED
    elif value == 0xFF:
        status = VMDSensorStatus.ERROR
    return VMDHumidity(value, status)


def _co2_adapter(value: int) -> VMDCO2Level:
    status = VMDSensorStatus.OK
    if value == 0x7FFF:
        status = VMDSensorStatus.UNAVAILABLE
    elif 0x8000 <= value <= 0xFFFF:
        status = VMDSensorStatus.ERROR
    return VMDCO2Level(value, status)


def _flow_adapter(value: int) -> VMDFlowLevel:
    status = VMDSensorStatus.OK
    if value == 0x7FFF:
        status = VMDSensorStatus.UNAVAILABLE
    elif 0x8000 <= value <= 0x85FF:
        status = VMDSensorStatus.ERROR
    return VMDFlowLevel(value, status)


def _bypass_position_adapter(value) -> VMDBypassPosition:
    error = value > 120
    return VMDBypassPosition(value, error)


def _heater_adapter(value) -> VMDHeater:
    status = VMDHeaterStatus.UNAVAILABLE if value == 0xEF else VMDHeaterStatus.OK
    return VMDHeater(value, status)


class VMD07RPS13(AiriosNode):
    """Represents a VMD-07RPS13 controller node."""

    def __init__(self, device_id: int, client: AsyncAiriosModbusClient) -> None:
        """Initialize the VMD-07RPS13 Ventura controller node instance."""
        super().__init__(device_id, client)
        vmd_registers: List[RegisterBase] = [
            FloatRegister(
                vp.TEMPERATURE_OUTLET,
                41000,
                RegisterAccess.READ | RegisterAccess.STATUS,
                result_adapter=_temperature_adapter,
            ),
            U8Register(
                vp.HUMIDITY_OUTDOOR,
                41002,
                RegisterAccess.READ | RegisterAccess.STATUS,
                result_adapter=_humidity_adapter,
            ),
            FloatRegister(
                vp.TEMPERATURE_INLET,
                41003,
                RegisterAccess.READ | RegisterAccess.STATUS,
                result_adapter=_temperature_adapter,
            ),
            FloatRegister(
                vp.TEMPERATURE_EXHAUST,
                41005,
                RegisterAccess.READ | RegisterAccess.STATUS,
                result_adapter=_temperature_adapter,
            ),
            U8Register(
                vp.HUMIDITY_INDOOR,
                41007,
                RegisterAccess.READ | RegisterAccess.STATUS,
                result_adapter=_humidity_adapter,
            ),
            U16Register(
                vp.CO2_LEVEL,
                41008,
                RegisterAccess.READ | RegisterAccess.STATUS,
                result_adapter=_co2_adapter,
            ),
            U8Register(
                vp.BYPASS_POSITION,
                41015,
                RegisterAccess.READ | RegisterAccess.STATUS,
                result_adapter=_bypass_position_adapter,
            ),
            U8Register(vp.FILTER_DIRTY, 41017, RegisterAccess.READ | RegisterAccess.STATUS),
            U8Register(vp.FAN_SPEED_EXHAUST, 41019, RegisterAccess.READ | RegisterAccess.STATUS),
            U8Register(vp.FAN_SPEED_SUPPLY, 41020, RegisterAccess.READ | RegisterAccess.STATUS),
            U8Register(
                vp.POSTHEATER,
                41023,
                RegisterAccess.READ | RegisterAccess.STATUS,
                result_adapter=_heater_adapter,
            ),
            FloatRegister(
                vp.FLOW_INLET,
                41024,
                RegisterAccess.READ | RegisterAccess.STATUS,
                result_adapter=_flow_adapter,
            ),
            FloatRegister(
                vp.FLOW_OUTLET,
                41026,
                RegisterAccess.READ | RegisterAccess.STATUS,
                result_adapter=_flow_adapter,
            ),
            U16Register(
                vp.FILTER_REMAINING_DAYS, 41028, RegisterAccess.READ | RegisterAccess.STATUS
            ),
            U16Register(vp.FILTER_DURATION, 41029, RegisterAccess.READ | RegisterAccess.STATUS),
            U8Register(
                vp.FILTER_REMAINING_PERCENT, 41030, RegisterAccess.READ | RegisterAccess.STATUS
            ),
            U8Register(vp.ERROR_CODE, 41032, RegisterAccess.READ | RegisterAccess.STATUS),
            U8Register(
                vp.VENTILATION_MODE,
                41100,
                RegisterAccess.READ | RegisterAccess.STATUS,
                result_type=VMDVentilationMode,
            ),
            U8Register(vp.VENTILATION_SUB_MODE, 41101, RegisterAccess.READ | RegisterAccess.STATUS),
            U8Register(
                vp.TEMP_VENTILATION_MODE, 41103, RegisterAccess.READ | RegisterAccess.STATUS
            ),
            U8Register(
                vp.TEMP_VENTILATION_SUB_MODE, 41104, RegisterAccess.READ | RegisterAccess.STATUS
            ),
            U8Register(
                vp.REQUESTED_VENTILATION_MODE,
                41120,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            U8Register(
                vp.REQUESTED_VENTILATION_SUB_MODE,
                41121,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            U8Register(
                vp.REQUESTED_TEMP_VENTILATION_MODE,
                41123,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            U8Register(
                vp.REQUESTED_TEMP_VENTILATION_SUB_MODE,
                41124,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            U8Register(vp.FILTER_RESET, 41151, RegisterAccess.WRITE | RegisterAccess.STATUS),
            U8Register(
                vp.BASIC_VENTILATION_ENABLE,
                42000,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            U8Register(
                vp.BASIC_VENTILATION_LEVEL,
                42001,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            U16Register(
                vp.TEMP_OVERRIDE_DURATION, 42009, (RegisterAccess.READ | RegisterAccess.WRITE)
            ),
            U16Register(vp.CO2_CONTROL_SETPOINT, 42011, RegisterAccess.READ | RegisterAccess.WRITE),
            U8Register(
                vp.PRODUCT_VARIANT,
                41010,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            U8Register(
                vp.SYSTEM_VENTILATION_CONFIGURATION,
                42021,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
        ]
        self._add_registers(vmd_registers)

    def __str__(self) -> str:
        return f"VMD-07RPS13@{self.device_id}"

    async def capabilities(self) -> Result[VMDCapabilities]:
        """Get the ventilation unit capabilities.
        Capabilities register not supported on VMD-07RPS13, so must simulate"""
        _caps = VMDCapabilities.NO_CAPABLE
        return Result(_caps, None)

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

        mode = await self.client.get_register(self.regmap[vp.VENTILATION_MODE], self.device_id)
        man_step = await self.client.get_register(
            self.regmap[vp.TEMP_VENTILATION_SUB_MODE], self.device_id
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

    async def set_ventilation_speed(self, speed: VMDRequestedVentilationSpeed) -> bool:
        """Set the ventilation unit speed (temp 8H) preset."""
        md = 0  # VMDVentilationSpeed.OFF, PAUSE?
        if speed == VMDRequestedVentilationSpeed.AUTO:
            md = 0
        elif speed == VMDRequestedVentilationSpeed.AWAY:
            md = 0
        elif speed == VMDRequestedVentilationSpeed.LOW:
            md = 202
        elif speed == VMDRequestedVentilationSpeed.MID:
            md = 203
        elif speed == VMDRequestedVentilationSpeed.HIGH:
            md = 205

        regdesc = self.regmap[vp.REQUESTED_VENTILATION_SUB_MODE]
        # check why no immediate change
        return await self.client.set_register(regdesc, md, self.device_id)

    async def system_ventilation_configuration(self) -> Result[int]:
        """Get the system ventilation configuration status."""
        regdesc = self.regmap[vp.SYSTEM_VENTILATION_CONFIGURATION]
        return await self.client.get_register(regdesc, self.device_id)

    async def ventilation_mode(self) -> Result[VMDVentilationMode]:
        """Get the ventilation mode status. 0=Off, 1=Pause, 2=On, 3=Man1, 5=Man3, 8=Service"""
        # seen: 0 (with temp_vent_mode 3) | 1 = Pause | 2 = On (with vent_sub_mode 48)
        regdesc = self.regmap[vp.VENTILATION_MODE]
        return await self.client.get_register(regdesc, self.device_id)

    async def set_ventilation_mode(self, mode: VMDVentilationMode) -> bool:
        """Set the ventilation mode. 0=Off, 2=On, 3=Man1, 5=Man3, 8=Service"""
        regdesc = self.regmap[vp.REQUESTED_VENTILATION_MODE]
        return await self.client.set_register(regdesc, mode, self.device_id)

    async def requested_ventilation_mode(self) -> Result[VMDVentilationMode]:
        """Get the ventilation mode status. 0=Off, 2=On, 3=Man1, 5=Man3, 8=Service"""
        regdesc = self.regmap[vp.REQUESTED_VENTILATION_MODE]
        return await self.client.get_register(regdesc, self.device_id)

    async def ventilation_sub_mode(self) -> Result[int]:
        """Get the ventilation sub mode status."""
        # seen: 0 | 48
        regdesc = self.regmap[vp.VENTILATION_SUB_MODE]
        return await self.client.get_register(regdesc, self.device_id)

    async def set_ventilation_sub_mode(self, mode: int) -> bool:
        """Set the ventilation sub mode. 0=Off/Pause, 48=Auto"""
        regdesc = self.regmap[vp.REQUESTED_VENTILATION_SUB_MODE]
        return await self.client.set_register(regdesc, mode, self.device_id)

    async def requested_ventilation_sub_mode(self) -> Result[int]:
        """Get the ventilation mode status. 0=Off/Pause, 2=On, 3=Man1, 5=Man3, 8=Service"""
        regdesc = self.regmap[vp.REQUESTED_VENTILATION_SUB_MODE]
        return await self.client.get_register(regdesc, self.device_id)

    async def temp_ventilation_mode(self) -> Result[int]:
        """Get the temporary ventilation mode status."""
        # seen: 0 (with Ventilation mode != 0) | 3
        regdesc = self.regmap[vp.TEMP_VENTILATION_MODE]
        return await self.client.get_register(regdesc, self.device_id)

    async def temp_ventilation_sub_mode(self) -> Result[int]:
        """Get the temporary ventilation sub mode status."""
        # seen: 0 (with temp_vent_mode 3) | 201 | 202 | .. | 205
        regdesc = self.regmap[vp.TEMP_VENTILATION_SUB_MODE]
        return await self.client.get_register(regdesc, self.device_id)

    async def set_temp_ventilation_mode(self, mode: int) -> bool:
        """Set the temp ventilation mode. 0=Off, 1=Pause, 2=On, 3=Man1, 5=Man3, 8=Service"""
        regdesc = self.regmap[vp.REQUESTED_TEMP_VENTILATION_MODE]
        return await self.client.set_register(regdesc, mode, self.device_id)

    async def requested_temp_ventilation_mode(self) -> Result[int]:
        """Get the temp ventilation mode status. 0=Off, 1=Pause, 2=On, 3=Man1, 5=Man3, 8=Service"""
        regdesc = self.regmap[vp.REQUESTED_TEMP_VENTILATION_MODE]
        return await self.client.get_register(regdesc, self.device_id)

    async def set_temp_ventilation_sub_mode(self, mode: int) -> bool:
        """Set the temp ventilation sub mode. 0=Off/Pause, 201, ..."""
        regdesc = self.regmap[vp.REQUESTED_TEMP_VENTILATION_SUB_MODE]
        return await self.client.set_register(regdesc, mode, self.device_id)

    async def requested_temp_ventilation_sub_mode(self) -> Result[int]:
        """Get the temp ventilation sub mode status. 0=Off/Pause, 201, ..."""
        regdesc = self.regmap[vp.REQUESTED_TEMP_VENTILATION_SUB_MODE]
        return await self.client.get_register(regdesc, self.device_id)

    async def bypass_position(self) -> Result[VMDBypassPosition]:
        """Get the bypass position."""
        regdesc = self.regmap[vp.BYPASS_POSITION]
        return await self.client.get_register(regdesc, self.device_id)

    async def filter_duration(self) -> Result[int]:
        """Get the filter duration (in days)."""
        return await self.client.get_register(self.regmap[vp.FILTER_DURATION], self.device_id)

    async def filter_remaining_days(self) -> Result[int]:
        """Get the filter remaining lifetime (in days)."""
        return await self.client.get_register(self.regmap[vp.FILTER_REMAINING_DAYS], self.device_id)

    async def filter_remaining_percent(self) -> Result[int]:
        """Get the filter remaining lifetime (in %)."""
        return await self.client.get_register(
            self.regmap[vp.FILTER_REMAINING_PERCENT], self.device_id
        )

    async def filter_reset(self) -> bool:
        """Reset the filter dirty status."""
        return await self.client.set_register(self.regmap[vp.FILTER_RESET], 0, self.device_id)

    async def filter_dirty(self) -> Result[int]:
        """Get the filter dirty status."""
        regdesc = self.regmap[vp.FILTER_DIRTY]
        return await self.client.get_register(regdesc, self.device_id)

    async def error_code(self) -> Result[VMDErrorCode]:
        """Get the ventilation unit error code."""
        regdesc = self.regmap[vp.ERROR_CODE]
        return await self.client.get_register(regdesc, self.device_id)

    async def indoor_humidity(self) -> Result[VMDHumidity]:
        """Get the indoor humidity (%)"""
        regdesc = self.regmap[vp.HUMIDITY_INDOOR]
        return await self.client.get_register(regdesc, self.device_id)

    async def outdoor_humidity(self) -> Result[VMDHumidity]:
        """Get the outdoor humidity (%)"""
        regdesc = self.regmap[vp.HUMIDITY_OUTDOOR]
        return await self.client.get_register(regdesc, self.device_id)

    async def exhaust_fan_speed(self) -> Result[int]:
        """Get the exhaust fan speed (%)"""
        return await self.client.get_register(self.regmap[vp.FAN_SPEED_EXHAUST], self.device_id)

    async def supply_fan_speed(self) -> Result[int]:
        """Get the supply fan speed (%)"""
        return await self.client.get_register(self.regmap[vp.FAN_SPEED_SUPPLY], self.device_id)

    async def indoor_air_temperature(self) -> Result[VMDTemperature]:
        """Get the indoor air temperature.

        This is exhaust flow before the heat exchanger.
        """
        regdesc = self.regmap[vp.TEMPERATURE_EXHAUST]
        return await self.client.get_register(regdesc, self.device_id)

    async def outdoor_air_temperature(self) -> Result[VMDTemperature]:
        """Get the outdoor air temperature.

        This is the supply flow before the heat exchanger.
        """
        regdesc = self.regmap[vp.TEMPERATURE_INLET]
        return await self.client.get_register(regdesc, self.device_id)

    async def exhaust_air_temperature(self) -> Result[VMDTemperature]:
        """Get the exhaust air temperature.

        This is the exhaust flow after the heat exchanger.
        """
        regdesc = self.regmap[vp.TEMPERATURE_OUTLET]
        return await self.client.get_register(regdesc, self.device_id)

    async def postheater(self) -> Result[VMDHeater]:
        """Get the postheater level."""
        regdesc = self.regmap[vp.POSTHEATER]
        return await self.client.get_register(regdesc, self.device_id)

    async def basic_ventilation_enable(self) -> Result[int]:
        """Get base ventilation enabled."""
        return await self.client.get_register(
            self.regmap[vp.BASIC_VENTILATION_ENABLE], self.device_id
        )

    async def set_basic_ventilation_enable(self, mode: int) -> bool:
        """Set base ventilation enabled=1/disabled=0."""
        return await self.client.set_register(
            self.regmap[vp.BASIC_VENTILATION_ENABLE], mode, self.device_id
        )

    async def basic_ventilation_level(self) -> Result[int]:
        """Get base ventilation level."""
        return await self.client.get_register(
            self.regmap[vp.BASIC_VENTILATION_LEVEL], self.device_id
        )

    async def set_basic_ventilation_level(self, level: int) -> bool:
        """Set the base ventilation level."""
        return await self.client.set_register(
            self.regmap[vp.BASIC_VENTILATION_LEVEL], level, self.device_id
        )

    async def product_variant(self) -> Result[int]:
        """Get the product variant."""
        regdesc = self.regmap[vp.PRODUCT_VARIANT]
        return await self.client.get_register(regdesc, self.device_id)

    async def inlet_flow(self) -> Result[VMDFlowLevel]:
        """Get the inlet flow level (in m3/h)"""
        regdesc = self.regmap[vp.FLOW_INLET]
        return await self.client.get_register(regdesc, self.device_id)

    async def outlet_flow(self) -> Result[VMDFlowLevel]:
        """Get the outlet flow level (in m3/h)"""
        regdesc = self.regmap[vp.FLOW_OUTLET]
        return await self.client.get_register(regdesc, self.device_id)

    async def co2_level(self) -> Result[VMDCO2Level]:
        """Get the CO2 level (in ppm)."""
        regdesc = self.regmap[vp.CO2_LEVEL]
        return await self.client.get_register(regdesc, self.device_id)

    async def co2_setpoint(self) -> Result[int]:
        """Get the CO2 control setpoint (in ppm)."""
        regdesc = self.regmap[vp.CO2_CONTROL_SETPOINT]
        return await self.client.get_register(regdesc, self.device_id)

    async def set_co2_setpoint(self, setpnt: int) -> bool:
        """Set the CO2 control setpoint (in ppm)."""
        regdesc = self.regmap[vp.CO2_CONTROL_SETPOINT]
        return await self.client.set_register(regdesc, setpnt, self.device_id)
