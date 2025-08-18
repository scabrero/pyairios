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
    VMDRequestedVentilationSpeed,
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
module_names: dict[str, str] = {}
# a dict with module names by class name, used to fill in CLI prompt model
product_ids: dict[str, str] = {}
# a dict with ids by class name (replaces enum in const.py)
modules: dict[str, ModuleType] = {}
# a dict with imported modules by class name

for file_path in modules_list:
    file_name = str(os.path.basename(file_path))
    if (
        file_name == "__init__.py" or file_name == "brdg_02r13.py" or file_name.endswith("_base.py")
    ):  # skip BRDG and the base model definitions
        continue
    module_name = file_name[:-3]  # drop '.py' file extension
    model_key: str = str(re.sub(r"_", "", module_name).upper())  # drop '_'
    assert model_key is not None
    module_names[model_key] = str(module_name.upper())  # convert to upper case, dict by class_name

    # using importlib, create a spec for each module:
    module_spec = importlib.util.spec_from_file_location(module_name, file_path)
    # store the spec in a dict by class name:
    mod = importlib.util.module_from_spec(module_spec)
    # load the module from the spec:
    module_spec.loader.exec_module(mod)
    # store the imported module in dict:
    modules[model_key] = mod
    # now we can use the module as if it were imported normally

    # check loading by fetching the product_id, the int te check against
    product_ids[model_key] = modules[model_key].product_id()

print("module_names by key:")
print(module_names)  # dict
print("Loaded modules:")
print(modules)  # dict
print("Loaded product_id's:")
print(product_ids)  # dict
# all loaded up


class AiriosVmnCLI(aiocmd.PromptToolkitCmd):
    """The VMN_ modules common CLI interface."""

    class_pointer: str = "VMN"

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

        self.vmn.print_data(res)


class AiriosVmdCLI(aiocmd.PromptToolkitCmd):
    """The VMD_ modules common CLI interface."""

    class_pointer: str = "VMD"  # (how) is this used?

    def __init__(self, vmd) -> None:
        """
        :param vmd: contains all details of this model
        """
        super().__init__()
        self.vmd = vmd
        self.class_pointer = str(vmd)
        self.prompt = f"[{str(vmd)}]>> "

    async def do_capabilities(self) -> None:
        """Print the device RF capabilities."""
        res = await self.vmd.capabilities()
        print(f"{res.value} ({res.status})")

    async def do_status(self) -> None:  # pylint: disable=too-many-statements
        """Print the device status."""
        res = await self.vmd.fetch_vmd_data()  # customised in model file
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

        self.vmd.print_data(res)

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

        print()  # just a spacer

        # find by product_ids: {'VMD07RPS13': 116867, 'VMD02RPS78': 116882, 'VMN05LM02': 116798}
        # compare to src/pyairios/_init_.py: fetch models from bridge
        for key, value in product_ids.items():
            LOGGER.debug(f"Looking up Key: {key}, Value: {value}")
            # DEBUG:__main__:Looking up Key: VMD07RPS13, Value: 116867
            if value == node_info.product_id:
                LOGGER.debug(f"Start matching CLI for: {key}")
                if key.startswith("VMD"):
                    LOGGER.debug("Start vmdCLI")
                    # DEBUG:__main__:Start matching CLI for: VMD_07RPS13
                    vmd = modules[key].VmdNode(  # use fixed class name in all VMD models
                        node_info.slave_id, self.bridge.client
                    )
                    LOGGER.debug(f"await AiriosVmdCLI for: {key}")  # << up to here OK
                    # DEBUG:__main__:await AiriosVmdCLI for: VMD07RPS13
                    # Command failed:  'str' object has no attribute 'vmd_07rps13'
                    await AiriosVmdCLI(vmd).run()
                    LOGGER.debug(f"Loaded vmd for {key}")
                    return

                elif key.startswith("VMN"):
                    LOGGER.debug("Start vmnCLI")
                    vmn = modules[key].VmnNode(  # modules[VMD_02RPS78].VMD02RPS78(
                        node_info.slave_id, self.bridge.client
                    )
                    LOGGER.debug(f"await AiriosVmnCLI: {key}")
                    await AiriosVmnCLI(vmn).run()
                    LOGGER.debug("Loaded vmn for {key}")
                    return

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
