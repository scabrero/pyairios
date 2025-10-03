"""Airios BRDG-BASE controller implementation."""

from __future__ import annotations

import asyncio
import glob
import importlib.util
import logging
import os
import re
from types import ModuleType

from pyairios.device import AiriosDevice
from pyairios.exceptions import AiriosException
from pyairios.registers import RegisterAddress

LOGGER = logging.getLogger(__name__)


class Reg(RegisterAddress):
    """Register set for BRDG-BASE controller node."""


def pr_id() -> int:
    """
    Get product_id for model BRDG- models.
    Named as is to discern from node.product_id register.
    :return: unique int
    """
    # base class, should not be called
    return 0x0


def product_descr() -> str | tuple[str, ...]:
    """
    Get description of product(s) using BRDG_xxxx.
    Human-readable text, used in e.g. HomeAssistant Binding UI.
    :return: string or tuple of strings, starting with manufacturer
    """
    # base class, should not be called
    return "-"


class BrdgBase(AiriosDevice):
    """Base class for BRDG-xxx bridge nodes.
    Only contains common Airios support methods, available to all bridge implementations.
    """

    modules: dict[str, ModuleType] = {}
    # a dict with imported modules by model
    prids: dict[str, int] = {}
    # a dict with product_ids by model (replaces ProductId enum in const.py)
    descriptions: dict[str, str] = {}
    # a dict with label description model, for use in UI
    modules_loaded: bool = False

    async def load_models(self) -> int:
        """
        Analyse and import all VMx.py files from the models/ folder.
        """
        if not self.modules_loaded:
            loop = asyncio.get_running_loop()
            # must call this async run_in_executor to prevent HA blocking call during file I/O.
            modules_list = await loop.run_in_executor(
                None, glob.glob, os.path.join(os.path.dirname(__file__), "*.py")
            )
            # we are in models/
            check_id = []

            for file_path in modules_list:
                file_name = str(os.path.basename(file_path))
                if (
                    file_name == "__init__.py" or file_name.endswith("_base.py")
                    # or file_name == "brdg_02r13.py"  # bridges have sensors that need this info
                ):  # skip init and any base model definitions
                    continue
                module_name = file_name.removesuffix(".py")
                if module_name is None:
                    raise AiriosException(f"Failed to extract mod_name from filename {file_name}")
                model_key: str = str(re.sub(r"_", "-", module_name).upper())
                if model_key is None:
                    raise AiriosException(f"Failed to create model_key from {module_name}")

                # using importlib, create a spec for each module:
                module_spec = importlib.util.spec_from_file_location(module_name, file_path)
                if module_spec is None or module_spec.loader is None:
                    raise AiriosException(f"Failed to load module {module_name}")
                # store the spec in a dict by class name:
                mod = importlib.util.module_from_spec(module_spec)
                # load the module from the spec:
                if mod is None:
                    raise AiriosException(f"Failed to load module_from_spec {module_name}")
                module_spec.loader.exec_module(mod)
                # store the imported module in dict:
                self.modules[model_key] = mod

                # now we can use the module as if it were imported normally
                # check correct loading by fetching the product_id
                # (the int to check binding against)
                _id = self.modules[model_key].pr_id()
                # verify no duplicate product_id's
                if _id in check_id:  #  product_id not unique among models
                    raise AiriosException(
                        f"Found duplicate product_id while collecting models:id {model_key}"
                        f"used by {self.modules[model_key].__name__} and by {mod.__name__}"
                    )
                self.prids[model_key] = _id
                check_id.append(_id)  # remember all added _id's to check for duplicates
                self.descriptions[model_key] = self.modules[model_key].product_descr()

            LOGGER.debug("Loaded modules:")
            LOGGER.debug(self.modules)  # dict
            LOGGER.info("Loaded product_id's:")
            LOGGER.info(self.prids)  # dict
            LOGGER.info("Loaded products:")
            LOGGER.info(self.descriptions)  # dict
            # all loaded up
            self.modules_loaded = True
        return len(self.modules)

    async def models(self) -> dict[str, ModuleType] | None:
        """
        Util to fetch all supported models with their imported module class.
        Must call this async run_in_executor to prevent HA blocking call during file I/O.

        :return: dict of all controller and accessory modules by key
        """
        if not self.modules_loaded:
            task = asyncio.create_task(self.load_models())
            await task
            return self.modules
        return self.modules

    async def model_descriptions(self) -> dict[str, str] | None:
        """
        Util to fetch all supported model labels.

        :return: dict of all controller and accessory module labels by key
        """
        if not self.modules_loaded:
            task = asyncio.create_task(self.load_models())
            await task
            return self.descriptions
        return self.descriptions

    async def product_ids(self) -> dict[str, int] | None:
        """
        Util to pick up all supported models with their productId.

        :return: dict of all controller and accessory definitions installed
        """
        if not self.modules_loaded:
            task = asyncio.create_task(self.load_models())
            await task
            return self.prids
        return self.prids

    def print_base_data(self, res) -> None:
        """
        Print shared BRDG labels + states, in CLI.

        :return: no confirmation, outputs to serial monitor
        """
        print("Node data")
        print("---------")
        print(f"    {'Product ID:': <25}{res['product_id']} (0x{res['product_id']:08X})")
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

        amount = 0 if self.modules is None else len(self.modules)
        print(f"Loaded {amount} model files")
        if self.modules is not None:
            for key, mod in self.modules.items():
                report1 = f"{key[:3]}{':': <6}{key: <14}name: {mod.__name__: <14} descr.:"
                report2 = f"{str(mod.product_descr()): <38} product_id: {mod.pr_id()}"
                print(f"    {report1}{report2}")
        # print(f"    {'ProductIDs:': <13}{self.prids}")

        print("----------------")
