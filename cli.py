#!/usr/bin/env python3

"""Airios RF bridge Command Line Interface."""

import argparse
import asyncio
import glob
import importlib.util
import logging
import os
import re
from types import ModuleType

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
    StopBits,
    VMDBypassMode,
    # VMDBypassPosition,
    VMDRequestedVentilationSpeed,
    # VMDVentilationMode,
    VMDVentilationSpeed,
)
from pyairios.exceptions import (
    AiriosConnectionException,
    AiriosInvalidArgumentException,
    AiriosIOException,
    AiriosNotImplemented,
)
from pyairios.models.brdg_02r13 import (
    BRDG02R13,
    SerialConfig,
)
from pyairios.models.brdg_02r13 import (
    DEFAULT_SLAVE_ID as BRDG02R13_DEFAULT_SLAVE_ID,
)

LOGGER = logging.getLogger(__name__)

# analyse and import all VMx.py files from the models/ folder
modules_list = glob.glob(os.path.join(os.path.dirname(__file__), "src/pyairios/models/*.py"))
# A major benefit of the glob library is that it includes the path to the file in each item

# all (usable) models found are stored in 3 dicts:
prids: dict[str, str] = {}
# a dict with product_id's by class name (replaces ProductId enum in const.py)
modules: dict[str, ModuleType] = {}
# a dict with imported modules by class name
descriptions: dict[str, str] = {}
# a dict with label description model, for use in UI

for file_path in modules_list:
    file_name = str(os.path.basename(file_path))
    if (
        file_name == "__init__.py" or file_name == "brdg_02r13.py" or file_name.endswith("_base.py")
    ):  # skip BRDG and the base model definitions
        continue
    module_name = file_name.removesuffix(".py")
    model_key: str = str(re.sub(r"_", "-", module_name).upper())
    assert model_key is not None

    # using importlib, create a spec for each module:
    module_spec = importlib.util.spec_from_file_location(module_name, file_path)
    # store the spec in a dict by class name:
    mod = importlib.util.module_from_spec(module_spec)
    # load the module from the spec:
    module_spec.loader.exec_module(mod)
    # store the imported module in dict:
    modules[model_key] = mod
    # now we can use the module as if it were imported normally

    # check loading by fetching the product_id (the int te check binding against)
    prids[model_key] = modules[model_key].product_id()
    descriptions[model_key] = modules[model_key].product_description()

print(f"Supported models by key: {descriptions}")
# print(f"Loaded modules: {modules}")
print(f"Loaded product_id's: {prids}")
# all loaded up


class AiriosVMN05LM02CLI(aiocmd.PromptToolkitCmd):
    """The VMN_ modules common CLI interface."""

    def __init__(self, vmn) -> None:  # TODO subclass aiocmd_type
        """
        :param vmn: contains all details of this model
        """
        super().__init__()
        self.vmn = vmn
        self.class_pointer = str(vmn)
        self.prompt = f"[{str(vmn)}]>> "

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
        """Print the complete device status."""
        await self.vmn.print_data()


class AiriosVMD02RPS78CLI(aiocmd.PromptToolkitCmd):
    """The VMD02RPS78 CLI interface."""

    def __init__(self, vmd) -> None:
        """
        :param vmd: contains all details of this model
        """
        super().__init__()
        self.vmd = vmd
        self.class_pointer = str(vmd)
        self.prompt = f"[{str(vmd)}]>> "

    async def do_received_product_id(self) -> None:
        """Print the received product ID from the device."""
        res = await self.vmd.node_received_product_id()
        print(f"0x{res.value:08X}")

    async def do_capabilities(self) -> None:
        """Print the device RF capabilities."""
        res = await self.vmd.capabilities()
        print(f"{res.value} ({res.status})")

    async def do_status(self) -> None:  # pylint: disable=too-many-statements
        """Print the complete device status."""
        await self.vmd.print_data()

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


