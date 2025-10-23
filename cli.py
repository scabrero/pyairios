#!/usr/bin/env python3

"""Airios RF bridge Command Line Interface."""

import argparse
import asyncio
import logging
import pprint
from typing import cast

from aiocmd import aiocmd

try:
    from pyairios.client import AsyncAiriosModbusRtuClient
except ModuleNotFoundError:
    import os
    import sys

    sys.path.append(f"{os.path.dirname(__file__)}/src")
    from pyairios.client import AsyncAiriosModbusRtuClient

from pyairios.client import (
    AiriosRtuTransport,
    AiriosTcpTransport,
    AsyncAiriosModbusClient,
    AsyncAiriosModbusTcpClient,
)
from pyairios.constants import (
    Baudrate,
    ModbusEvents,
    Parity,
    ProductId,
    ResetMode,
    SerialConfig,
    StopBits,
    VMDBypassMode,
    VMDRequestedVentilationSpeed,
    VMDVentilationMode,
    VMDVentilationSpeed,
)
from pyairios.data_model import AiriosDeviceData
from pyairios.device import AiriosDevice
from pyairios.exceptions import (
    AiriosConnectionException,
    AiriosInvalidArgumentException,
    AiriosIOException,
    AiriosNotImplemented,
)
from pyairios.models.brdg_02r13 import BRDG02R13
from pyairios.models.brdg_02r13 import DEFAULT_DEVICE_ID as BRDG02R13_DEFAULT_DEVICE_ID
from pyairios.models.factory import factory
from pyairios.models.vmd_02rps78 import VMD02RPS78
from pyairios.models.vmd_07rps13 import VMD07RPS13
from pyairios.models.vmn_05lm02 import VMN05LM02
from pyairios.properties import AiriosBridgeProperty as bp
from pyairios.properties import AiriosDeviceProperty as dp
from pyairios.properties import AiriosNodeProperty as np
from pyairios.properties import AiriosVMDProperty as vmdp
from pyairios.properties import AiriosVMNProperty as vmnp

LOGGER = logging.getLogger(__name__)


def _print_device_data(res: AiriosDeviceData):
    log = logging.getLogger()
    if log.isEnabledFor(logging.DEBUG):
        print("Raw data")
        print("--------")
        pprint.pprint(res)

    print("Device data")
    print("---------")
    print(f"    {'Product ID:': <25}{res[dp.PRODUCT_ID]}")
    print(f"    {'Product Name:': <25}{res[dp.PRODUCT_NAME]}")
    if dp.SOFTWARE_VERSION in res:
        print(f"    {'Software version:': <25}{res[dp.SOFTWARE_VERSION]}")
    if dp.SOFTWARE_BUILD_DATE in res:
        print(f"    {'Software build date:': <25}{res[dp.SOFTWARE_BUILD_DATE]}")
    print(f"    {'RF address:': <25}{res[dp.RF_ADDRESS]}")
    print(f"    {'RF comm status:': <25}{res[dp.RF_COMM_STATUS]}")
    print(f"    {'Battery status:': <25}{res[dp.BATTERY_STATUS]}")
    print(f"    {'Fault status:': <25}{res[dp.FAULT_STATUS]}")
    print("")


def _print_node_data(res: AiriosDeviceData):
    _print_device_data(res)
    print("Node data")
    print("---------")
    print(f"    {'Bound status:': <25}{res[np.BOUND_STATUS]}")
    print(f"    {'Value error status:': <25}{res[np.VALUE_ERROR_STATUS]}")
    print("")


