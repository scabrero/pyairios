"""Exceptions from the Airios library."""


class AiriosException(Exception):
    """Base class for Airios exceptions."""


class AiriosDecodeError(AiriosException):
    """Decoding failed."""


class AiriosEncodeError(AiriosException):
    """Encoding failed."""


class AiriosConnectionException(AiriosException):
    """Exception connecting to device."""


class AiriosInvalidArgumentException(AiriosException):
    """Invalid argument."""

    def __init__(self, message: str):
        super().__init__(message)


class AiriosReadException(AiriosException):
    """Exception reading register from device."""

    def __init__(self, message: str, modbus_exception_code: int | None):
        super().__init__(message)
        self.modbus_exception_code = modbus_exception_code


class AiriosConnectionInterruptedException(AiriosException):
    """Connection to the device was interrupted."""


class AiriosSlaveBusyException(AiriosException):
    """Non-fatal exception while trying to read from device."""


class AiriosSlaveFailureException(AiriosException):
    """Possibly fatal exception while trying to read from device."""


class AiriosAcknowledgeException(AiriosException):
    """Device accepted the request but needs time to process it."""


class AiriosWriteException(AiriosException):
    """Exception writing register to device."""

    def __init__(self, message: str, modbus_exception_code: int | None):
        super().__init__(message)
        self.modbus_exception_code = modbus_exception_code


class AiriosBindingException(AiriosException):
    """Binding failed."""


class AiriosNotImplemented(AiriosException):
    """Exception not implemented"""


class AiriosIOException(AiriosException):
    """I/O exception"""