class AiriosVMD07RPS13CLI(aiocmd.PromptToolkitCmd):
    """The VMD07RPS13 ClimaRad Ventura V1 CLI interface."""

    def __init__(self, vmd) -> None:
        """
        :param vmd: contains all details of this model
        """
        super().__init__()
        self.vmd = vmd
        self.class_pointer = str(vmd)
        self.prompt = f"[{str(vmd)}]>> "

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

    async def do_status(self) -> None:  # pylint: disable=too-many-statements
        """Print the complete device status."""
        await self.vmd.print_data()

    async def do_error_code(self) -> None:
        """Print the current error code."""
        res = await self.vmd.error_code()
        print(f"{res}")

    async def do_vent_mode(self) -> None:
        """Print the current ventilation mode."""
        res = await self.vmd.vent_mode()
        print(f"{res}")
        if res.status is not None:
            print(f"{res.status}")

    async def do_rq_vent_mode(self) -> None:  # failed
        """Print the current requested ventilation mode."""
        res = await self.vmd.rq_vent_mode()
        print(f"{res}")

    async def do_rq_vent_sub_mode(self) -> None:  # works!
        """Print the current requested ventilation sub mode."""
        res = await self.vmd.rq_vent_sub_mode()
        print(f"{res}")

    async def do_rq_temp_vent_mode(self) -> None:
        """Print the requested temp. ventilation mode."""
        res = await self.vmd.rq_temp_vent_mode()
        print(f"{res}")

    async def do_rq_temp_vent_mode_set(self, preset: int) -> None:
        """Change the requested ventilation mode. 0=Off, 1=Pause, 2=On, 3=Man1, 5=Man3, 8=Service"""
        # s = VMDRequestedVentilationSpeed.parse(preset)
        res = await self.vmd.set_rq_temp_vent_mode(preset)  # (s) lookup?
        print(f"{res}")

    async def do_rq_temp_vent_sub_mode(self) -> None:
        """Print the requested temp. ventilation sub mode."""
        res = await self.vmd.rq_temp_vent_sub_mode()
        print(f"{res}")

    async def do_rq_vent_mode_set(self, preset: int) -> None:
        """Change the requested ventilation mode. 0=Off, 1=Pause, 2=On, 3=Man1, 5=Man3, 8=Service"""
        # s = VMDRequestedVentilationSpeed.parse(preset)
        res = await self.vmd.set_rq_vent_mode(preset)  # (s) lookup?
        print(f"{res}")

    async def do_rq_vent_sub_mode_set(self, preset: int) -> None:
        """Change the requested ventilation sub mode. 0=Off, 201 - 205"""
        # s = VMDRequestedVentilationSpeed.parse(preset)
        res = await self.vmd.set_rq_vent_sub_mode(preset)  # (s) lookup?
        print(f"{res}")

    async def do_temp_vent_sub_mode(self) -> None:
        """Print the current temp. ventilation sub mode"""
        # s = VMDRequestedVentilationSpeed.parse(preset)
        res = await self.vmd.temp_vent_sub_mode()  # (s) lookup?
        print(f"{res}")

    async def do_rq_temp_vent_sub_mode_set(self, preset: int) -> None:
        """Change the requested ventilation sub mode. 0=Off, 201 - 205"""
        # s = VMDRequestedVentilationSpeed.parse(preset)
        res = await self.vmd.set_rq_temp_vent_sub_mode(preset)  # (s) lookup?
        print(f"{res}")

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
        res = await self.vmd.basic_vent_enable()
        print(f"{res} {'On' if res.value == 1 else 'Off'}")

    async def do_base_vent_enabled_set(self, state: bool) -> None:
        """Set the base ventilation enabled: on/off = 1/0."""
        if await self.vmd.set_basic_vent_enable(state):
            await self.do_basic_vent_enable()
        else:
            print(f"Error setting basic_vent_enabled")

    async def do_base_vent_level(self):
        """Print the base ventilation level."""
        res = await self.vmd.basic_vent_level()
        print(f"basic_vent_level: {res}")

    async def do_base_vent_level_set(self, lvl: int) -> None:
        """Set the base ventilation level."""
        if await self.vmd.set_basic_vent_level(lvl):
            res = await self.vmd.basic_vent_level()
            print(f"basic_vent_level set to: {res.value}")
        else:
            print(f"Error setting basic_vent_level")

    async def do_filter_remaining(self):
        """Print the filter remaining days."""
        res = await self.vmd.filter_remaining_days()
        print(f"{res.value} days")

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
            print(f"Error setting CO2 setpoint")

    # actions

    async def do_filter_reset(self):
        """Reset the filter change timer."""
        await self.vmd.filter_reset()


class AiriosBridgeCLI(aiocmd.PromptToolkitCmd):
    """The bridge CLI interface."""

    def __init__(self, bridge: BRDG02R13) -> None:
        super().__init__()
        self.prompt = f"[{str(bridge)}]>> "  # f"[BRDG-02R13@{bridge.slave_id}]>>
        self.bridge = bridge

    async def do_nodes(self) -> None:
        """Print the list of bound nodes."""
        LOGGER.debug("do_node starting")
        res = await self.bridge.nodes()
        for n in res:
            print(f"{n}")

    async def do_node(self, slave_id: str) -> None:
        """Manage a bound node."""
        LOGGER.debug("do_node fetch nodes")
        nodes = await self.bridge.nodes()
        LOGGER.debug("do_node starting")
        node_info = None
        for n in nodes:
            LOGGER.debug("do_node match slave_id")
            if int(slave_id) == int(n.slave_id):
                node_info = n
                break
        LOGGER.debug("node_info starting")
        if node_info is None:
            raise AiriosIOException(f"Node with address {slave_id} not bound")

        # find by product_id: {'VMD-07RPS13': 116867, 'VMD-02RPS78': 116882, 'VMN-05LM02': 116798}
        # compare to src/pyairios/_init_.py: fetch models from bridge
        key = str(node_info.product_id)
        _node = modules[key].Node(node_info.slave_id, self.bridge.client)
        if key == "VMD-02RPS78":  # dedicated CLI for each model
            await AiriosVMD02RPS78CLI(_node).run()
            return
        elif key == "VMD-07RPS13":  # ClimaRad Ventura
            LOGGER.debug("Node Ventura starts")
            await AiriosVMD07RPS13CLI(_node).run()
            return
        elif key == "VMN-05LM02":  # Remote accessory
            await AiriosVMN05LM02CLI(_node).run()
            return
        # add new models AiriosXXXXXXXXXCLI here to use them in CLI

        raise AiriosNotImplemented(
            f"{node_info.product_id} not implemented. Drop new definitions in models/"
        )

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

    async def do_node_oem_number(self) -> None:
        """Print the node OEM number."""
        number = await self.bridge.node_oem_number()
        print(number)

    async def do_oem_code(self) -> None:
        """Print the OEM code."""
        number = await self.bridge.oem_code()
        print(number)

    async def do_set_oem_code(self, number: int) -> None:
        """Set the OEM code."""
        await self.bridge.set_oem_code(int(number))

    async def do_status(self) -> None:
        """Print the complete device status."""
        await self.bridge.print_data()


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
        assert self.client  # to debug in test_one
        print("client attached. Waiting for client.run() ...")
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
        """Set the log level: critical, fatal, error, warning, info or debug."""
        if level is None:
            return
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