class AiriosVMN05LM02CLI(aiocmd.PromptToolkitCmd):
    """The VMN05LM02 CLI interface."""

    vmn: VMN05LM02

    def __init__(self, vmn: AiriosDevice) -> None:
        super().__init__()
        self.prompt = f"[VMN-05LM02@{vmn.device_id}]>> "
        self.vmn = cast(VMN05LM02, vmn)

    async def do_received_product_id(self) -> None:
        """Print the received product ID from the device."""
        res = await self.vmn.node_received_product_id()
        print(f"0x{res.value:08X}")

    async def do_requested_ventilation_speed(self) -> None:
        """Print the latest requested ventilation speed by the device."""
        res = await self.vmn.requested_ventilation_speed()
        print(f"{res}")
        if res.status is not None:
            print(f"\t{res.status}")

    async def do_status(self) -> None:
        """Print the device status."""
        res = await self.vmn.fetch()

        _print_node_data(res)

        print("VMN-02LM11 data")
        print("----------------")
        if vmnp.REQUESTED_VENTILATION_SPEED in res:
            print(
                f"    {'Requested ventilation speed:': <40}{res[vmnp.REQUESTED_VENTILATION_SPEED]}"
            )

    async def do_properties(self, status: bool) -> None:
        """Print all device properties."""
        _status = status in (1, "y", "yes")
        res = await self.vmn.fetch(_status)
        pprint.pprint(res)


