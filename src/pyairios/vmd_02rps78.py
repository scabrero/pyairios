"""Airios VMD-02RPS78 controller implementation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List

from .client import AsyncAiriosModbusClient
from .constants import (
    VMDBypassMode,
    VMDBypassPosition,
    VMDCapabilities,
    VMDErrorCode,
    VMDHeater,
    VMDHeaterStatus,
    VMDRequestedVentilationSpeed,
    VMDSensorStatus,
    VMDTemperature,
    VMDVentilationSpeed,
)
from .data_model import VMD02RPS78Data
from .device import AiriosDevice
from .exceptions import AiriosInvalidArgumentException
from .registers import (
    FloatRegister,
    RegisterAccess,
    RegisterAddress,
    RegisterBase,
    Result,
    U16Register,
)


@dataclass
class VMDPresetFansSpeeds:
    """Preset fan speeds."""

    exhaust_fan_speed: Result[int]
    """Exhaust fan speed (%)"""
    supply_fan_speed: Result[int]
    """Supply fan speed (%)"""


class Reg(RegisterAddress):
    """Register set for VMD-02RPS78 controller node."""

    CURRENT_VENTILATION_SPEED = 41000
    FAN_SPEED_EXHAUST = 41001
    FAN_SPEED_SUPPLY = 41002
    ERROR_CODE = 41003
    VENTILATION_SPEED_OVERRIDE_REMAINING_TIME = 41004
    TEMPERATURE_INDOOR = 41005
    TEMPERATURE_OUTDOOR = 41007
    TEMPERATURE_EXHAUST = 41009
    TEMPERATURE_SUPPLY = 41011
    PREHEATER = 41013
    FILTER_DIRTY = 41014
    DEFROST = 41015
    BYPASS_POSITION = 41016
    HUMIDITY_INDOOR = 41017
    HUMIDITY_OUTDOOR = 41018
    FLOW_INLET = 41019
    FLOW_OUTLET = 41021
    AIR_QUALITY = 41023
    AIR_QUALITY_BASIS = 41024
    CO2_LEVEL = 41025
    POST_HEATER = 41026
    CAPABILITIES = 41027
    FILTER_REMAINING_DAYS = 41040
    FILTER_DURATION = 41041
    FILTER_REMAINING_PERCENT = 41042
    FAN_RPM_EXHAUST = 41043
    FAN_RPM_SUPPLY = 41044
    BYPASS_MODE = 41050
    BYPASS_STATUS = 41051
    REQUESTED_VENTILATION_SPEED = 41500
    OVERRIDE_TIME_SPEED_LOW = 41501
    OVERRIDE_TIME_SPEED_MID = 41502
    OVERRIDE_TIME_SPEED_HIGH = 41503
    REQUESTED_BYPASS_MODE = 41550
    FILTER_RESET = 42000
    FAN_SPEED_AWAY_SUPPLY = 42001
    FAN_SPEED_AWAY_EXHAUST = 42002
    FAN_SPEED_LOW_SUPPLY = 42003
    FAN_SPEED_LOW_EXHAUST = 42004
    FAN_SPEED_MID_SUPPLY = 42005
    FAN_SPEED_MID_EXHAUST = 42006
    FAN_SPEED_HIGH_SUPPLY = 42007
    FAN_SPEED_HIGH_EXHAUST = 42008
    FROST_PROTECTION_PREHEATER_SETPOINT = 42009
    PREHEATER_SETPOINT = 42011
    FREE_VENTILATION_HEATING_SETPOINT = 42013
    FREE_VENTILATION_COOLING_OFFSET = 42015


class VMD02RPS78(AiriosDevice):
    """Represents a VMD-02RPS78 controller node."""

    def __init__(self, slave_id: int, client: AsyncAiriosModbusClient) -> None:
        """Initialize the VMD-02RPS78 controller node instance."""
        super().__init__(slave_id, client)
        vmd_registers: List[RegisterBase] = [
            U16Register(Reg.CURRENT_VENTILATION_SPEED, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.FAN_SPEED_EXHAUST, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.FAN_SPEED_SUPPLY, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.ERROR_CODE, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(
                Reg.VENTILATION_SPEED_OVERRIDE_REMAINING_TIME,
                RegisterAccess.READ | RegisterAccess.STATUS,
            ),
            FloatRegister(Reg.TEMPERATURE_INDOOR, RegisterAccess.READ | RegisterAccess.STATUS),
            FloatRegister(Reg.TEMPERATURE_OUTDOOR, RegisterAccess.READ | RegisterAccess.STATUS),
            FloatRegister(Reg.TEMPERATURE_EXHAUST, RegisterAccess.READ | RegisterAccess.STATUS),
            FloatRegister(Reg.TEMPERATURE_SUPPLY, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.PREHEATER, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.FILTER_DIRTY, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.DEFROST, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.BYPASS_POSITION, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.HUMIDITY_INDOOR, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.HUMIDITY_OUTDOOR, RegisterAccess.READ | RegisterAccess.STATUS),
            FloatRegister(Reg.FLOW_INLET, RegisterAccess.READ | RegisterAccess.STATUS),
            FloatRegister(Reg.FLOW_OUTLET, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.AIR_QUALITY, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.AIR_QUALITY_BASIS, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.CO2_LEVEL, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.POST_HEATER, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.CAPABILITIES, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.FILTER_REMAINING_DAYS, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.FILTER_DURATION, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.FILTER_REMAINING_PERCENT, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.FAN_RPM_EXHAUST, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.FAN_RPM_SUPPLY, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.BYPASS_MODE, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(Reg.BYPASS_STATUS, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(
                Reg.REQUESTED_VENTILATION_SPEED,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            U16Register(Reg.OVERRIDE_TIME_SPEED_LOW, RegisterAccess.WRITE),
            U16Register(Reg.OVERRIDE_TIME_SPEED_MID, RegisterAccess.WRITE),
            U16Register(Reg.OVERRIDE_TIME_SPEED_HIGH, RegisterAccess.WRITE),
            U16Register(
                Reg.REQUESTED_BYPASS_MODE,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            U16Register(Reg.FILTER_RESET, RegisterAccess.WRITE | RegisterAccess.STATUS),
            U16Register(
                Reg.FAN_SPEED_AWAY_SUPPLY,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            U16Register(
                Reg.FAN_SPEED_AWAY_EXHAUST,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            U16Register(
                Reg.FAN_SPEED_LOW_SUPPLY,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            U16Register(
                Reg.FAN_SPEED_LOW_EXHAUST,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            U16Register(
                Reg.FAN_SPEED_MID_SUPPLY,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            U16Register(
                Reg.FAN_SPEED_MID_EXHAUST,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            U16Register(
                Reg.FAN_SPEED_HIGH_SUPPLY,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            U16Register(
                Reg.FAN_SPEED_HIGH_EXHAUST,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            FloatRegister(
                Reg.FROST_PROTECTION_PREHEATER_SETPOINT,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            FloatRegister(
                Reg.PREHEATER_SETPOINT,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            FloatRegister(
                Reg.FREE_VENTILATION_HEATING_SETPOINT,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            FloatRegister(
                Reg.FREE_VENTILATION_COOLING_OFFSET,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
        ]
        self._add_registers(vmd_registers)

    def __str__(self) -> str:
        return f"VMD-02RPS78@{self.slave_id}"

    async def capabilities(self) -> Result[VMDCapabilities]:
        """Get the ventilation unit capabilitires."""
        regdesc = self.regmap[Reg.CAPABILITIES]
        result = await self.client.get_register(regdesc, self.slave_id)
        return Result(VMDCapabilities(result.value), result.status)

    async def ventilation_speed(self) -> Result[VMDVentilationSpeed]:
        """Get the ventilation unit active speed preset."""
        regdesc = self.regmap[Reg.CURRENT_VENTILATION_SPEED]
        result = await self.client.get_register(regdesc, self.slave_id)
        return Result(VMDVentilationSpeed(result.value), result.status)

    async def set_ventilation_speed(self, speed: VMDRequestedVentilationSpeed) -> bool:
        """Set the ventilation unit speed preset."""
        return await self.client.set_register(
            self.regmap[Reg.REQUESTED_VENTILATION_SPEED], speed, self.slave_id
        )

    async def set_ventilation_speed_override_time(
        self, speed: VMDRequestedVentilationSpeed, minutes: int
    ) -> bool:
        """Set the ventilation unit speed preset for a limited time."""
        if minutes > 18 * 60:
            raise AiriosInvalidArgumentException("Maximum speed override time is 18 hours")
        if speed == VMDRequestedVentilationSpeed.LOW:
            return await self.client.set_register(
                self.regmap[Reg.OVERRIDE_TIME_SPEED_LOW], minutes, self.slave_id
            )
        if speed == VMDRequestedVentilationSpeed.MID:
            return await self.client.set_register(
                self.regmap[Reg.OVERRIDE_TIME_SPEED_MID], minutes, self.slave_id
            )
        if speed == VMDRequestedVentilationSpeed.HIGH:
            return await self.client.set_register(
                self.regmap[Reg.OVERRIDE_TIME_SPEED_HIGH], minutes, self.slave_id
            )
        raise AiriosInvalidArgumentException(f"Invalid temporary override speed {speed}")

    async def preset_away_fans_speed(self) -> VMDPresetFansSpeeds:
        """Get the away ventilation speed preset fan speeds."""
        r1 = await self.client.get_register(self.regmap[Reg.FAN_SPEED_AWAY_SUPPLY], self.slave_id)
        r2 = await self.client.get_register(self.regmap[Reg.FAN_SPEED_AWAY_EXHAUST], self.slave_id)
        return VMDPresetFansSpeeds(supply_fan_speed=r1, exhaust_fan_speed=r2)

    async def set_preset_away_fans_speed(self, supply: int, exhaust: int) -> bool:
        """Set the away ventilation speed preset fan speeds."""
        if supply < 0 or exhaust < 0:
            raise AiriosInvalidArgumentException("Speed must be in range 0-40 %")
        if supply > 40 or exhaust > 40:
            raise AiriosInvalidArgumentException("Speed must be in range 0-40 %")
        r1 = await self.client.set_register(
            self.regmap[Reg.FAN_SPEED_AWAY_SUPPLY], supply, self.slave_id
        )
        r2 = await self.client.set_register(
            self.regmap[Reg.FAN_SPEED_AWAY_EXHAUST], exhaust, self.slave_id
        )
        return r1 and r2

    async def preset_low_fans_speed(self) -> VMDPresetFansSpeeds:
        """Get the low ventilation speed preset fan speeds."""
        r1 = await self.client.get_register(self.regmap[Reg.FAN_SPEED_LOW_SUPPLY], self.slave_id)
        r2 = await self.client.get_register(self.regmap[Reg.FAN_SPEED_LOW_EXHAUST], self.slave_id)
        return VMDPresetFansSpeeds(supply_fan_speed=r1, exhaust_fan_speed=r2)

    async def set_preset_low_fans_speed(self, supply: int, exhaust: int) -> bool:
        """Set the low ventilation speed preset fan speeds."""
        if supply < 0 or exhaust < 0:
            raise AiriosInvalidArgumentException("Speed must be in range 0-40 %")
        if supply > 80 or exhaust > 80:
            raise AiriosInvalidArgumentException("Speed must be in range 0-40 %")
        r1 = await self.client.set_register(
            self.regmap[Reg.FAN_SPEED_LOW_SUPPLY], supply, self.slave_id
        )
        r2 = await self.client.set_register(
            self.regmap[Reg.FAN_SPEED_LOW_EXHAUST], exhaust, self.slave_id
        )
        return r1 and r2

    async def preset_mid_fans_speed(self) -> VMDPresetFansSpeeds:
        """Get the mid ventilation speed preset fan speeds."""
        r1 = await self.client.get_register(self.regmap[Reg.FAN_SPEED_MID_SUPPLY], self.slave_id)
        r2 = await self.client.get_register(self.regmap[Reg.FAN_SPEED_MID_EXHAUST], self.slave_id)
        return VMDPresetFansSpeeds(supply_fan_speed=r1, exhaust_fan_speed=r2)

    async def set_preset_mid_fans_speed(self, supply: int, exhaust: int) -> bool:
        """Set the mid ventilation speed preset fan speeds."""
        if supply < 0 or exhaust < 0:
            raise AiriosInvalidArgumentException("Speed must be in range 0-40 %")
        if supply > 100 or exhaust > 100:
            raise AiriosInvalidArgumentException("Speed must be in range 0-40 %")
        r1 = await self.client.set_register(
            self.regmap[Reg.FAN_SPEED_MID_SUPPLY], supply, self.slave_id
        )
        r2 = await self.client.set_register(
            self.regmap[Reg.FAN_SPEED_MID_EXHAUST], exhaust, self.slave_id
        )
        return r1 and r2

    async def preset_high_fans_speed(self) -> VMDPresetFansSpeeds:
        """Get the high ventilation speed preset fan speeds."""
        r1 = await self.client.get_register(self.regmap[Reg.FAN_SPEED_HIGH_SUPPLY], self.slave_id)
        r2 = await self.client.get_register(self.regmap[Reg.FAN_SPEED_HIGH_EXHAUST], self.slave_id)
        return VMDPresetFansSpeeds(supply_fan_speed=r1, exhaust_fan_speed=r2)

    async def set_preset_high_fans_speed(self, supply: int, exhaust: int) -> bool:
        """Set the high ventilation speed preset fan speeds."""
        if supply < 0 or exhaust < 0:
            raise AiriosInvalidArgumentException("Speed must be in range 0-40 %")
        if supply > 100 or exhaust > 100:
            raise AiriosInvalidArgumentException("Speed must be in range 0-40 %")
        r1 = await self.client.set_register(
            self.regmap[Reg.FAN_SPEED_HIGH_SUPPLY], supply, self.slave_id
        )
        r2 = await self.client.set_register(
            self.regmap[Reg.FAN_SPEED_HIGH_EXHAUST], exhaust, self.slave_id
        )
        return r1 and r2

    async def bypass_mode(self) -> Result[VMDBypassMode]:
        """Get the bypass mode."""
        regdesc = self.regmap[Reg.BYPASS_MODE]
        result = await self.client.get_register(regdesc, self.slave_id)
        try:
            mode = VMDBypassMode(result.value)
        except ValueError:
            mode = VMDBypassMode.UNKNOWN
        return Result(mode, result.status)

    async def set_bypass_mode(self, mode: VMDBypassMode) -> bool:
        """Set the bypass mode."""
        if mode == VMDBypassMode.UNKNOWN:
            raise AiriosInvalidArgumentException(f"Invalid bypass mode {mode}")
        return await self.client.set_register(
            self.regmap[Reg.REQUESTED_BYPASS_MODE], mode, self.slave_id
        )

    async def bypass_status(self) -> Result[int]:
        """Get the bypass status."""
        return await self.client.get_register(self.regmap[Reg.BYPASS_STATUS], self.slave_id)

    async def bypass_position(self) -> Result[VMDBypassPosition]:
        """Get the bypass position."""
        regdesc = self.regmap[Reg.BYPASS_POSITION]
        result = await self.client.get_register(regdesc, self.slave_id)
        error = result.value > 120
        return Result(VMDBypassPosition(result.value, error), result.status)

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

    async def exhaust_fan_speed(self) -> Result[int]:
        """Get the exhaust fan speed (%)"""
        return await self.client.get_register(self.regmap[Reg.FAN_SPEED_EXHAUST], self.slave_id)

    async def supply_fan_speed(self) -> Result[int]:
        """Get the supply fan speed (%)"""
        return await self.client.get_register(self.regmap[Reg.FAN_SPEED_SUPPLY], self.slave_id)

    async def exhaust_fan_rpm(self) -> Result[int]:
        """Get the exhaust fan speed (RPM)"""
        return await self.client.get_register(self.regmap[Reg.FAN_RPM_EXHAUST], self.slave_id)

    async def supply_fan_rpm(self) -> Result[int]:
        """Get the supply fan speed (RPM)"""
        return await self.client.get_register(self.regmap[Reg.FAN_RPM_SUPPLY], self.slave_id)

    async def override_remaining_time(self) -> Result[int]:
        """Get the ventilation speed override remaining time."""
        return await self.client.get_register(
            self.regmap[Reg.VENTILATION_SPEED_OVERRIDE_REMAINING_TIME], self.slave_id
        )

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
        return Result(VMDTemperature(result.value, status), result.status)

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
        return Result(VMDTemperature(result.value, status), result.status)

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
        return Result(VMDTemperature(result.value, status), result.status)

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
        return Result(VMDTemperature(result.value, status), result.status)

    async def defrost(self) -> Result[int]:
        """Get if defrost is active."""
        return await self.client.get_register(self.regmap[Reg.DEFROST], self.slave_id)

    async def preheater(self) -> Result[VMDHeater]:
        """Get the preheater level."""
        regdesc = self.regmap[Reg.PREHEATER]
        result = await self.client.get_register(regdesc, self.slave_id)
        status = VMDHeaterStatus.UNAVAILABLE if result.value == 0xEF else VMDHeaterStatus.OK
        return Result(VMDHeater(result.value, status), result.status)

    async def postheater(self) -> Result[VMDHeater]:
        """Get the postheater level."""
        regdesc = self.regmap[Reg.POST_HEATER]
        result = await self.client.get_register(regdesc, self.slave_id)
        status = VMDHeaterStatus.UNAVAILABLE if result.value == 0xEF else VMDHeaterStatus.OK
        return Result(VMDHeater(result.value, status), result.status)

    async def preheater_setpoint(self) -> Result[float]:
        """Get the preheater setpoint."""
        return await self.client.get_register(self.regmap[Reg.PREHEATER_SETPOINT], self.slave_id)

    async def set_preheater_setpoint(self, value: float) -> bool:
        """Set the preheater setpoint."""
        return await self.client.set_register(
            self.regmap[Reg.PREHEATER_SETPOINT], value, self.slave_id
        )

    async def free_ventilation_setpoint(self) -> Result[float]:
        """Get the free ventilation setpoint."""
        return await self.client.get_register(
            self.regmap[Reg.FREE_VENTILATION_HEATING_SETPOINT], self.slave_id
        )

    async def set_free_ventilation_setpoint(self, value: float) -> bool:
        """Set the free ventilation setpoint."""
        return await self.client.set_register(
            self.regmap[Reg.FREE_VENTILATION_HEATING_SETPOINT], value, self.slave_id
        )

    async def free_ventilation_cooling_offset(self) -> Result[float]:
        """Get the free ventilation cooling offset."""
        return await self.client.get_register(
            self.regmap[Reg.FREE_VENTILATION_COOLING_OFFSET], self.slave_id
        )

    async def set_free_ventilation_cooling_offset(self, value: float) -> bool:
        """Set the free ventilation cooling offset."""
        return await self.client.set_register(
            self.regmap[Reg.FREE_VENTILATION_COOLING_OFFSET], value, self.slave_id
        )

    async def frost_protection_preheater_setpoint(self) -> Result[float]:
        """Get the frost protection preheater setpoint."""
        return await self.client.get_register(
            self.regmap[Reg.FROST_PROTECTION_PREHEATER_SETPOINT], self.slave_id
        )

    async def set_frost_protection_preheater_setpoint(self, value: float) -> bool:
        """Set the frost protection preheater setpoint."""
        return await self.client.set_register(
            self.regmap[Reg.FROST_PROTECTION_PREHEATER_SETPOINT], value, self.slave_id
        )

    async def preset_high_fan_speed_supply(self) -> Result[int]:
        """Get the supply fan speed for the high preset."""
        return await self.client.get_register(self.regmap[Reg.FAN_SPEED_HIGH_SUPPLY], self.slave_id)

    async def set_preset_high_fan_speed_supply(self, value: int) -> bool:
        """Set the supply fan speed for the high preset."""
        return await self.client.set_register(
            self.regmap[Reg.FAN_SPEED_HIGH_SUPPLY], value, self.slave_id
        )

    async def preset_high_fan_speed_exhaust(self) -> Result[int]:
        """Get the exhaust fan speed for the high preset."""
        return await self.client.get_register(
            self.regmap[Reg.FAN_SPEED_HIGH_EXHAUST], self.slave_id
        )

    async def set_preset_high_fan_speed_exhaust(self, value: int) -> bool:
        """Set the exhaust fan speed for the high preset."""
        return await self.client.set_register(
            self.regmap[Reg.FAN_SPEED_HIGH_EXHAUST], value, self.slave_id
        )

    async def preset_medium_fan_speed_supply(self) -> Result[int]:
        """Get the supply fan speed for the medium preset."""
        return await self.client.get_register(self.regmap[Reg.FAN_SPEED_MID_SUPPLY], self.slave_id)

    async def set_preset_medium_fan_speed_supply(self, value: int) -> bool:
        """Set the supply fan speed for the medium preset."""
        return await self.client.set_register(
            self.regmap[Reg.FAN_SPEED_MID_SUPPLY], value, self.slave_id
        )

    async def preset_medium_fan_speed_exhaust(self) -> Result[int]:
        """Get the exhaust fan speed for the medium preset."""
        return await self.client.get_register(self.regmap[Reg.FAN_SPEED_MID_EXHAUST], self.slave_id)

    async def set_preset_medium_fan_speed_exhaust(self, value: int) -> bool:
        """Set the exhaust fan speed for the medium preset."""
        return await self.client.set_register(
            self.regmap[Reg.FAN_SPEED_MID_EXHAUST], value, self.slave_id
        )

    async def preset_low_fan_speed_supply(self) -> Result[int]:
        """Get the supply fan speed for the low preset."""
        return await self.client.get_register(self.regmap[Reg.FAN_SPEED_LOW_SUPPLY], self.slave_id)

    async def set_preset_low_fan_speed_supply(self, value: int) -> bool:
        """Set the supply fan speed for the low preset."""
        return await self.client.set_register(
            self.regmap[Reg.FAN_SPEED_LOW_SUPPLY], value, self.slave_id
        )

    async def preset_low_fan_speed_exhaust(self) -> Result[int]:
        """Get the exhaust fan speed for the low preset."""
        return await self.client.get_register(self.regmap[Reg.FAN_SPEED_LOW_EXHAUST], self.slave_id)

    async def set_preset_low_fan_speed_exhaust(self, value: int) -> bool:
        """Set the exhaust fan speed for the low preset."""
        return await self.client.set_register(
            self.regmap[Reg.FAN_SPEED_LOW_EXHAUST], value, self.slave_id
        )

    async def preset_standby_fan_speed_supply(self) -> Result[int]:
        """Get the supply fan speed for the standby preset."""
        return await self.client.get_register(self.regmap[Reg.FAN_SPEED_AWAY_SUPPLY], self.slave_id)

    async def set_preset_standby_fan_speed_supply(self, value: int) -> bool:
        """Set the supply fan speed for the standby preset."""
        return await self.client.set_register(
            self.regmap[Reg.FAN_SPEED_AWAY_SUPPLY], value, self.slave_id
        )

    async def preset_standby_fan_speed_exhaust(self) -> Result[int]:
        """Get the exhaust fan speed for the standby preset."""
        return await self.client.get_register(
            self.regmap[Reg.FAN_SPEED_AWAY_EXHAUST], self.slave_id
        )

    async def set_preset_standby_fan_speed_exhaust(self, value: int) -> bool:
        """Set the exhaust fan speed for the standby preset."""
        return await self.client.set_register(
            self.regmap[Reg.FAN_SPEED_AWAY_EXHAUST], value, self.slave_id
        )

    async def fetch_vmd_data(self) -> VMD02RPS78Data:  # pylint: disable=duplicate-code
        """Fetch all controller data at once."""

        return VMD02RPS78Data(
            slave_id=self.slave_id,
            rf_address=await self._safe_fetch(self.node_rf_address),
            product_id=await self._safe_fetch(self.node_product_id),
            sw_version=await self._safe_fetch(self.node_software_version),
            product_name=await self._safe_fetch(self.node_product_name),
            rf_comm_status=await self._safe_fetch(self.node_rf_comm_status),
            battery_status=await self._safe_fetch(self.node_battery_status),
            fault_status=await self._safe_fetch(self.node_fault_status),
            bound_status=await self._safe_fetch(self.device_bound_status),
            value_error_status=await self._safe_fetch(self.device_value_error_status),
            error_code=await self._safe_fetch(self.error_code),
            ventilation_speed=await self._safe_fetch(self.ventilation_speed),
            exhaust_fan_speed=await self._safe_fetch(self.exhaust_fan_speed),
            supply_fan_speed=await self._safe_fetch(self.supply_fan_speed),
            exhaust_fan_rpm=await self._safe_fetch(self.exhaust_fan_rpm),
            supply_fan_rpm=await self._safe_fetch(self.supply_fan_rpm),
            override_remaining_time=await self._safe_fetch(self.override_remaining_time),
            indoor_air_temperature=await self._safe_fetch(self.indoor_air_temperature),
            outdoor_air_temperature=await self._safe_fetch(self.outdoor_air_temperature),
            exhaust_air_temperature=await self._safe_fetch(self.exhaust_air_temperature),
            supply_air_temperature=await self._safe_fetch(self.supply_air_temperature),
            filter_dirty=await self._safe_fetch(self.filter_dirty),
            filter_remaining_percent=await self._safe_fetch(self.filter_remaining),
            filter_duration_days=await self._safe_fetch(self.filter_duration),
            defrost=await self._safe_fetch(self.defrost),
            bypass_position=await self._safe_fetch(self.bypass_position),
            bypass_mode=await self._safe_fetch(self.bypass_mode),
            bypass_status=await self._safe_fetch(self.bypass_status),
            preheater=await self._safe_fetch(self.preheater),
            postheater=await self._safe_fetch(self.postheater),
            preheater_setpoint=await self._safe_fetch(self.preheater_setpoint),
            free_ventilation_setpoint=await self._safe_fetch(self.free_ventilation_setpoint),
            free_ventilation_cooling_offset=await self._safe_fetch(
                self.free_ventilation_cooling_offset
            ),
            frost_protection_preheater_setpoint=await self._safe_fetch(
                self.frost_protection_preheater_setpoint
            ),
            preset_high_fan_speed_supply=await self._safe_fetch(self.preset_high_fan_speed_supply),
            preset_high_fan_speed_exhaust=await self._safe_fetch(
                self.preset_high_fan_speed_exhaust
            ),
            preset_medium_fan_speed_supply=await self._safe_fetch(
                self.preset_medium_fan_speed_supply
            ),
            preset_medium_fan_speed_exhaust=await self._safe_fetch(
                self.preset_medium_fan_speed_exhaust
            ),
            preset_low_fan_speed_supply=await self._safe_fetch(self.preset_low_fan_speed_supply),
            preset_low_fan_speed_exhaust=await self._safe_fetch(self.preset_low_fan_speed_exhaust),
            preset_standby_fan_speed_supply=await self._safe_fetch(
                self.preset_standby_fan_speed_supply
            ),
            preset_standby_fan_speed_exhaust=await self._safe_fetch(
                self.preset_standby_fan_speed_exhaust
            ),
        )
