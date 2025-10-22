"""Airios VMD-02RPS78 controller implementation."""

from __future__ import annotations

import logging
import math
from typing import List

from pyairios.client import AsyncAiriosModbusClient
from pyairios.constants import (
    ProductId,
    VMDBypassMode,
    VMDBypassPosition,
    VMDCapabilities,
    VMDErrorCode,
    VMDHeater,
    VMDHeaterStatus,
    VMDPresetFansSpeeds,
    VMDRequestedVentilationSpeed,
    VMDSensorStatus,
    VMDTemperature,
    VMDVentilationSpeed,
)
from pyairios.exceptions import AiriosInvalidArgumentException
from pyairios.node import AiriosNode
from pyairios.properties import AiriosVMDProperty as vp
from pyairios.registers import (
    FloatRegister,
    RegisterAccess,
    RegisterBase,
    Result,
    U16Register,
)

LOGGER = logging.getLogger(__name__)


def pr_id() -> ProductId:
    """
    Get product_id for model VMD_02RPS78.
    Named as is to discern from product_id register.
    """
    return ProductId.VMD_02RPS78


def pr_description() -> str | tuple[str, ...]:
    """
    Get description of product(s) using VMD_02RPS78.
    Human-readable text, used in e.g. HomeAssistant Binding UI.
    :return: string or tuple of strings, starting with manufacturer
    """
    return ("Siber DF Evo", "Siber DF Optima 2")


def pr_instantiate(device_id: int, client: AsyncAiriosModbusClient) -> VMD02RPS78:
    """Get a new device instance. Used by the device factory to instantiate by product ID."""
    return VMD02RPS78(device_id, client)


def _temperature_adapter(value: float) -> VMDTemperature:
    if math.isnan(value):
        status = VMDSensorStatus.UNAVAILABLE
    elif value < -273.0:
        status = VMDSensorStatus.ERROR
    else:
        status = VMDSensorStatus.OK
    return VMDTemperature(value, status)