class AiriosVMD02RPS78CLI(aiocmd.PromptToolkitCmd):
    """The VMD02RPS78 CLI interface."""

    vmd: VMD02RPS78

    def __init__(self, vmd: AiriosDevice) -> None:
        super().__init__()
        self.prompt = f"[VMD-02RPS78@{vmd.device_id}]>> "
        self.vmd = cast(VMD02RPS78, vmd)

    async def do_capabilities(self) -> None:
        """Print the device RF capabilities."""
        res = await self.vmd.capabilities()
        print(f"{res.value} ({res.status})")

    async def do_status(self) -> None:  # pylint: disable=too-many-statements
        """Print the device status."""
        res = await self.vmd.fetch()

        _print_node_data(res)

        print("VMD-02RPS78 data")
        print("----------------")
        print(f"    {'Error code:': <25}{res[vmdp.ERROR_CODE]}")

        print(f"    {'Ventilation speed:': <25}{res[vmdp.CURRENT_VENTILATION_SPEED]}")
        print(
            (
                f"    {'Override remaining time:': <25}"
                f"{res[vmdp.VENTILATION_SPEED_OVERRIDE_REMAINING_TIME]}"
            )
        )

        print(
            f"    {'Supply fan speed:': <25}{res[vmdp.FAN_SPEED_SUPPLY]}% "
            f"({res[vmdp.FAN_RPM_SUPPLY]} RPM)"
        )
        print(
            f"    {'Exhaust fan speed:': <25}{res[vmdp.FAN_SPEED_EXHAUST]}% "
            f"({res[vmdp.FAN_RPM_EXHAUST]} RPM)"
        )

        print(f"    {'Inlet temperature:': <25}{res[vmdp.TEMPERATURE_INLET]}")
        print(f"    {'Supply temperature:': <25}{res[vmdp.TEMPERATURE_SUPPLY]}")
        print(f"    {'Exhaust temperature:': <25}{res[vmdp.TEMPERATURE_EXHAUST]}")
        print(f"    {'Outlet temperature:': <25}{res[vmdp.TEMPERATURE_OUTLET]}")

        print(f"    {'Filter dirty:': <25}{res[vmdp.FILTER_DIRTY]}")
        print(f"    {'Filter remaining:': <25}{res[vmdp.FILTER_REMAINING_PERCENT]} %")
        print(f"    {'Filter duration:': <25}{res[vmdp.FILTER_REMAINING_DAYS]} days")

        print(f"    {'Bypass position:': <25}{res[vmdp.BYPASS_POSITION]}")
        print(f"    {'Bypass status:': <25}{res[vmdp.BYPASS_STATUS]}")
        print(f"    {'Bypass mode:': <25}{res[vmdp.BYPASS_MODE]}")

        print(f"    {'Defrost:': <25}{res[vmdp.DEFROST]}")
        print(f"    {'Preheater:': <25}{res[vmdp.PREHEATER]}")
        print(f"    {'Postheater:': <25}{res[vmdp.POSTHEATER]}")
        print("")

        print(f"    {'Preset speeds':<25}{'Supply':<10}{'Exhaust':<10}")
        print(f"    {'-------------':<25}")
        print(
            f"    {'High':<25}{str(res[vmdp.FAN_SPEED_HIGH_SUPPLY]) + ' %':<10}"
            f"{str(res[vmdp.FAN_SPEED_HIGH_EXHAUST]) + ' %':<10}"
        )
        print(
            f"    {'Mid':<25}{str(res[vmdp.FAN_SPEED_MID_SUPPLY]) + ' %':<10}"
            f"{str(res[vmdp.FAN_SPEED_MID_EXHAUST]) + ' %':<10}"
        )
        print(
            f"    {'Low':<25}{str(res[vmdp.FAN_SPEED_LOW_SUPPLY]) + ' %':<10}"
            f"{str(res[vmdp.FAN_SPEED_LOW_EXHAUST]) + ' %':<10}"
        )
        print(
            f"    {'Away':<25}{str(res[vmdp.FAN_SPEED_AWAY_SUPPLY]) + ' %':<10}"
            f"{str(res[vmdp.FAN_SPEED_AWAY_EXHAUST]) + ' %':<10}"
        )
        print("")

        print("    Setpoints")
        print("    ---------")
        print(
            f"    {'Frost protection preheater setpoint:':<40}"
            f"{res[vmdp.FROST_PROTECTION_PREHEATER_SETPOINT]} ºC"
        )
        print(f"    {'Preheater setpoint:': <40}{res[vmdp.PREHEATER_SETPOINT]} ºC")
        print(
            (
                f"    {'Free ventilation setpoint:':<40}"
                f"{res[vmdp.FREE_VENTILATION_HEATING_SETPOINT]} ºC"
            )
        )
        print(
            f"    {'Free ventilation cooling offset:':<40}"
            f"{res[vmdp.FREE_VENTILATION_COOLING_OFFSET]} K"
        )

    async def do_error_code(self) -> None:
        """Print the current error code."""
        res = await self.vmd.error_code()
        print(f"{res}")

    async def do_ventilation_speed(self) -> None:
        """Print the current ventilation speed."""
        res = await self.vmd.ventilation_speed()
        if res.value in [
            VMDVentilationSpeed.OVERRIDE_LOW,
            VMDVentilationSpeed.OVERRIDE_MID,
            VMDVentilationSpeed.OVERRIDE_HIGH,
        ]:
            rem = await self.vmd.override_remaining_time()
            print(f"{res.value} ({rem.value} min. remaining)")
        else:
            print(f"{res}")
        if res.status is not None:
            print(f"{res.status}")

    async def do_set_ventilation_speed(self, preset: str) -> None:
        """Change the ventilation speed."""
        s = VMDRequestedVentilationSpeed.parse(preset)
        await self.vmd.set_ventilation_speed(s)

    async def do_set_ventilation_speed_override_time(self, preset: str, minutes: str) -> None:
        """Change the ventilation speed for a limited time."""
        s = VMDRequestedVentilationSpeed.parse(preset)
        await self.vmd.set_ventilation_speed_override_time(s, int(minutes))

    async def do_preset_away_fans_speeds(self):
        """Print the away preset fan speeds."""
        res = await self.vmd.preset_away_fans_speed()
        print(f"{'Supply fan speed:': <25}{res.supply_fan_speed}%")
        print(f"{'Exhaust fan speed:': <25}{res.exhaust_fan_speed}%")

    async def do_set_preset_away_fans_speeds(self, supply: int, exhaust: int):
        """Change the away preset fan speeds."""
        await self.vmd.set_preset_away_fans_speed(int(supply), int(exhaust))

    async def do_preset_low_fans_speeds(self):
        """Print the low preset fan speeds."""
        res = await self.vmd.preset_low_fans_speed()
        print(f"{'Supply fan speed:': <25}{res.supply_fan_speed}%")
        print(f"{'Exhaust fan speed:': <25}{res.exhaust_fan_speed}%")

    async def do_set_preset_low_fans_speeds(self, supply: int, exhaust: int):
        """Change the low preset fan speeds."""
        await self.vmd.set_preset_low_fans_speed(int(supply), int(exhaust))

    async def do_preset_mid_fans_speeds(self):
        """Print the mid preset fan speeds."""
        res = await self.vmd.preset_mid_fans_speed()
        print(f"{'Supply fan speed:': <25}{res.supply_fan_speed}%")
        print(f"{'Exhaust fan speed:': <25}{res.exhaust_fan_speed}%")

    async def do_set_preset_mid_fans_speeds(self, supply: int, exhaust: int):
        """Change the mid preset fan speeds."""
        await self.vmd.set_preset_mid_fans_speed(int(supply), int(exhaust))

    async def do_preset_high_fans_speeds(self):
        """Print the high preset fan speeds."""
        res = await self.vmd.preset_high_fans_speed()
        print(f"{'Supply fan speed:': <25}{res.supply_fan_speed}%")
        print(f"{'Exhaust fan speed:': <25}{res.exhaust_fan_speed}%")

    async def do_set_preset_high_fans_speeds(self, supply: int, exhaust: int):
        """Change the high preset fan speeds."""
        await self.vmd.set_preset_high_fans_speed(int(supply), int(exhaust))

    async def do_bypass_position(self):
        """Print the bypass position."""
        res = await self.vmd.bypass_position()
        print(f"{res}")

    async def do_bypass_status(self):
        """Print the bypass status."""
        res = await self.vmd.bypass_status()
        print(f"{res}")

    async def do_bypass_mode(self):
        """Print the bypass mode."""
        res = await self.vmd.bypass_mode()
        print(f"{res}")

    async def do_set_bypass_mode(self, mode: str):
        """Change the bypass mode."""
        v = VMDBypassMode.parse(mode)
        await self.vmd.set_bypass_mode(v)

    async def do_filter_duration(self):
        """Print the filter duration."""
        res = await self.vmd.filter_duration()
        print(f"{res}")

    async def do_filter_remaining(self):
        """Print the filter remaining percentage."""
        r1 = await self.vmd.filter_remaining()
        r2 = await self.vmd.filter_remaining_days()
        r3 = await self.vmd.filter_duration()
        print(f"{r1.value} % ({r2.value} of {r3.value} days)")

    async def do_filter_reset(self):
        """Reset the filter change timer."""
        await self.vmd.filter_reset()

    async def do_properties(self, status: bool) -> None:
        """Print all device properties."""
        _status = status in (1, "y", "yes")
        res = await self.vmd.fetch(_status)
        pprint.pprint(res)


