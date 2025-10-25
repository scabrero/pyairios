"""Airios device factory."""

import asyncio
from dataclasses import dataclass
import glob
import importlib.util
import logging
import os
from types import ModuleType
from typing import Dict

from pyairios.client import AsyncAiriosModbusClient
from pyairios.constants import AiriosDeviceType, ProductId
from pyairios.device import AiriosDevice
from pyairios.exceptions import AiriosException, AiriosUnknownProductException

LOGGER = logging.getLogger(__name__)


@dataclass
class AiriosDeviceDescription:
    """Airios device description."""

    product_id: ProductId
    type: AiriosDeviceType
    description: list[str]


class AiriosDeviceFactory:
    """Airios device factory."""

    modules: Dict[ProductId, ModuleType]
    modules_loaded: bool

    def __init__(self) -> None:
        self.modules_loaded = False
        self.modules = {}

    async def get_device_by_product_id(
        self,
        product_id: ProductId,
        address: int,
        client: AsyncAiriosModbusClient,
    ) -> AiriosDevice:
        """Get device instance by product ID."""

        if not self.modules_loaded:
            await self.load_models()

        try:
            pid = ProductId(product_id)
            mod = self.modules[pid]
            return mod.pr_instantiate(address, client)
        except ValueError as ex:
            raise AiriosUnknownProductException(f"Unknown product ID 0x{product_id:08X}") from ex
        except KeyError as ex:
            raise AiriosUnknownProductException(f"Unknown product ID 0x{product_id:08X}") from ex

    async def load_models(self) -> int:
        """
        Analyse and import all .py files from the models/ folder.
        """
        if not self.modules_loaded:
            loop = asyncio.get_running_loop()
            # must call this async run_in_executor to prevent HA blocking call during file I/O.
            modules_list = await loop.run_in_executor(
                None, glob.glob, os.path.join(os.path.dirname(__file__), "*.py")
            )

            for file_path in modules_list:
                file_name = str(os.path.basename(file_path))
                if file_name in ("__init__.py", "factory.py"):
                    continue
                module_name = file_name.removesuffix(".py")

                # using importlib, create a spec for each module:
                module_spec = importlib.util.spec_from_file_location(module_name, file_path)
                if not module_spec:
                    LOGGER.warning(
                        "Failed to create spec from file %s - %s", module_name, file_path
                    )
                    continue

                mod = importlib.util.module_from_spec(module_spec)

                if not module_spec.loader:
                    LOGGER.warning("Module spec has no loader (%s)", module_spec)
                    continue
                module_spec.loader.exec_module(mod)

                _id = mod.pr_id()
                if _id in self.modules:
                    prev = self.modules[_id]
                    raise AiriosException(
                        f"Found duplicate product_id while collecting models: {_id}"
                        f"used by {prev.__name__} and by {mod.__name__}"
                    )
                self.modules[_id] = mod

            LOGGER.debug("Loaded modules: %s", str(self.modules))

            self.modules_loaded = True

        return len(self.modules)

    async def models(self) -> Dict[ProductId, ModuleType]:
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

    async def model_descriptions(self) -> list[AiriosDeviceDescription]:
        """
        Util to fetch all supported model descriptions.
        """
        if not self.modules_loaded:
            task = asyncio.create_task(self.load_models())
            await task
        descriptions: list[AiriosDeviceDescription] = []
        for mod in self.modules.values():
            d = AiriosDeviceDescription(
                product_id=mod.pr_id(),
                type=mod.pr_type(),
                description=mod.pr_description(),
            )
            descriptions.append(d)
        return descriptions


factory = AiriosDeviceFactory()
