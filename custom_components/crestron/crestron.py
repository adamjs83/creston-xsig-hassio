import asyncio
import struct
import logging
from typing import Callable, Any
from collections.abc import Coroutine

_LOGGER = logging.getLogger(__name__)

class CrestronXsig:
    def __init__(self) -> None:
        """ Initialize CrestronXsig object """
        self._digital: dict[int, bool] = {}
        self._analog: dict[int, int] = {}
        self._serial: dict[int, str] = {}
        # Track which joins have received data from Crestron
        self._digital_received: set[int] = set()
        self._analog_received: set[int] = set()
        self._serial_received: set[int] = set()
        self._writer: asyncio.StreamWriter | None = None
        self._callbacks: set[Callable[[str, str], Coroutine[Any, Any, None]]] = set()
        self._server: asyncio.Server | None = None
        self._available: bool = False
        self._sync_all_joins_callback: Callable[[], Coroutine[Any, Any, None]] | None = None
        self.port: int | None = None

    async def listen(self, port: int) -> None:
        """ Start TCP XSIG server listening on configured port """
        self.port = port
        server = await asyncio.start_server(self.handle_connection, "0.0.0.0", port)
        self._server = server
        addr = server.sockets[0].getsockname()
        _LOGGER.info("Listening on %s:%s", addr, port)
        # Use create_task to properly run the server in the background
        asyncio.create_task(server.serve_forever())

    async def stop(self) -> None:
        """ Stop TCP XSIG server """
        self._available = False
        for callback in self._callbacks:
            await callback("available", "False")
        _LOGGER.info("Stop called. Closing connection")

        # Close the writer if connected (drain pending data first)
        if self._writer is not None:
            try:
                self._writer.close()
                await self._writer.wait_closed()
                _LOGGER.debug("Writer closed successfully")
            except Exception as err:
                _LOGGER.debug("Error closing writer: %s", err)
            self._writer = None

        # Close the server and wait for it to fully stop
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            _LOGGER.debug("Server closed successfully")

    def register_sync_all_joins_callback(self, callback: Callable[[], Coroutine[Any, Any, None]]) -> None:
        """ Allow callback to be registred for when control system requests an update to all joins """
        _LOGGER.debug("Sync-all-joins callback registered")
        self._sync_all_joins_callback = callback

    def register_callback(self, callback: Callable[[str, str], Coroutine[Any, Any, None]]) -> None:
        """ Allow callbacks to be registered for when dict entries change """
        self._callbacks.add(callback)

    def remove_callback(self, callback: Callable[[str, str], Coroutine[Any, Any, None]]) -> None:
        """ Allow callbacks to be de-registered """
        self._callbacks.discard(callback)

    async def handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """ Parse packets from Crestron XSIG symbol """
        self._writer = writer
        peer = writer.get_extra_info("peername")
        _LOGGER.info("Control system connection from %s", peer)
        _LOGGER.debug("Sending update request")
        writer.write(b"\xfd")
        self._available = True
        for callback in self._callbacks:
            await callback("available", "True")

        connected = True
        while connected:
            data = await reader.read(1)
            if data:
                # Sync all joins request
                if data[0] == 0xFB:
                    _LOGGER.debug("Got update all joins request")
                    if self._sync_all_joins_callback is not None:
                        await self._sync_all_joins_callback()
                        _LOGGER.debug("Calling sync-all-joins callback")
                else:
                    data += await reader.read(1)
                    # Digital Join
                    if (
                        data[0] & 0b11000000 == 0b10000000
                        and data[1] & 0b10000000 == 0b00000000
                    ):
                        header = struct.unpack("BB", data)
                        join = ((header[0] & 0b00011111) << 7 | header[1]) + 1
                        value = ~header[0] >> 5 & 0b1
                        self._digital[join] = True if value == 1 else False
                        self._digital_received.add(join)  # Mark as received
                        # Removed excessive debug logging that floods logs
                        # _LOGGER.debug(f"Got Digital: {join} = {value}")
                        for callback in self._callbacks:
                            await callback(f"d{join}", str(value))
                    # Analog Join
                    elif (
                        data[0] & 0b11001000 == 0b11000000
                        and data[1] & 0b10000000 == 0b00000000
                    ):
                        data += await reader.read(2)
                        header = struct.unpack("BBBB", data)
                        join = ((header[0] & 0b00000111) << 7 | header[1]) + 1
                        value = (
                            (header[0] & 0b00110000) << 10 | header[2] << 7 | header[3]
                        )
                        self._analog[join] = value
                        self._analog_received.add(join)  # Mark as received
                        # Removed excessive debug logging that floods logs
                        # _LOGGER.debug(f"Got Analog: {join} = {value}")
                        for callback in self._callbacks:
                            await callback(f"a{join}", str(value))
                    # Serial Join
                    elif (
                        data[0] & 0b11111000 == 0b11001000
                        and data[1] & 0b10000000 == 0b00000000
                    ):
                        data += await reader.readuntil(b"\xff")
                        header = struct.unpack("BB", data[:2])
                        join = ((header[0] & 0b00000111) << 7 | header[1]) + 1
                        string = data[2:-1].decode("utf-8")
                        self._serial[join] = string
                        self._serial_received.add(join)  # Mark as received
                        # Removed excessive debug logging that floods logs
                        # _LOGGER.debug(f"Got String: {join} = {string}")
                        for callback in self._callbacks:
                            await callback(f"s{join}", string)
                    else:
                        _LOGGER.debug("Unknown Packet: %s", data.hex())
            else:
                _LOGGER.info("Control system disconnected")
                connected = False
                self._available = False
                for callback in self._callbacks:
                    await callback("available", "False")

    def is_available(self) -> bool:
        """Returns True if control system is connected"""
        return self._available

    def get_analog(self, join: int) -> int:
        """ Return analog value for join"""
        return self._analog.get(join, 0)

    def get_digital(self, join: int) -> bool:
        """ Return digital value for join"""
        return self._digital.get(join, False)

    def get_serial(self, join: int) -> str:
        """ Return serial value for join"""
        return self._serial.get(join, "")

    def has_analog_value(self, join: int) -> bool:
        """ Check if analog join has received valid data from Crestron """
        return join in self._analog_received

    def has_digital_value(self, join: int) -> bool:
        """ Check if digital join has received valid data from Crestron """
        return join in self._digital_received

    def has_serial_value(self, join: int) -> bool:
        """ Check if serial join has received valid data from Crestron """
        return join in self._serial_received

    def set_analog(self, join: int, value: int) -> None:
        """ Send Analog Join to Crestron XSIG symbol """
        if self._writer:
            try:
                data = struct.pack(
                    ">BBBB",
                    0b11000000 | (value >> 10 & 0b00110000) | (join - 1) >> 7,
                    (join - 1) & 0b01111111,
                    value >> 7 & 0b01111111,
                    value & 0b01111111,
                )
                self._writer.write(data)
                # Removed excessive debug logging
                # _LOGGER.debug(f"Sending Analog: {join}, {value}")
            except OSError as err:
                _LOGGER.warning("Failed to send analog join %s: %s", join, err)
                self._writer = None  # Mark connection as dead
                self._available = False
        else:
            _LOGGER.debug("Could not send analog. No connection to hub")

    async def async_set_analog(self, join: int, value: int) -> None:
        """ Send Analog Join to Crestron XSIG symbol and ensure it's transmitted """
        if self._writer:
            try:
                data = struct.pack(
                    ">BBBB",
                    0b11000000 | (value >> 10 & 0b00110000) | (join - 1) >> 7,
                    (join - 1) & 0b01111111,
                    value >> 7 & 0b01111111,
                    value & 0b01111111,
                )
                self._writer.write(data)
                await self._writer.drain()  # Ensure data is actually sent
            except OSError as err:
                _LOGGER.warning("Failed to send analog join %s: %s", join, err)
                self._writer = None  # Mark connection as dead
                self._available = False
        else:
            _LOGGER.debug("Could not send analog. No connection to hub")

    def set_digital(self, join: int, value: int) -> None:
        """ Send Digital Join to Crestron XSIG symbol """
        if self._writer:
            try:
                data = struct.pack(
                    ">BB",
                    0b10000000 | (~value << 5 & 0b00100000) | (join - 1) >> 7,
                    (join - 1) & 0b01111111,
                )
                self._writer.write(data)
                # Removed excessive debug logging
                # _LOGGER.debug(f"Sending Digital: {join}, {value}")
            except OSError as err:
                _LOGGER.warning("Failed to send digital join %s: %s", join, err)
                self._writer = None  # Mark connection as dead
                self._available = False
        else:
            _LOGGER.debug("Could not send digital. No connection to hub")

    async def async_set_digital(self, join: int, value: int) -> None:
        """ Send Digital Join to Crestron XSIG symbol and ensure it's transmitted """
        if self._writer:
            try:
                data = struct.pack(
                    ">BB",
                    0b10000000 | (~value << 5 & 0b00100000) | (join - 1) >> 7,
                    (join - 1) & 0b01111111,
                )
                self._writer.write(data)
                await self._writer.drain()  # Ensure data is actually sent
                # Removed excessive debug logging
                # _LOGGER.debug(f"Sending Digital: {join}, {value}")
            except OSError as err:
                _LOGGER.warning("Failed to send digital join %s: %s", join, err)
                self._writer = None  # Mark connection as dead
                self._available = False
        else:
            _LOGGER.debug("Could not send digital. No connection to hub")

    def set_serial(self, join: int, string: str) -> None:
        """ Send String Join to Crestron XSIG symbol """
        if len(string) > 252:
            _LOGGER.warning("Could not send serial. String too long (%d>252)", len(string))
            return
        elif self._writer:
            try:
                data = struct.pack(
                    ">BB", 0b11001000 | ((join - 1) >> 7), (join - 1) & 0b01111111
                )
                data += string.encode()
                data += b"\xff"
                self._writer.write(data)
                # Removed excessive debug logging
                # _LOGGER.debug(f"Sending Serial: {join}, {string}")
            except OSError as err:
                _LOGGER.warning("Failed to send serial join %s: %s", join, err)
                self._writer = None  # Mark connection as dead
                self._available = False
        else:
            _LOGGER.debug("Could not send serial. No connection to hub")

    def request_update(self) -> None:
        """ Request Crestron to send current state of all joins """
        if self._writer:
            try:
                self._writer.write(b"\xfd")
                _LOGGER.debug("Requested update from Crestron")
            except OSError as err:
                _LOGGER.warning("Failed to request update: %s", err)
                self._writer = None
                self._available = False
        else:
            _LOGGER.debug("Could not request update. No connection to hub")