class AiriosVMD07RPS13CLI(aiocmd.PromptToolkitCmd):
    """The VMD07RPS13 CLI interface."""

    vmd: VMD07RPS13

    def __init__(self, vmd: AiriosDevice) -> None:
        super().__init__()
        self.prompt = f"[VMD-07RPS13@{vmd.device_id}]>> "
        self.vmd = cast(VMD07RPS13, vmd)

    async def do_received_product_id(self) -> None:
        """Print the received product ID from the device."""
        res = await self.vmd.node_received_product_id()
        print(f"0x{res.value:08X}")

    async def do_capabilities(self) -> None:
        """Print the device RF capabilities."""
        res = await self.vmd.capabilities()
        if res is not None:
            print(f"{res.value} ({res.status})")
        else:
            print("N/A")

    async def do_error_code(self) -> None:
        """Print the current error code."""
        res = await self.vmd.error_code()
        print(f"{res}")

    async def do_vent_mode(self) -> None:
        """Print the current ventilation mode."""
        res = await self.vmd.ventilation_mode()
        print(f"{res}")
        if res.status is not None:
            print(f"{res.status}")

    async def do_rq_vent_mode(self) -> None:  # failed
        """Print the current requested ventilation mode."""
        res = await self.vmd.requested_ventilation_mode()
        print(f"{res}")

    async def do_rq_vent_sub_mode(self) -> None:  # works!
        """Print the current requested ventilation sub mode."""
        res = await self.vmd.requested_ventilation_sub_mode()
        print(f"{res}")

    async def do_rq_temp_vent_mode(self) -> None:
        """Print the requested temp. ventilation mode."""
        res = await self.vmd.requested_temp_ventilation_mode()
        print(f"{res}")

    async def do_rq_temp_vent_mode_set(self, preset: int) -> None:
        """Change the requested ventilation mode. 0=Off, 1=Pause, 2=On, 3=Man1, 5=Man3, 8=Service"""
        # s = VMDRequestedVentilationSpeed.parse(preset)
        res = await self.vmd.set_temp_ventilation_mode(preset)  # (s) lookup?
        print(f"{res}")

    async def do_rq_temp_vent_sub_mode(self) -> None:
        """Print the requested temp. ventilation sub mode."""
        res = await self.vmd.requested_temp_ventilation_sub_mode()
        print(f"{res}")

    async def do_rq_vent_mode_set(self, preset: int) -> None:
        """Change the requested ventilation mode. 0=Off, 1=Pause, 2=On, 3=Man1, 5=Man3, 8=Service"""
        s = VMDVentilationMode(preset)
        res = await self.vmd.set_ventilation_mode(s)
        print(f"{res}")

    async def do_rq_vent_sub_mode_set(self, preset: int) -> None:
        """Change the requested ventilation sub mode. 0=Off, 201 - 205"""
        # s = VMDRequestedVentilationSpeed.parse(preset)
        res = await self.vmd.set_ventilation_sub_mode(preset)  # (s) lookup?
        print(f"{res}")

    async def do_temp_vent_sub_mode(self) -> None:
        """Print the current temp. ventilation sub mode"""
        # s = VMDRequestedVentilationSpeed.parse(preset)
        res = await self.vmd.temp_ventilation_sub_mode()  # (s) lookup?
        print(f"{res}")

    async def do_rq_temp_vent_sub_mode_set(self, preset: int) -> None:
        """Change the requested ventilation sub mode. 0=Off, 201 - 205"""
        # s = VMDRequestedVentilationSpeed.parse(preset)
        res = await self.vmd.set_temp_ventilation_sub_mode(preset)  # (s) lookup?
        print(f"{res}")

    async def do_ventilation_speed(self) -> None:
        """Print the current ventilation speed."""
        res = await self.vmd.ventilation_speed()
        print(f"{res}")
        if res.status is not None:
            print(f"{res.status}")

    async def do_indoor_hum(self):
        """Print the indoor humidity level in %."""
        res = await self.vmd.indoor_humidity()
        print(f"{res} %")

    async def do_outdoor_hum(self):
        """Print the outdoor humidity level in %."""
        res = await self.vmd.outdoor_humidity()
        print(f"{res} %")

    async def do_bypass_pos(self):
        """Print the bypass position."""
        res = await self.vmd.bypass_position()
        print(f"{res} {'Open' if res == 1 else 'Closed'}")

    async def do_base_vent_enabled(self):
        """Print the base ventilation enabled: On/Off = 1/0."""
        res = await self.vmd.basic_ventilation_enable()
        print(f"{res} {'On' if res.value == 1 else 'Off'}")

    async def do_base_vent_enabled_set(self, state: bool) -> None:
        """Set the base ventilation enabled: on/off = 1/0."""
        if await self.vmd.set_basic_ventilation_enable(state):
            await self.do_base_vent_enabled()
        else:
            print("Error setting base_vent_enabled")

    async def do_base_vent_level(self):
        """Print the base ventilation level."""
        res = await self.vmd.basic_ventilation_level()
        print(f"base_vent_level: {res}")

    async def do_base_vent_level_set(self, lvl: int) -> None:
        """Set the base ventilation level."""
        if await self.vmd.set_basic_ventilation_level(lvl):
            res = await self.vmd.basic_ventilation_level()
            print(f"base_vent_level set to: {res.value}")
        else:
            print("Error setting base_vent_level")

    async def do_filter_remaining(self):
        """Print the filter remaining."""
        r1 = await self.vmd.filter_remaining_percent()
        r2 = await self.vmd.filter_remaining_days()
        print(f"{r1.value} % ({r2.value} days)")

    async def do_co2_setpoint(self):
        """Print the CO2 setpoint in ppm."""
        res = await self.vmd.co2_setpoint()
        print(f"{res.value} ppm")

    async def do_co2_setpoint_set(self, setp: int) -> None:
        """Change the CO2 setpoint in ppm. Factory default = 1000."""
        if await self.vmd.set_co2_setpoint(setp):
            res = await self.vmd.co2_setpoint()
            print(f"CO2 setpoint set to: {res.value} ppm")
        else:
            print("Error setting CO2 setpoint")

    # actions

    async def do_filter_reset(self):
        """Reset the filter change timer."""
        await self.vmd.filter_reset()

    async def do_status(self) -> None:  # pylint: disable=too-many-statements
        """Print the complete device status."""
        # Not interested in values status here, use multiple register
        # fetching to reduce modbus transactions.
        res = await self.vmd.fetch(status=False)

        _print_node_data(res)

        print("VMD-07RPS13 data")
        print("----------------")
        print(f"    {'Product Variant:': <25}{res[vmdp.PRODUCT_VARIANT]}")
        print(f"    {'Error code:': <25}{res[vmdp.ERROR_CODE]}")
        print("")
        print(f"    {'Ventilation mode:': <25}{res[vmdp.VENTILATION_MODE]}")
        print(f"    {'Ventilation sub mode:': <25}{res[vmdp.VENTILATION_SUB_MODE]}")
        print(f"    {'Temp. Ventil. mode:': <25}{res[vmdp.TEMP_VENTILATION_MODE]}")
        print(f"    {'Temp. Ventil. sub mode:': <25}{res[vmdp.TEMP_VENTILATION_SUB_MODE]}")
        #
        print(
            f"    {'Supply fan speed:': <25}{res[vmdp.FAN_SPEED_SUPPLY]}% "
            # f"({res['supply_fan_rpm']} RPM)"
        )
        print(
            f"    {'Exhaust fan speed:': <25}{res[vmdp.FAN_SPEED_EXHAUST]}% "
            # f"({res['exhaust_fan_rpm']} RPM)"
        )

        print(f"    {'Outlet temperature:': <25}{res[vmdp.TEMPERATURE_OUTLET]}")
        print(f"    {'Indoor temperature:': <25}{res[vmdp.TEMPERATURE_EXHAUST]}")
        print(f"    {'Supply temperature:': <25}{res[vmdp.TEMPERATURE_SUPPLY]}")

        print(f"    {'CO2 level:':<40}{res[vmdp.CO2_LEVEL]} ppm")

        print(f"    {'Filter dirty:': <25}{res[vmdp.FILTER_DIRTY]}")
        print(f"    {'Filter remaining days:': <25}{res[vmdp.FILTER_REMAINING_DAYS]} days")
        print(f"    {'Filter remaining perc.:': <25}{res[vmdp.FILTER_REMAINING_PERCENT]}%")

        print(
            f"    {'Bypass position:': <25}{'Open ' if res == 1 else 'Closed '}{
                res[vmdp.BYPASS_POSITION]
            }"
        )
        print(f"    {'Base ventil. enabled:': <25}{res[vmdp.BASIC_VENTILATION_ENABLE]}")
        print("")

        print("    Setpoints")
        print("    ---------")
        print(f"    {'CO2 control setpoint:':<40}{res[vmdp.CO2_CONTROL_SETPOINT]} ppm")

    async def do_properties(self, status: bool) -> None:
        """Print all device properties."""
        _status = status in (1, "y", "yes")
        res = await self.vmd.fetch(_status)
        pprint.pprint(res)


