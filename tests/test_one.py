#!/usr/bin/env python3
"""pyairios minimal pytest suite."""
# compare to pymodbus/test/client/test_client_sync.py TestSyncClientSerial

import logging
import pytest
import sys

from cli import AiriosRootCLI
from pyairios import Airios, AiriosRtuTransport

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format="%(levelname)s - %(message)s")


class TestStartPyairiosCli:
    """
    CLI tests.
    """

    def test_init_cli_root(self) -> None:
        """
        Test root level init of cli.py.
        """

        # init CLI
        cli = AiriosRootCLI()
        assert cli, "no CLI"

    @pytest.mark.asyncio
    async def test_cli_init(self) -> None:
        """
        Test cli.py serial connect on null port.
        """

        # init CLI
        cli = AiriosRootCLI()
        await cli.do_connect_rtu("/dev/null")

        assert cli.client, "no client"


class TestStartPyairiosApi:
    """
    Airios api tests.
    """

    @pytest.mark.asyncio
    async def test_api_init(self) -> None:
        """
        Test pyairios api serial connect on null port.
        """

        transport = AiriosRtuTransport("/dev/null")

        # init api
        api = Airios(transport)
        assert api, "no api"
