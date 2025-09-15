#!/usr/bin/env python3
"""pyairios minimal pytest suite."""

import logging
import sys

from mock_serial import MockSerial
from serial import Serial

from cli import AiriosRootCLI

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format="%(levelname)s - %(message)s")


class TestStartPyairios:  # pylint: disable=too-few-public-methods
    """
    pyairios tests.
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

    # TODO(eb): mock serial port so connect + next cli levels can run
    #  see pymodbus simulator + their tests

    # TODO(eb): add Airios api init test