class AiriosBridgeCLI(aiocmd.PromptToolkitCmd):
    """The bridge CLI interface."""

    def __init__(self, bridge: BRDG02R13) -> None:
        super().__init__()
        self.prompt = f"[BRDG-02R13@{bridge.device_id}]>> "
        self.bridge = bridge

    async def do_nodes(self) -> None:
        """Print the list of bound nodes."""
        res = await self.bridge.nodes()
        for n in res:
            print(f"{n}")

    async def do_node(self, device_id: str) -> None:
        """Manage a bound node."""
        nodes = await self.bridge.nodes()
        node_info = None
        for n in nodes:
            if int(device_id) == int(n.device_id):
                node_info = n
                break

        if node_info is None:
            raise AiriosIOException(f"Node with address {device_id} not bound")

        dev = await factory.get_device_by_product_id(
            node_info.product_id,
            node_info.device_id,
            self.bridge.client,
        )

        if node_info.product_id == ProductId.VMD_02RPS78:
            await AiriosVMD02RPS78CLI(dev).run()
        elif node_info.product_id == ProductId.VMN_05LM02:
            await AiriosVMN05LM02CLI(dev).run()
        else:
            raise AiriosNotImplemented(f"{node_info.product_id} not implemented")

    async def do_rf_sent_messages(self) -> None:
        """Print the RF sent messages."""
        res = await self.bridge.rf_sent_messages()
        print(f"RF Sent Messages: {res}")

    async def do_modbus_events(self) -> None:
        """Print the modbus events mode."""
        res = await self.bridge.modbus_events()
        print(f"Modbus events: {res}")

    async def do_set_modbus_events(self, mode: str) -> None:
        """Set the Modbus events mode:
        'none'   - No Modbus events are generated
        'bridge' - Modbus function 'bridge event' is sent when a value is changed
        'node'   - Modbus function 'node event' is sent when a value is changed
        'data'   - Modbus function 'data event' is sent when a value is changed
        """
        value = ModbusEvents.parse(mode)
        await self.bridge.set_modbus_events(value)

    async def do_serial_config(self) -> None:
        """Print the serial configuration."""
        res = await self.bridge.serial_config()
        print(f"Serial Config: {res}")

    async def do_set_serial_config(self, baudrate: int, parity: str, stop_bits: int) -> None:
        """Set the serial configuration.

        The bridge must be reset to make new settings effective."""
        b = Baudrate.parse(baudrate)
        p = Parity.parse(parity)
        s = StopBits.parse(stop_bits)
        config = SerialConfig(b, p, s)
        if await self.bridge.set_serial_config(config):
            print("Reset the bridge with `reset` command to make new settings effective.")

    async def do_uptime(self) -> None:
        """Print the device uptime."""
        res = await self.bridge.power_on_time()
        print(f"Uptime: {res}")

    async def do_reset(self, factory_reset: bool = False) -> None:
        """Reset the device."""
        mode = ResetMode.SOFT_RESET
        if factory_reset:
            mode = ResetMode.FACTORY_RESET
        await self.bridge.reset(mode)

    async def do_unbind(self, device_id) -> None:
        """Remove a bound node."""
        device_id = int(device_id)
        await self.bridge.unbind(device_id)

    async def do_bind_status(self) -> None:
        """Print bind status."""
        res = await self.bridge.bind_status()
        print(f"Bind status: {res}")

    async def do_bind_controller(
        self, device_id, product_id, product_serial: str | None = None
    ) -> None:
        """Bind a new controller."""
        device_id = int(device_id)
        pid = ProductId(int(product_id))
        psn = None
        if product_serial is not None:
            psn = int(product_serial)
        await self.bridge.bind_controller(device_id, pid, psn)

    async def do_bind_accessory(self, ctrl_device_id, device_id, product_id) -> None:
        """Bind a new accessory."""
        ctrl_device_id = int(ctrl_device_id)
        device_id = int(device_id)
        pid = ProductId(int(product_id))
        await self.bridge.bind_accessory(ctrl_device_id, device_id, pid)

    async def do_software_build_date(self) -> None:
        """Print the software build date."""
        date = await self.bridge.device_software_build_date()
        print(date)

    async def do_utc_time(self) -> None:
        """Print the UTC time."""
        time = await self.bridge.utc_time()
        print(time)

    async def do_node_oem_number(self) -> None:
        """Print the node OEM number."""
        number = await self.bridge.device_oem_number()
        print(number)

    async def do_oem_code(self) -> None:
        """Print the OEM code."""
        number = await self.bridge.oem_code()
        print(number)

    async def do_set_oem_code(self, number: int) -> None:
        """Set the OEM code."""
        await self.bridge.set_oem_code(int(number))

    async def do_status(self) -> None:
        """Print the device status."""
        res = await self.bridge.fetch()

        _print_device_data(res)

        print("BRDG-02R13 data")
        print("----------------")
        print(f"    {'Customer product ID:': <40}0x{res[bp.CUSTOMER_PRODUCT_ID].value:08X}")
        print(f"    {'RF sent messages last hour': <40}{res[bp.MESSAGES_SEND_LAST_HOUR]}")
        print(f"    {'RF sent messages current hour:': <40}{res[bp.MESSAGES_SEND_CURRENT_HOUR]}")
        print(f"    {'RF load last hour:': <40}{res[bp.RF_LOAD_LAST_HOUR]}")
        print(f"    {'RF load current hour:': <40}{res[bp.RF_LOAD_CURRENT_HOUR]}")
        print(f"    {'Uptime:': <40}{res[bp.UPTIME]}")

    async def do_properties(self, status: bool) -> None:
        """Print all device properties."""
        _status = status in (1, "y", "yes")
        res = await self.bridge.fetch(_status)
        pprint.pprint(res)


