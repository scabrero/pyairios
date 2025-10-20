"""Airios device factory."""

from pyairios.client import AsyncAiriosModbusClient
from pyairios.constants import ProductId
from pyairios.exceptions import AiriosUnknownProductException
from pyairios.models.brdg_02r13 import BRDG02R13
from pyairios.models.vmd_02rps78 import VMD02RPS78
from pyairios.models.vmn_05lm02 import VMN05LM02


class AiriosDeviceFactory:  # pylint: disable=too-few-public-methods
    """Airios device factory."""

    def get_device_by_product_id(
        self,
        product_id: ProductId,
        address: int,
        client: AsyncAiriosModbusClient,
    ):
        """Get device instance by product ID."""

        try:
            pid = ProductId(product_id)
            if pid == ProductId.BRDG_02R13:
                return BRDG02R13(address, client)
            if pid == ProductId.VMD_02RPS78:
                return VMD02RPS78(address, client)
            if pid in (ProductId.VMN_05LM02, ProductId.VMN_02LM11):
                return VMN05LM02(address, client)
            raise AiriosUnknownProductException(f"Unknown product ID 0x{product_id:08X}")
        except ValueError as ex:
            raise AiriosUnknownProductException(f"Unknown product ID 0x{product_id:08X}") from ex


factory = AiriosDeviceFactory()
