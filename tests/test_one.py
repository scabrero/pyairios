#!/usr/bin/env python3
"""pyairios minimal pytest suite."""

import logging
import sys

import pytest
from mock_serial import MockSerial
from serial import Serial

from cli import AiriosRootCLI

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format="%(levelname)s - %(message)s")


class TestStartPyairiosCli:
    """
    Init CLI test.
    """
    def test_init_root(self):
        device = MockSerial()
        device.open()
        serial = Serial(device.port)

        # init CLI
        cli = AiriosRootCLI()
        assert cli, "no CLI"

        # break down
        serial.close()
        device.close()

        # TODO(eb): mock serial port so test can run, see pymodbus simulator + their tests