class VMD02RPS78(AiriosNode):
    """Represents a VMD-02RPS78 controller node."""

    def __init__(self, device_id: int, client: AsyncAiriosModbusClient) -> None:
        """Initialize the VMD-02RPS78 controller node instance."""
        super().__init__(device_id, client)
        vmd_registers: List[RegisterBase] = [
            U16Register(
                vp.CURRENT_VENTILATION_SPEED, 41000, RegisterAccess.READ | RegisterAccess.STATUS
            ),
            U16Register(vp.FAN_SPEED_EXHAUST, 41001, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(vp.FAN_SPEED_SUPPLY, 41002, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(vp.ERROR_CODE, 41003, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(
                vp.VENTILATION_SPEED_OVERRIDE_REMAINING_TIME,
                41004,
                RegisterAccess.READ | RegisterAccess.STATUS,
            ),
            FloatRegister(
                vp.TEMPERATURE_EXHAUST,
                41005,
                RegisterAccess.READ | RegisterAccess.STATUS,
                result_adapter=_temperature_adapter,
            ),
            FloatRegister(
                vp.TEMPERATURE_INLET,
                41007,
                RegisterAccess.READ | RegisterAccess.STATUS,
                result_adapter=_temperature_adapter,
            ),
            FloatRegister(
                vp.TEMPERATURE_OUTLET,
                41009,
                RegisterAccess.READ | RegisterAccess.STATUS,
                result_adapter=_temperature_adapter,
            ),
            FloatRegister(
                vp.TEMPERATURE_SUPPLY,
                41011,
                RegisterAccess.READ | RegisterAccess.STATUS,
                result_adapter=_temperature_adapter,
            ),
            U16Register(vp.PREHEATER, 41013, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(vp.FILTER_DIRTY, 41014, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(vp.DEFROST, 41015, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(vp.BYPASS_POSITION, 41016, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(vp.HUMIDITY_INDOOR, 41017, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(vp.HUMIDITY_OUTDOOR, 41018, RegisterAccess.READ | RegisterAccess.STATUS),
            FloatRegister(vp.FLOW_INLET, 41019, RegisterAccess.READ | RegisterAccess.STATUS),
            FloatRegister(vp.FLOW_OUTLET, 41021, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(vp.AIR_QUALITY, 41023, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(vp.AIR_QUALITY_BASIS, 41024, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(vp.CO2_LEVEL, 41025, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(vp.POSTHEATER, 41026, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(vp.CAPABILITIES, 41027, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(
                vp.FILTER_REMAINING_DAYS, 41040, RegisterAccess.READ | RegisterAccess.STATUS
            ),
            U16Register(vp.FILTER_DURATION, 41041, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(
                vp.FILTER_REMAINING_PERCENT, 41042, RegisterAccess.READ | RegisterAccess.STATUS
            ),
            U16Register(vp.FAN_RPM_EXHAUST, 41043, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(vp.FAN_RPM_SUPPLY, 41044, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(vp.BYPASS_MODE, 41050, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(vp.BYPASS_STATUS, 41051, RegisterAccess.READ | RegisterAccess.STATUS),
            U16Register(
                vp.REQUESTED_VENTILATION_SPEED,
                41500,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            U16Register(
                vp.OVERRIDE_TIME_SPEED_LOW,
                41501,
                RegisterAccess.WRITE,
                max_value=18 * 60,
            ),
            U16Register(
                vp.OVERRIDE_TIME_SPEED_MID,
                41502,
                RegisterAccess.WRITE,
                max_value=18 * 60,
            ),
            U16Register(
                vp.OVERRIDE_TIME_SPEED_HIGH,
                41503,
                RegisterAccess.WRITE,
                max_value=18 * 60,
            ),
            U16Register(
                vp.REQUESTED_BYPASS_MODE,
                41550,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            U16Register(vp.FILTER_RESET, 42000, RegisterAccess.WRITE | RegisterAccess.STATUS),
            U16Register(
                vp.FAN_SPEED_AWAY_SUPPLY,
                42001,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
                max_value=40,
            ),
            U16Register(
                vp.FAN_SPEED_AWAY_EXHAUST,
                42002,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
                max_value=40,
            ),
            U16Register(
                vp.FAN_SPEED_LOW_SUPPLY,
                42003,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
                max_value=80,
            ),
            U16Register(
                vp.FAN_SPEED_LOW_EXHAUST,
                42004,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
                max_value=80,
            ),
            U16Register(
                vp.FAN_SPEED_MID_SUPPLY,
                42005,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
                max_value=100,
            ),
            U16Register(
                vp.FAN_SPEED_MID_EXHAUST,
                42006,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
                max_value=100,
            ),
            U16Register(
                vp.FAN_SPEED_HIGH_SUPPLY,
                42007,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
                max_value=100,
            ),
            U16Register(
                vp.FAN_SPEED_HIGH_EXHAUST,
                42008,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
                max_value=100,
            ),
            FloatRegister(
                vp.FROST_PROTECTION_PREHEATER_SETPOINT,
                42009,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            FloatRegister(
                vp.PREHEATER_SETPOINT,
                42011,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            FloatRegister(
                vp.FREE_VENTILATION_HEATING_SETPOINT,
                42013,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
            FloatRegister(
                vp.FREE_VENTILATION_COOLING_OFFSET,
                42015,
                RegisterAccess.READ | RegisterAccess.WRITE | RegisterAccess.STATUS,
            ),
        ]
        self._add_registers(vmd_registers)

    def __str__(self) -> str:
        return f"VMD-02RPS78@{self.device_id}"

    async def capabilities(self) -> Result[VMDCapabilities]:
        """Get the ventilation unit capabilities."""
        regdesc = self.regmap[vp.CAPABILITIES]
        result = await self.client.get_register(regdesc, self.device_id)
        return Result(VMDCapabilities(result.value), result.status)

    async def ventilation_speed(self) -> Result[VMDVentilationSpeed]:
        """Get the ventilation unit active speed preset."""
        regdesc = self.regmap[vp.CURRENT_VENTILATION_SPEED]
        result = await self.client.get_register(regdesc, self.device_id)
        return Result(VMDVentilationSpeed(result.value), result.status)

    async def set_ventilation_speed(self, speed: VMDRequestedVentilationSpeed) -> bool:
        """Set the ventilation unit speed preset."""
        return await self.client.set_register(
            self.regmap[vp.REQUESTED_VENTILATION_SPEED], speed, self.device_id
        )

    async def set_ventilation_speed_override_time(
        self, speed: VMDRequestedVentilationSpeed, minutes: int
    ) -> bool:
        """Set the ventilation unit speed preset for a limited time."""
        if speed == VMDRequestedVentilationSpeed.LOW:
            return await self.client.set_register(
                self.regmap[vp.OVERRIDE_TIME_SPEED_LOW], minutes, self.device_id
            )
        if speed == VMDRequestedVentilationSpeed.MID:
            return await self.client.set_register(
                self.regmap[vp.OVERRIDE_TIME_SPEED_MID], minutes, self.device_id
            )
        if speed == VMDRequestedVentilationSpeed.HIGH:
            return await self.client.set_register(
                self.regmap[vp.OVERRIDE_TIME_SPEED_HIGH], minutes, self.device_id
            )
        raise AiriosInvalidArgumentException(f"Invalid temporary override speed {speed}")

    async def preset_away_fans_speed(self) -> VMDPresetFansSpeeds:
        """Get the away ventilation speed preset fan speeds."""
        r1 = await self.client.get_register(self.regmap[vp.FAN_SPEED_AWAY_SUPPLY], self.device_id)
        r2 = await self.client.get_register(self.regmap[vp.FAN_SPEED_AWAY_EXHAUST], self.device_id)
        return VMDPresetFansSpeeds(supply_fan_speed=r1.value, exhaust_fan_speed=r2.value)

    async def set_preset_away_fans_speed(self, supply: int, exhaust: int) -> bool:
        """Set the away ventilation speed preset fan speeds."""
        r1 = await self.client.set_register(
            self.regmap[vp.FAN_SPEED_AWAY_SUPPLY], supply, self.device_id
        )
        r2 = await self.client.set_register(
            self.regmap[vp.FAN_SPEED_AWAY_EXHAUST], exhaust, self.device_id
        )
        return r1 and r2

    async def preset_low_fans_speed(self) -> VMDPresetFansSpeeds:
        """Get the low ventilation speed preset fan speeds."""
        r1 = await self.client.get_register(self.regmap[vp.FAN_SPEED_LOW_SUPPLY], self.device_id)
        r2 = await self.client.get_register(self.regmap[vp.FAN_SPEED_LOW_EXHAUST], self.device_id)
        return VMDPresetFansSpeeds(supply_fan_speed=r1.value, exhaust_fan_speed=r2.value)

    async def set_preset_low_fans_speed(self, supply: int, exhaust: int) -> bool:
        """Set the low ventilation speed preset fan speeds."""
        r1 = await self.client.set_register(
            self.regmap[vp.FAN_SPEED_LOW_SUPPLY], supply, self.device_id
        )
        r2 = await self.client.set_register(
            self.regmap[vp.FAN_SPEED_LOW_EXHAUST], exhaust, self.device_id
        )
        return r1 and r2

    async def preset_mid_fans_speed(self) -> VMDPresetFansSpeeds:
        """Get the mid ventilation speed preset fan speeds."""
        r1 = await self.client.get_register(self.regmap[vp.FAN_SPEED_MID_SUPPLY], self.device_id)
        r2 = await self.client.get_register(self.regmap[vp.FAN_SPEED_MID_EXHAUST], self.device_id)
        return VMDPresetFansSpeeds(supply_fan_speed=r1.value, exhaust_fan_speed=r2.value)

    async def set_preset_mid_fans_speed(self, supply: int, exhaust: int) -> bool:
        """Set the mid ventilation speed preset fan speeds."""
        r1 = await self.client.set_register(
            self.regmap[vp.FAN_SPEED_MID_SUPPLY], supply, self.device_id
        )
        r2 = await self.client.set_register(
            self.regmap[vp.FAN_SPEED_MID_EXHAUST], exhaust, self.device_id
        )
        return r1 and r2

    async def preset_high_fans_speed(self) -> VMDPresetFansSpeeds:
        """Get the high ventilation speed preset fan speeds."""
        r1 = await self.client.get_register(self.regmap[vp.FAN_SPEED_HIGH_SUPPLY], self.device_id)
        r2 = await self.client.get_register(self.regmap[vp.FAN_SPEED_HIGH_EXHAUST], self.device_id)
        return VMDPresetFansSpeeds(supply_fan_speed=r1.value, exhaust_fan_speed=r2.value)

    async def set_preset_high_fans_speed(self, supply: int, exhaust: int) -> bool:
        """Set the high ventilation speed preset fan speeds."""
        r1 = await self.client.set_register(
            self.regmap[vp.FAN_SPEED_HIGH_SUPPLY], supply, self.device_id
        )
        r2 = await self.client.set_register(
            self.regmap[vp.FAN_SPEED_HIGH_EXHAUST], exhaust, self.device_id
        )
        return r1 and r2

    async def bypass_mode(self) -> Result[VMDBypassMode]:
        """Get the bypass mode."""
        regdesc = self.regmap[vp.BYPASS_MODE]
        result = await self.client.get_register(regdesc, self.device_id)
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
            self.regmap[vp.REQUESTED_BYPASS_MODE], mode, self.device_id
        )

    async def bypass_status(self) -> Result[int]:
        """Get the bypass status."""
        return await self.client.get_register(self.regmap[vp.BYPASS_STATUS], self.device_id)

    async def bypass_position(self) -> Result[VMDBypassPosition]:
        """Get the bypass position."""
        regdesc = self.regmap[vp.BYPASS_POSITION]
        result = await self.client.get_register(regdesc, self.device_id)
        error = result.value > 120
        return Result(VMDBypassPosition(result.value, error), result.status)

    async def filter_duration(self) -> Result[int]:
        """Get the filter duration (in days)."""
        return await self.client.get_register(self.regmap[vp.FILTER_DURATION], self.device_id)

    async def filter_remaining_days(self) -> Result[int]:
        """Get the filter remaining lifetime (in days)."""
        return await self.client.get_register(self.regmap[vp.FILTER_REMAINING_DAYS], self.device_id)

    async def filter_remaining(self) -> Result[int]:
        """Get the filter remaining lifetime (in %)."""
        return await self.client.get_register(
            self.regmap[vp.FILTER_REMAINING_PERCENT], self.device_id
        )

    async def filter_reset(self) -> bool:
        """Reset the filter dirty status."""
        return await self.client.set_register(self.regmap[vp.FILTER_RESET], 0, self.device_id)

    async def filter_dirty(self) -> Result[int]:
        """Get the filter dirty status."""
        return await self.client.get_register(self.regmap[vp.FILTER_DIRTY], self.device_id)

    async def error_code(self) -> Result[VMDErrorCode]:
        """Get the ventilation unit error code."""
        regdesc = self.regmap[vp.ERROR_CODE]
        result = await self.client.get_register(regdesc, self.device_id)
        return Result(VMDErrorCode(result.value), result.status)

    async def exhaust_fan_speed(self) -> Result[int]:
        """Get the exhaust fan speed (%)"""
        return await self.client.get_register(self.regmap[vp.FAN_SPEED_EXHAUST], self.device_id)

    async def supply_fan_speed(self) -> Result[int]:
        """Get the supply fan speed (%)"""
        return await self.client.get_register(self.regmap[vp.FAN_SPEED_SUPPLY], self.device_id)

    async def exhaust_fan_rpm(self) -> Result[int]:
        """Get the exhaust fan speed (RPM)"""
        return await self.client.get_register(self.regmap[vp.FAN_RPM_EXHAUST], self.device_id)

    async def supply_fan_rpm(self) -> Result[int]:
        """Get the supply fan speed (RPM)"""
        return await self.client.get_register(self.regmap[vp.FAN_RPM_SUPPLY], self.device_id)

    async def override_remaining_time(self) -> Result[int]:
        """Get the ventilation speed override remaining time."""
        return await self.client.get_register(
            self.regmap[vp.VENTILATION_SPEED_OVERRIDE_REMAINING_TIME], self.device_id
        )

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

    async def supply_air_temperature(self) -> Result[VMDTemperature]:
        """Get the supply air temperature.

        This is the supply flow after the heat exchanger.
        """
        regdesc = self.regmap[vp.TEMPERATURE_SUPPLY]
        return await self.client.get_register(regdesc, self.device_id)

    async def defrost(self) -> Result[int]:
        """Get if defrost is active."""
        return await self.client.get_register(self.regmap[vp.DEFROST], self.device_id)

    async def preheater(self) -> Result[VMDHeater]:
        """Get the preheater level."""
        regdesc = self.regmap[vp.PREHEATER]
        result = await self.client.get_register(regdesc, self.device_id)
        status = VMDHeaterStatus.UNAVAILABLE if result.value == 0xEF else VMDHeaterStatus.OK
        return Result(VMDHeater(result.value, status), result.status)

    async def postheater(self) -> Result[VMDHeater]:
        """Get the postheater level."""
        regdesc = self.regmap[vp.POSTHEATER]
        result = await self.client.get_register(regdesc, self.device_id)
        status = VMDHeaterStatus.UNAVAILABLE if result.value == 0xEF else VMDHeaterStatus.OK
        return Result(VMDHeater(result.value, status), result.status)

    async def preheater_setpoint(self) -> Result[float]:
        """Get the preheater setpoint."""
        return await self.client.get_register(self.regmap[vp.PREHEATER_SETPOINT], self.device_id)

    async def set_preheater_setpoint(self, value: float) -> bool:
        """Set the preheater setpoint."""
        return await self.client.set_register(
            self.regmap[vp.PREHEATER_SETPOINT], value, self.device_id
        )

    async def free_ventilation_setpoint(self) -> Result[float]:
        """Get the free ventilation setpoint."""
        return await self.client.get_register(
            self.regmap[vp.FREE_VENTILATION_HEATING_SETPOINT], self.device_id
        )

    async def set_free_ventilation_setpoint(self, value: float) -> bool:
        """Set the free ventilation setpoint."""
        return await self.client.set_register(
            self.regmap[vp.FREE_VENTILATION_HEATING_SETPOINT], value, self.device_id
        )

    async def free_ventilation_cooling_offset(self) -> Result[float]:
        """Get the free ventilation cooling offset."""
        return await self.client.get_register(
            self.regmap[vp.FREE_VENTILATION_COOLING_OFFSET], self.device_id
        )

    async def set_free_ventilation_cooling_offset(self, value: float) -> bool:
        """Set the free ventilation cooling offset."""
        return await self.client.set_register(
            self.regmap[vp.FREE_VENTILATION_COOLING_OFFSET], value, self.device_id
        )

    async def frost_protection_preheater_setpoint(self) -> Result[float]:
        """Get the frost protection preheater setpoint."""
        return await self.client.get_register(
            self.regmap[vp.FROST_PROTECTION_PREHEATER_SETPOINT], self.device_id
        )

    async def set_frost_protection_preheater_setpoint(self, value: float) -> bool:
        """Set the frost protection preheater setpoint."""
        return await self.client.set_register(
            self.regmap[vp.FROST_PROTECTION_PREHEATER_SETPOINT], value, self.device_id
        )

    async def preset_high_fan_speed_supply(self) -> Result[int]:
        """Get the supply fan speed for the high preset."""
        return await self.client.get_register(self.regmap[vp.FAN_SPEED_HIGH_SUPPLY], self.device_id)

    async def set_preset_high_fan_speed_supply(self, value: int) -> bool:
        """Set the supply fan speed for the high preset."""
        return await self.client.set_register(
            self.regmap[vp.FAN_SPEED_HIGH_SUPPLY], value, self.device_id
        )

    async def preset_high_fan_speed_exhaust(self) -> Result[int]:
        """Get the exhaust fan speed for the high preset."""
        return await self.client.get_register(
            self.regmap[vp.FAN_SPEED_HIGH_EXHAUST], self.device_id
        )

    async def set_preset_high_fan_speed_exhaust(self, value: int) -> bool:
        """Set the exhaust fan speed for the high preset."""
        return await self.client.set_register(
            self.regmap[vp.FAN_SPEED_HIGH_EXHAUST], value, self.device_id
        )

    async def preset_medium_fan_speed_supply(self) -> Result[int]:
        """Get the supply fan speed for the medium preset."""
        return await self.client.get_register(self.regmap[vp.FAN_SPEED_MID_SUPPLY], self.device_id)

    async def set_preset_medium_fan_speed_supply(self, value: int) -> bool:
        """Set the supply fan speed for the medium preset."""
        return await self.client.set_register(
            self.regmap[vp.FAN_SPEED_MID_SUPPLY], value, self.device_id
        )

    async def preset_medium_fan_speed_exhaust(self) -> Result[int]:
        """Get the exhaust fan speed for the medium preset."""
        return await self.client.get_register(self.regmap[vp.FAN_SPEED_MID_EXHAUST], self.device_id)

    async def set_preset_medium_fan_speed_exhaust(self, value: int) -> bool:
        """Set the exhaust fan speed for the medium preset."""
        return await self.client.set_register(
            self.regmap[vp.FAN_SPEED_MID_EXHAUST], value, self.device_id
        )

    async def preset_low_fan_speed_supply(self) -> Result[int]:
        """Get the supply fan speed for the low preset."""
        return await self.client.get_register(self.regmap[vp.FAN_SPEED_LOW_SUPPLY], self.device_id)

    async def set_preset_low_fan_speed_supply(self, value: int) -> bool:
        """Set the supply fan speed for the low preset."""
        return await self.client.set_register(
            self.regmap[vp.FAN_SPEED_LOW_SUPPLY], value, self.device_id
        )

    async def preset_low_fan_speed_exhaust(self) -> Result[int]:
        """Get the exhaust fan speed for the low preset."""
        return await self.client.get_register(self.regmap[vp.FAN_SPEED_LOW_EXHAUST], self.device_id)

    async def set_preset_low_fan_speed_exhaust(self, value: int) -> bool:
        """Set the exhaust fan speed for the low preset."""
        return await self.client.set_register(
            self.regmap[vp.FAN_SPEED_LOW_EXHAUST], value, self.device_id
        )

    async def preset_standby_fan_speed_supply(self) -> Result[int]:
        """Get the supply fan speed for the standby preset."""
        return await self.client.get_register(self.regmap[vp.FAN_SPEED_AWAY_SUPPLY], self.device_id)

    async def set_preset_standby_fan_speed_supply(self, value: int) -> bool:
        """Set the supply fan speed for the standby preset."""
        return await self.client.set_register(
            self.regmap[vp.FAN_SPEED_AWAY_SUPPLY], value, self.device_id
        )

    async def preset_standby_fan_speed_exhaust(self) -> Result[int]:
        """Get the exhaust fan speed for the standby preset."""
        return await self.client.get_register(
            self.regmap[vp.FAN_SPEED_AWAY_EXHAUST], self.device_id
        )

    async def set_preset_standby_fan_speed_exhaust(self, value: int) -> bool:
        """Set the exhaust fan speed for the standby preset."""
        return await self.client.set_register(
            self.regmap[vp.FAN_SPEED_AWAY_EXHAUST], value, self.device_id
        )
