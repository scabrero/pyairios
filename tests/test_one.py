import logging
import sys

import pytest
from mock_serial import MockSerial
from serial import Serial

# from pyairios.client import AsyncAiriosModbusRtuClient
from cli import AiriosRootCLI

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format="%(levelname)s - %(message)s")


class TestStartPyairios:
    def test_init_root(self):
        device = MockSerial()
        device.open()
        serial = Serial(device.port)

        stub = device.stub(name="foo", receive_bytes=b"123", send_bytes=b"456")

        # init CLI
        cli = AiriosRootCLI()
        assert cli, "no CLI"

        # break down
        serial.close()
        device.close()

    @pytest.mark.asyncio
    @pytest.mark.timeout(1)
    async def test_init(self):
        device = MockSerial()
        device.open()
        serial = Serial(device.port)

        # stub = device.stub(name="foo", receive_bytes=b"123", send_bytes=b"456")

        # init CLI
        cli = AiriosRootCLI()
        await cli.do_connect_rtu(serial)
        # TODO timeout here, but no error
        assert cli.client, "no client"

        # break down
        serial.close()
        device.close()
