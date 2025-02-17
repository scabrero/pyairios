# pyAirios

[![License](https://img.shields.io/github/license/scabrero/pyairios)](https://img.shields.io/github/license/scabrero/pyairios)
[![PyPI version](https://badge.fury.io/py/pyairios.svg)](https://badge.fury.io/py/pyairios)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pyairios)](https://img.shields.io/pypi/pyversions/pyairios)

A Python library to interface with Airios RF bridges.

## Description

[Airios](https://www.airios.eu/) develop and produce several components for residential ventilation systems that final manufacturers use to build their products upon, from controller boards to remote controls or sensors.

All of these components communicate over a proprietary RF protocol from Honeywell called Ramses II in the 868Mhz band. The RF bridge allows third party applications to access the nodes in the RF network over standard Modbus protocol.

There are two bridge models with different interfaces. The [BRDG-02R13](https://www.airios.eu/brdg-02r13) has a RS485 serial interface (Modbus-RTU) and the [BRDG-02EM23](https://www.airios.eu/brdg-02em23) is an Ethernet device (Modbus-TCP).

This library only supports the RS485 model.

## Working principle

Each device in the RF network is called a node and nodes must be bound together to be able to communicate. There are two classes of nodes:

* Controllers (typically ventilation units). Binding mode is enabled for a fixed period after power cycle.
* Accessories (remote controls or sensors). They bind to a controller in a device-specific way, e.g., pressing a combination of buttons.

The bridge is an accessory with special features. It can bind to multiple controllers and at the same time it can "intercept" the accessories binding procedure so they are bound to the controller and the bridge at the same time. Each bound device to the bridge creates a new virtual Modbus slave with its own address and register set. The register set depends on the bounded product.

NOTE:
Binding is only possible when products have the same *OEM code*. The RF bridge has a registry to change it if necessary.

## Supported devices

This library has been tested with the following devices:

* [Siber DF Optima 2](https://www.siberzone.es/descarga/siber-df-optima-2-19170/) ([Airios VMD-02RPS78](https://www.airios.eu/vmd-heat-recovery-unit-controller))
* [Siber 4 button remote](https://www.siberzone.es/descarga/mando-pulsador-inal%C3%81mbrico-4-posiciones-15462/) ([Airios VMN-02LM11](https://www.airios.eu/vmn-02lm11))

## Installation

```bash
python -m pip install pyairios
```

## How to use

The library offers a high level and easy to use API:

```
transport = AiriosModbusRTUTransport(device="/dev/ttyACM0")
api = Airios(transport)
vmd = api.node(<slave id>)
```

A command line interface is also included in the library for testing purposes. Use the `help` or `?` command to get the list of available commands in each context.

![CLI](./docs/cli.gif)

## Acknowledgements

* Siber for providing the documentation and an outstanding support.
