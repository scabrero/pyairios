#!/usr/bin/env python3
"""pyairios minimal pytest suite."""
# compare to pymodbus/test/client/test_client_sync.py TestSyncClientSerial

import logging
import sys

import pytest

from cli.airios_cli import AiriosRootCLI
from pyairios import Airios, AiriosRtuTransport
from pyairios.exceptions import AiriosConnectionException

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format="%(levelname)s - %(message)s")


class TestStartPyairiosCli:
    """
    CLI tests.
    """

    def test_cli_root_init(self) -> None:
        """
        Test cli.py root level init.
        """

        # init CLI
        cli = AiriosRootCLI()
        assert cli, "no CLI"

    @pytest.mark.asyncio
    async def test_cli_connect(self) -> None:
        """
        Test cli.py serial connect on null port.
        """

        # init CLI
        cli = AiriosRootCLI()
        # connect
        await cli.do_connect_rtu("/dev/null")

        assert cli.client, "no client"


class TestStartPyairiosApi:
    """
    Airios api tests.
    """

    @pytest.mark.asyncio
    async def test_api_init(self) -> None:
        """
        Test pyairios api serial init.
        """

        transport = AiriosRtuTransport("/dev/null")

        # init api
        api = Airios(transport)
        assert api, "no api"

    @pytest.mark.asyncio
    async def test_api_connect(self) -> None:
        """
        Test pyairios api serial connect.
        """

        transport = AiriosRtuTransport("/dev/null")
        api = Airios(transport)

        # try to connect
        try:
            await api.connect()
        except AiriosConnectionException:
            pass
        else:
            raise AssertionError("Expected AiriosConnectionException")
        # api.close()
