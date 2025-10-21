"""Airios VMD-02RPS78 controller implementation."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import List

from pyairios.client import AsyncAiriosModbusClient
from pyairios.constants import (
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
from pyairios.data_model import VMD02RPS78Data
from pyairios.device import AiriosDevice
from pyairios.exceptions import AiriosInvalidArgumentException
from pyairios.registers import (
    FloatRegister,
    RegisterAccess,
    RegisterBase,
    Result,
    U16Register,
)
from pyairios.properties import AiriosVMDProperty as vp

LOGGER = logging.getLogger(__name__)


@dataclass
class VMDPresetFansSpeeds:
    """Preset fan speeds."""

    exhaust_fan_speed: Result[int]
    """Exhaust fan speed (%)"""
    supply_fan_speed: Result[int]
    """Supply fan speed (%)"""


class VMD02RPS78(AiriosDevice):
    """Represents a VMD-02RPS78 controller node."""

    def __init__(self, slave_id: int, client: AsyncAiriosModbusClient) -> None:
        """Initialize the VMD-02RPS78 controller node instance."""
        super().__init__(slave_id, client)
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
                vp.TEMPERATURE_INDOOR, 41005, RegisterAccess.READ | RegisterAccess.STATUS
            ),
            FloatRegister(
                vp.TEMPERATURE_OUTDOOR, 41007, RegisterAccess.READ | RegisterAccess.STATUS
            ),
            FloatRegister(
                vp.TEMPERATURE_EXHAUST, 41009, RegisterAccess.READ | RegisterAccess.STATUS
            ),
            FloatRegister(
                vp.TEMPERATURE_SUPPLY, 41011, RegisterAccess.READ | RegisterAccess.STATUS
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
            U16Register(vp.POST_HEATER, 41026, RegisterAccess.READ | RegisterAccess.STATUS),
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
        return f"VMD-02RPS78@{self.slave_id}"

    async def capabilities(self) -> Result[VMDCapabilities]:
        """Get the ventilation unit capabilities."""
        regdesc = self.regmap[vp.CAPABILITIES]
        result = await self.client.get_register(regdesc, self.slave_id)
        return Result(VMDCapabilities(result.value), result.status)

    async def ventilation_speed(self) -> Result[VMDVentilationSpeed]:
        """Get the ventilation unit active speed preset."""
        regdesc = self.regmap[vp.CURRENT_VENTILATION_SPEED]
        result = await self.client.get_register(regdesc, self.slave_id)
        return Result(VMDVentilationSpeed(result.value), result.status)

    async def set_ventilation_speed(self, speed: VMDRequestedVentilationSpeed) -> bool:
        """Set the ventilation unit speed preset."""
        return await self.client.set_register(
            self.regmap[vp.REQUESTED_VENTILATION_SPEED], speed, self.slave_id
        )

    async def set_ventilation_speed_override_time(
        self, speed: VMDRequestedVentilationSpeed, minutes: int
    ) -> bool:
        """Set the ventilation unit speed preset for a limited time."""
        if speed == VMDRequestedVentilationSpeed.LOW:
            return await self.client.set_register(
                self.regmap[vp.OVERRIDE_TIME_SPEED_LOW], minutes, self.slave_id
            )
        if speed == VMDRequestedVentilationSpeed.MID:
            return await self.client.set_register(
                self.regmap[vp.OVERRIDE_TIME_SPEED_MID], minutes, self.slave_id
            )
        if speed == VMDRequestedVentilationSpeed.HIGH:
            return await self.client.set_register(
                self.regmap[vp.OVERRIDE_TIME_SPEED_HIGH], minutes, self.slave_id
            )
        raise AiriosInvalidArgumentException(f"Invalid temporary override speed {speed}")

    async def preset_away_fans_speed(self) -> VMDPresetFansSpeeds:
        """Get the away ventilation speed preset fan speeds."""
        r1 = await self.client.get_register(self.regmap[vp.FAN_SPEED_AWAY_SUPPLY], self.slave_id)
        r2 = await self.client.get_register(self.regmap[vp.FAN_SPEED_AWAY_EXHAUST], self.slave_id)
        return VMDPresetFansSpeeds(supply_fan_speed=r1, exhaust_fan_speed=r2)

    async def set_preset_away_fans_speed(self, supply: int, exhaust: int) -> bool:
        """Set the away ventilation speed preset fan speeds."""
        r1 = await self.client.set_register(
            self.regmap[vp.FAN_SPEED_AWAY_SUPPLY], supply, self.slave_id
        )
        r2 = await self.client.set_register(
            self.regmap[vp.FAN_SPEED_AWAY_EXHAUST], exhaust, self.slave_id
        )
        return r1 and r2

    async def preset_low_fans_speed(self) -> VMDPresetFansSpeeds:
        """Get the low ventilation speed preset fan speeds."""
        r1 = await self.client.get_register(self.regmap[vp.FAN_SPEED_LOW_SUPPLY], self.slave_id)
        r2 = await self.client.get_register(self.regmap[vp.FAN_SPEED_LOW_EXHAUST], self.slave_id)
        return VMDPresetFansSpeeds(supply_fan_speed=r1, exhaust_fan_speed=r2)

    async def set_preset_low_fans_speed(self, supply: int, exhaust: int) -> bool:
        """Set the low ventilation speed preset fan speeds."""
        r1 = await self.client.set_register(
            self.regmap[vp.FAN_SPEED_LOW_SUPPLY], supply, self.slave_id
        )
        r2 = await self.client.set_register(
            self.regmap[vp.FAN_SPEED_LOW_EXHAUST], exhaust, self.slave_id
        )
        return r1 and r2

    async def preset_mid_fans_speed(self) -> VMDPresetFansSpeeds:
        """Get the mid ventilation speed preset fan speeds."""
        r1 = await self.client.get_register(self.regmap[vp.FAN_SPEED_MID_SUPPLY], self.slave_id)
        r2 = await self.client.get_register(self.regmap[vp.FAN_SPEED_MID_EXHAUST], self.slave_id)
        return VMDPresetFansSpeeds(supply_fan_speed=r1, exhaust_fan_speed=r2)

    async def set_preset_mid_fans_speed(self, supply: int, exhaust: int) -> bool:
        """Set the mid ventilation speed preset fan speeds."""
        r1 = await self.client.set_register(
            self.regmap[vp.FAN_SPEED_MID_SUPPLY], supply, self.slave_id
        )
        r2 = await self.client.set_register(
            self.regmap[vp.FAN_SPEED_MID_EXHAUST], exhaust, self.slave_id
        )
        return r1 and r2

    async def preset_high_fans_speed(self) -> VMDPresetFansSpeeds:
        """Get the high ventilation speed preset fan speeds."""
        r1 = await self.client.get_register(self.regmap[vp.FAN_SPEED_HIGH_SUPPLY], self.slave_id)
        r2 = await self.client.get_register(self.regmap[vp.FAN_SPEED_HIGH_EXHAUST], self.slave_id)
        return VMDPresetFansSpeeds(supply_fan_speed=r1, exhaust_fan_speed=r2)

    async def set_preset_high_fans_speed(self, supply: int, exhaust: int) -> bool:
        """Set the high ventilation speed preset fan speeds."""
        r1 = await self.client.set_register(
            self.regmap[vp.FAN_SPEED_HIGH_SUPPLY], supply, self.slave_id
        )
        r2 = await self.client.set_register(
            self.regmap[vp.FAN_SPEED_HIGH_EXHAUST], exhaust, self.slave_id
        )
        return r1 and r2

    async def bypass_mode(self) -> Result[VMDBypassMode]:
        """Get the bypass mode."""
        regdesc = self.regmap[vp.BYPASS_MODE]
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
            self.regmap[vp.REQUESTED_BYPASS_MODE], mode, self.slave_id
        )

    async def bypass_status(self) -> Result[int]:
        """Get the bypass status."""
        return await self.client.get_register(self.regmap[vp.BYPASS_STATUS], self.slave_id)

    async def bypass_position(self) -> Result[VMDBypassPosition]:
        """Get the bypass position."""
        regdesc = self.regmap[vp.BYPASS_POSITION]
        result = await self.client.get_register(regdesc, self.slave_id)
        error = result.value > 120
        return Result(VMDBypassPosition(result.value, error), result.status)

    async def filter_duration(self) -> Result[int]:
        """Get the filter duration (in days)."""
        return await self.client.get_register(self.regmap[vp.FILTER_DURATION], self.slave_id)

    async def filter_remaining_days(self) -> Result[int]:
        """Get the filter remaining lifetime (in days)."""
        return await self.client.get_register(self.regmap[vp.FILTER_REMAINING_DAYS], self.slave_id)

    async def filter_remaining(self) -> Result[int]:
        """Get the filter remaining lifetime (in %)."""
        return await self.client.get_register(
            self.regmap[vp.FILTER_REMAINING_PERCENT], self.slave_id
        )

    async def filter_reset(self) -> bool:
        """Reset the filter dirty status."""
        return await self.client.set_register(self.regmap[vp.FILTER_RESET], 0, self.slave_id)

    async def filter_dirty(self) -> Result[int]:
        """Get the filter dirty status."""
        return await self.client.get_register(self.regmap[vp.FILTER_DIRTY], self.slave_id)

    async def error_code(self) -> Result[VMDErrorCode]:
        """Get the ventilation unit error code."""
        regdesc = self.regmap[vp.ERROR_CODE]
        result = await self.client.get_register(regdesc, self.slave_id)
        return Result(VMDErrorCode(result.value), result.status)

    async def exhaust_fan_speed(self) -> Result[int]:
        """Get the exhaust fan speed (%)"""
        return await self.client.get_register(self.regmap[vp.FAN_SPEED_EXHAUST], self.slave_id)

    async def supply_fan_speed(self) -> Result[int]:
        """Get the supply fan speed (%)"""
        return await self.client.get_register(self.regmap[vp.FAN_SPEED_SUPPLY], self.slave_id)

    async def exhaust_fan_rpm(self) -> Result[int]:
        """Get the exhaust fan speed (RPM)"""
        return await self.client.get_register(self.regmap[vp.FAN_RPM_EXHAUST], self.slave_id)

    async def supply_fan_rpm(self) -> Result[int]:
        """Get the supply fan speed (RPM)"""
        return await self.client.get_register(self.regmap[vp.FAN_RPM_SUPPLY], self.slave_id)

    async def override_remaining_time(self) -> Result[int]:
        """Get the ventilation speed override remaining time."""
        return await self.client.get_register(
            self.regmap[vp.VENTILATION_SPEED_OVERRIDE_REMAINING_TIME], self.slave_id
        )

    async def indoor_air_temperature(self) -> Result[VMDTemperature]:
        """Get the indoor air temperature.

        This is exhaust flow before the heat exchanger.
        """
        regdesc = self.regmap[vp.TEMPERATURE_INDOOR]
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
        regdesc = self.regmap[vp.TEMPERATURE_OUTDOOR]
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
        regdesc = self.regmap[vp.TEMPERATURE_EXHAUST]
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
        regdesc = self.regmap[vp.TEMPERATURE_SUPPLY]
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
        return await self.client.get_register(self.regmap[vp.DEFROST], self.slave_id)

    async def preheater(self) -> Result[VMDHeater]:
        """Get the preheater level."""
        regdesc = self.regmap[vp.PREHEATER]
        result = await self.client.get_register(regdesc, self.slave_id)
        status = VMDHeaterStatus.UNAVAILABLE if result.value == 0xEF else VMDHeaterStatus.OK
        return Result(VMDHeater(result.value, status), result.status)

    async def postheater(self) -> Result[VMDHeater]:
        """Get the postheater level."""
        regdesc = self.regmap[vp.POST_HEATER]
        result = await self.client.get_register(regdesc, self.slave_id)
        status = VMDHeaterStatus.UNAVAILABLE if result.value == 0xEF else VMDHeaterStatus.OK
        return Result(VMDHeater(result.value, status), result.status)

    async def preheater_setpoint(self) -> Result[float]:
        """Get the preheater setpoint."""
        return await self.client.get_register(self.regmap[vp.PREHEATER_SETPOINT], self.slave_id)

    async def set_preheater_setpoint(self, value: float) -> bool:
        """Set the preheater setpoint."""
        return await self.client.set_register(
            self.regmap[vp.PREHEATER_SETPOINT], value, self.slave_id
        )

    async def free_ventilation_setpoint(self) -> Result[float]:
        """Get the free ventilation setpoint."""
        return await self.client.get_register(
            self.regmap[vp.FREE_VENTILATION_HEATING_SETPOINT], self.slave_id
        )

    async def set_free_ventilation_setpoint(self, value: float) -> bool:
        """Set the free ventilation setpoint."""
        return await self.client.set_register(
            self.regmap[vp.FREE_VENTILATION_HEATING_SETPOINT], value, self.slave_id
        )

    async def free_ventilation_cooling_offset(self) -> Result[float]:
        """Get the free ventilation cooling offset."""
        return await self.client.get_register(
            self.regmap[vp.FREE_VENTILATION_COOLING_OFFSET], self.slave_id
        )

    async def set_free_ventilation_cooling_offset(self, value: float) -> bool:
        """Set the free ventilation cooling offset."""
        return await self.client.set_register(
            self.regmap[vp.FREE_VENTILATION_COOLING_OFFSET], value, self.slave_id
        )

    async def frost_protection_preheater_setpoint(self) -> Result[float]:
        """Get the frost protection preheater setpoint."""
        return await self.client.get_register(
            self.regmap[vp.FROST_PROTECTION_PREHEATER_SETPOINT], self.slave_id
        )

    async def set_frost_protection_preheater_setpoint(self, value: float) -> bool:
        """Set the frost protection preheater setpoint."""
        return await self.client.set_register(
            self.regmap[vp.FROST_PROTECTION_PREHEATER_SETPOINT], value, self.slave_id
        )

    async def preset_high_fan_speed_supply(self) -> Result[int]:
        """Get the supply fan speed for the high preset."""
        return await self.client.get_register(self.regmap[vp.FAN_SPEED_HIGH_SUPPLY], self.slave_id)

    async def set_preset_high_fan_speed_supply(self, value: int) -> bool:
        """Set the supply fan speed for the high preset."""
        return await self.client.set_register(
            self.regmap[vp.FAN_SPEED_HIGH_SUPPLY], value, self.slave_id
        )

    async def preset_high_fan_speed_exhaust(self) -> Result[int]:
        """Get the exhaust fan speed for the high preset."""
        return await self.client.get_register(self.regmap[vp.FAN_SPEED_HIGH_EXHAUST], self.slave_id)

    async def set_preset_high_fan_speed_exhaust(self, value: int) -> bool:
        """Set the exhaust fan speed for the high preset."""
        return await self.client.set_register(
            self.regmap[vp.FAN_SPEED_HIGH_EXHAUST], value, self.slave_id
        )

    async def preset_medium_fan_speed_supply(self) -> Result[int]:
        """Get the supply fan speed for the medium preset."""
        return await self.client.get_register(self.regmap[vp.FAN_SPEED_MID_SUPPLY], self.slave_id)

    async def set_preset_medium_fan_speed_supply(self, value: int) -> bool:
        """Set the supply fan speed for the medium preset."""
        return await self.client.set_register(
            self.regmap[vp.FAN_SPEED_MID_SUPPLY], value, self.slave_id
        )

    async def preset_medium_fan_speed_exhaust(self) -> Result[int]:
        """Get the exhaust fan speed for the medium preset."""
        return await self.client.get_register(self.regmap[vp.FAN_SPEED_MID_EXHAUST], self.slave_id)

    async def set_preset_medium_fan_speed_exhaust(self, value: int) -> bool:
        """Set the exhaust fan speed for the medium preset."""
        return await self.client.set_register(
            self.regmap[vp.FAN_SPEED_MID_EXHAUST], value, self.slave_id
        )

    async def preset_low_fan_speed_supply(self) -> Result[int]:
        """Get the supply fan speed for the low preset."""
        return await self.client.get_register(self.regmap[vp.FAN_SPEED_LOW_SUPPLY], self.slave_id)

    async def set_preset_low_fan_speed_supply(self, value: int) -> bool:
        """Set the supply fan speed for the low preset."""
        return await self.client.set_register(
            self.regmap[vp.FAN_SPEED_LOW_SUPPLY], value, self.slave_id
        )

    async def preset_low_fan_speed_exhaust(self) -> Result[int]:
        """Get the exhaust fan speed for the low preset."""
        return await self.client.get_register(self.regmap[vp.FAN_SPEED_LOW_EXHAUST], self.slave_id)

    async def set_preset_low_fan_speed_exhaust(self, value: int) -> bool:
        """Set the exhaust fan speed for the low preset."""
        return await self.client.set_register(
            self.regmap[vp.FAN_SPEED_LOW_EXHAUST], value, self.slave_id
        )

    async def preset_standby_fan_speed_supply(self) -> Result[int]:
        """Get the supply fan speed for the standby preset."""
        return await self.client.get_register(self.regmap[vp.FAN_SPEED_AWAY_SUPPLY], self.slave_id)

    async def set_preset_standby_fan_speed_supply(self, value: int) -> bool:
        """Set the supply fan speed for the standby preset."""
        return await self.client.set_register(
            self.regmap[vp.FAN_SPEED_AWAY_SUPPLY], value, self.slave_id
        )

    async def preset_standby_fan_speed_exhaust(self) -> Result[int]:
        """Get the exhaust fan speed for the standby preset."""
        return await self.client.get_register(self.regmap[vp.FAN_SPEED_AWAY_EXHAUST], self.slave_id)

    async def set_preset_standby_fan_speed_exhaust(self, value: int) -> bool:
        """Set the exhaust fan speed for the standby preset."""
        return await self.client.set_register(
            self.regmap[vp.FAN_SPEED_AWAY_EXHAUST], value, self.slave_id
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
