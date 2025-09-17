#!/usr/bin/env python3
"""pyairios minimal pytest suite."""

import logging
import sys

from mock_serial import MockSerial
from serial import Serial

from cli import AiriosRootCLI
from pyairios import Airios, AiriosRtuTransport

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format="%(levelname)s - %(message)s")


class TestStartPyairiosCli:  # pylint: disable=too-few-public-methods
    """
    CLI tests.
    """

    def test_init_cli_root(self) -> None:
        """
        Test root level init of cli.py.
        """
        device = MockSerial()
        device.open()
        serial = Serial(device.port)

        # init CLI
        cli = AiriosRootCLI()
        assert cli, "no CLI"

        # break down
        serial.close()
        device.close()

    @pytest.mark.asyncio
    @pytest.mark.timeout(1)
    async def test_cli_init(self) -> None:
        """
        Test cli.py serial connect on mocked port.
        """
        device = MockSerial()
        device.open()
        serial = Serial(device.port)

        # init CLI
        cli = AiriosRootCLI()
        try:
            await cli.do_connect_rtu(str(serial))
            # timeout here, but no error
            # TODO(eb): mock serial port so test can run, see pymodbus tests
            # see pymodbus simulator + their tests
        except TimeoutError:
            pass
        else:
            raise AssertionError("Expected TimeoutError")

        # assert cli.client, "no client"

        # break down
        serial.close()
        device.close()

    @pytest.mark.asyncio
    async def test_api_init(self) -> None:
        """
        Test pyairios api serial connect on mocked port.
        """
        device = MockSerial()
        device.open()
        serial = Serial(device.port)
        transport = AiriosRtuTransport(device)

        # init api
        api = Airios(transport)
        assert api, "no api"

        # break down
        serial.close()
        device.close()