class AiriosClientCLI(aiocmd.PromptToolkitCmd):  # pylint: disable=too-few-public-methods
    """CLI client interface."""

    prompt = "[client]>> "

    def __init__(self, client: AsyncAiriosModbusClient) -> None:
        super().__init__()
        self.client = client

    async def do_bridge(self, address: str | None = None) -> None:
        """Manage the bridge."""
        if address is None:
            _address = (
                BRDG02R13_DEFAULT_DEVICE_ID
                if isinstance(self.client, AsyncAiriosModbusRtuClient)
                else 1
            )
        else:
            _address = int(address)
        bridge = await factory.get_device_by_product_id(ProductId.BRDG_02R13, _address, self.client)
        await AiriosBridgeCLI(bridge).run()


class AiriosRootCLI(aiocmd.PromptToolkitCmd):
    """CLI root context."""

    prompt = ">> "
    intro = 'Welcome to AiriosCLI. Type "help" for available commands.'
    client: AsyncAiriosModbusClient | None = None

    async def do_connect_rtu(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        port: str = "/dev/ttyACM0",
        baudrate: str = "19200",
        data_bits: str = "8",
        parity: str = "E",
        stop_bits: str = "1",
    ) -> None:
        """Connect to serial bridge."""
        if self.client:
            raise AiriosConnectionException("Already connected")
        transport = AiriosRtuTransport(
            device=port,
            baudrate=int(baudrate),
            data_bits=int(data_bits),
            parity=parity,
            stop_bits=int(stop_bits),
        )
        self.client = AsyncAiriosModbusRtuClient(transport)
        await AiriosClientCLI(self.client).run()

    async def do_connect_tcp(self, host: str = "192.168.1.254", port: int = 502):
        """Connect to Ethernet bridge."""
        if self.client:
            raise AiriosConnectionException("Already connected")
        transport = AiriosTcpTransport(host, port=port)
        self.client = AsyncAiriosModbusTcpClient(transport)
        await AiriosClientCLI(self.client).run()

    async def do_disconnect(self) -> None:
        """Disconnect from bridge."""
        if self.client:
            self.client = None

    async def do_set_log_level(self, level: str) -> None:
        "Set the log level: critical, fatal, error, warning, info or debug."
        logging.basicConfig()
        log = logging.getLogger()
        if level.casefold() == "critical".casefold():
            log.setLevel(logging.CRITICAL)
        elif level.casefold() == "fatal".casefold():
            log.setLevel(logging.FATAL)
        elif level.casefold() == "error".casefold():
            log.setLevel(logging.ERROR)
        elif level.casefold() == "warning".casefold():
            log.setLevel(logging.WARNING)
        elif level.casefold() == "info".casefold():
            log.setLevel(logging.INFO)
        elif level.casefold() == "debug".casefold():
            log.setLevel(logging.DEBUG)
        else:
            raise AiriosInvalidArgumentException("Invalid log level")


async def main() -> None:
    """Run the async CLI."""
    await AiriosRootCLI().run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Airios RF bridge Command Line Interface",
        epilog=(
            "Thanks to Siber for providing the documentation and support to develop this library."
        ),
    )
    args = parser.parse_args()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
