#!/usr/bin/env python3

"""Airios RF bridge Command Line Interface."""

import argparse
import asyncio

from aiocmd import aiocmd

try:
    from pyairios.client import AsyncAiriosModbusRtuClient
except ModuleNotFoundError:
    import os
    import sys

    sys.path.append(f"{os.path.dirname(__file__)}/src")
    from pyairios.client import AsyncAiriosModbusRtuClient

from pyairios.brdg_02r13 import BRDG02R13, DEFAULT_SLAVE_ID as BRDG02R13_DEFAULT_SLAVE_ID
from pyairios.constants import (
    ProductId,
    ResetMode,
    VMDBypassMode,
    VMDRequestedVentilationSpeed,
    VMDVentilationSpeed,
)
from pyairios.vmd_02rps78 import VMD02RPS78
from pyairios.vmn_05lm02 import VMN05LM02
from pyairios.exceptions import AiriosConnectionException, AiriosIOException, AiriosNotImplemented
from pyairios.client import (
    AiriosRtuTransport,
    AiriosTcpTransport,
    AsyncAiriosModbusClient,
    AsyncAiriosModbusTcpClient,
)


class AiriosVMN05LM02CLI(aiocmd.PromptToolkitCmd):
    """The VMN05LM02 CLI interface."""

    def __init__(self, vmn: VMN05LM02) -> None:
        super().__init__()
        self.prompt = f"[VMN-05LM02@{vmn.slave_id}]>> "
        self.vmn = vmn

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
        res = await self.vmn.fetch_vmn_data()
        print("Node data")
        print("---------")
        print(f"    {'Product ID:': <25}{res['product_id']}")
        print(f"    {'Product Name:': <25}{res['product_name']}")
        print(f"    {'Software version:': <25}{res['sw_version']}")
        print(f"    {'RF address:': <25}{res['rf_address']}")
        print("")

        print("Device data")
        print("---------")
        print(f"    {'RF comm status:': <25}{res['rf_comm_status']}")
        print(f"    {'Battery status:': <25}{res['battery_status']}")
        print(f"    {'Fault status:': <25}{res['fault_status']}")
        print(f"    {'Bound status:': <25}{res['bound_status']}")
        print(f"    {'Value error status:': <25}{res['value_error_status']}")
        print("")

        print("VMN-02LM11 data")
        print("----------------")
        print(f"    {'Requested ventilation speed:': <40}{res['requested_ventilation_speed']}")


class AiriosVMD02RPS78CLI(aiocmd.PromptToolkitCmd):
    """The VMD02RPS78 CLI interface."""

    def __init__(self, vmd: VMD02RPS78) -> None:
        super().__init__()
        self.prompt = f"[VMD-02RPS78@{vmd.slave_id}]>> "
        self.vmd = vmd

    async def do_capabilities(self) -> None:
        """Print the device RF capabilities."""
        res = await self.vmd.capabilities()
        print(f"{res.value} ({res.status})")

    async def do_status(self) -> None:  # pylint: disable=too-many-statements
        """Print the device status."""
        res = await self.vmd.fetch_vmd_data()
        print("Node data")
        print("---------")
        print(f"    {'Product ID:': <25}{res['product_id']}")
        print(f"    {'Product Name:': <25}{res['product_name']}")
        print(f"    {'Software version:': <25}{res['sw_version']}")
        print(f"    {'RF address:': <25}{res['rf_address']}")
        print("")

        print("Device data")
        print("---------")
        print(f"    {'RF comm status:': <25}{res['rf_comm_status']}")
        print(f"    {'Battery status:': <25}{res['battery_status']}")
        print(f"    {'Fault status:': <25}{res['fault_status']}")
        print(f"    {'Bound status:': <25}{res['bound_status']}")
        print(f"    {'Value error status:': <25}{res['value_error_status']}")
        print("")

        print("VMD-02RPS78 data")
        print("----------------")
        print(f"    {'Error code:': <25}{res['error_code']}")

        print(f"    {'Ventilation speed:': <25}{res['ventilation_speed']}")
        print(f"    {'Override remaining time:': <25}{res['override_remaining_time']}")

        print(
            f"    {'Supply fan speed:': <25}{res['supply_fan_speed']}% "
            f"({res['supply_fan_rpm']} RPM)"
        )
        print(
            f"    {'Exhaust fan speed:': <25}{res['exhaust_fan_speed']}% "
            f"({res['exhaust_fan_rpm']} RPM)"
        )

        print(f"    {'Indoor temperature:': <25}{res['indoor_air_temperature']}")
        print(f"    {'Outdoor temperature:': <25}{res['outdoor_air_temperature']}")
        print(f"    {'Exhaust temperature:': <25}{res['exhaust_air_temperature']}")
        print(f"    {'Supply temperature:': <25}{res['supply_air_temperature']}")

        print(f"    {'Filter dirty:': <25}{res['filter_dirty']}")
        print(f"    {'Filter remaining:': <25}{res['filter_remaining_percent']} %")
        print(f"    {'Filter duration:': <25}{res['filter_duration_days']} days")

        print(f"    {'Bypass position:': <25}{res['bypass_position']}")
        print(f"    {'Bypass status:': <25}{res['bypass_status']}")
        print(f"    {'Bypass mode:': <25}{res['bypass_mode']}")

        print(f"    {'Defrost:': <25}{res['defrost']}")
        print(f"    {'Preheater:': <25}{res['preheater']}")
        print(f"    {'Postheater:': <25}{res['postheater']}")
        print("")

        print(f"    {'Preset speeds':<25}{'Supply':<10}{'Exhaust':<10}")
        print(f"    {'-------------':<25}")
        print(
            f"    {'High':<25}{str(res['preset_high_fan_speed_supply']) + ' %':<10}"
            f"{str(res['preset_high_fan_speed_exhaust']) + ' %':<10}"
        )
        print(
            f"    {'Mid':<25}{str(res['preset_medium_fan_speed_supply']) + ' %':<10}"
            f"{str(res['preset_medium_fan_speed_exhaust']) + ' %':<10}"
        )
        print(
            f"    {'Low':<25}{str(res['preset_low_fan_speed_supply']) + ' %':<10}"
            f"{str(res['preset_low_fan_speed_exhaust']) + ' %':<10}"
        )
        print(
            f"    {'Standby':<25}{str(res['preset_standby_fan_speed_supply']) + ' %':<10}"
            f"{str(res['preset_standby_fan_speed_exhaust']) + ' %':<10}"
        )
        print("")

        print("    Setpoints")
        print("    ---------")
        print(
            f"    {'Frost protection preheater setpoint:':<40}"
            f"{res['frost_protection_preheater_setpoint']} ºC"
        )
        print(f"    {'Preheater setpoint:': <40}{res['preheater_setpoint']} ºC")
        print(f"    {'Free ventilation setpoint:':<40}{res['free_ventilation_setpoint']} ºC")
        print(
            f"    {'Free ventilation cooling offset:':<40}"
            f"{res['free_ventilation_cooling_offset']} K"
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


class AiriosBridgeCLI(aiocmd.PromptToolkitCmd):
    """The bridge CLI interface."""

    def __init__(self, bridge: BRDG02R13) -> None:
        super().__init__()
        self.prompt = f"[BRDG-02R13@{bridge.slave_id}]>> "
        self.bridge = bridge

    async def do_nodes(self) -> None:
        """Print the list of bound nodes."""
        res = await self.bridge.nodes()
        for n in res:
            print(f"{n}")

    async def do_node(self, slave_id: str) -> None:
        """Manage a bound node."""
        nodes = await self.bridge.nodes()
        node_info = None
        for n in nodes:
            if int(slave_id) == int(n.slave_id):
                node_info = n
                break

        if node_info is None:
            raise AiriosIOException(f"Node with address {slave_id} not bound")

        if node_info.product_id == ProductId.VMD_02RPS78:
            vmd = VMD02RPS78(node_info.slave_id, self.bridge.client)
            await AiriosVMD02RPS78CLI(vmd).run()
            return

        if node_info.product_id == ProductId.VMN_05LM02:
            vmn = VMN05LM02(node_info.slave_id, self.bridge.client)
            await AiriosVMN05LM02CLI(vmn).run()
            return

        raise AiriosNotImplemented(f"{node_info.product_id} not implemented")

    async def do_rf_sent_messages(self) -> None:
        """Print the RF sent messages."""
        res = await self.bridge.rf_sent_messages()
        print(f"RF Sent Messages: {res}")

    async def do_modbus_events(self) -> None:
        """Print the modbus events mode."""
        res = await self.bridge.modbus_events()
        print(f"Modbus events: {res}")

    async def do_serial_config(self) -> None:
        """Print the serial configuration."""
        res = await self.bridge.serial_config()
        print(f"Serial Config: {res}")

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

    async def do_unbind(self, slave_id) -> None:
        """Remove a bound node."""
        slave_id = int(slave_id)
        await self.bridge.unbind(slave_id)

    async def do_bind_status(self) -> None:
        """Print bind status."""
        res = await self.bridge.bind_status()
        print(f"Bind status: {res}")

    async def do_bind_controller(
        self, slave_id, product_id, product_serial: str | None = None
    ) -> None:
        """Bind a new controller."""
        slave_id = int(slave_id)
        pid = ProductId(int(product_id))
        psn = None
        if product_serial is not None:
            psn = int(product_serial)
        await self.bridge.bind_controller(slave_id, pid, psn)

    async def do_bind_accessory(self, ctrl_slave_id, slave_id, product_id) -> None:
        """Bind a new accessory."""
        ctrl_slave_id = int(ctrl_slave_id)
        slave_id = int(slave_id)
        pid = ProductId(int(product_id))
        await self.bridge.bind_accessory(ctrl_slave_id, slave_id, pid)

    async def do_software_build_date(self) -> None:
        """Print the software build date."""
        date = await self.bridge.node_software_build_date()
        print(date)

    async def do_utc_time(self) -> None:
        """Print the UTC time."""
        time = await self.bridge.utc_time()
        print(time)

    async def do_status(self) -> None:
        """Print the device status."""
        res = await self.bridge.fetch_bridge()
        print("Node data")
        print("---------")
        print(f"    {'Product ID:': <25}{res['product_id']}")
        print(f"    {'Product Name:': <25}{res['product_name']}")
        print(f"    {'Software version:': <25}{res['sw_version']}")
        print(f"    {'RF address:': <25}{res['rf_address']}")
        print("")

        print("Device data")
        print("---------")
        print(f"    {'RF comm status:': <25}{res['rf_comm_status']}")
        print(f"    {'Battery status:': <25}{res['battery_status']}")
        print(f"    {'Fault status:': <25}{res['fault_status']}")
        print("")

        print("BRDG-02R13 data")
        print("----------------")
        print(f"    {'RF sent messages last hour': <40}{res['rf_sent_messages_last_hour']}")
        print(f"    {'RF sent messages current hour:': <40}{res['rf_sent_messages_current_hour']}")
        print(f"    {'RF load last hour:': <40}{res['rf_load_last_hour']}")
        print(f"    {'RF load current hour:': <40}{res['rf_load_current_hour']}")
        print(f"    {'Uptime:': <40}{res['power_on_time']}")


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
                BRDG02R13_DEFAULT_SLAVE_ID
                if isinstance(self.client, AsyncAiriosModbusRtuClient)
                else 1
            )
        else:
            _address = int(address)
        bridge = BRDG02R13(_address, self.client)
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


async def main() -> None:
    """Run the async CLI."""
    await AiriosRootCLI().run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Airios RF bridge Command Line Interface",
        epilog=(
            "Thanks to Siber for providing the documentation and suppport to develop this library."
        ),
    )
    args = parser.parse_args()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
