"""Tests for CrestronXsig core protocol handler."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
import sys
import os

# Add custom_components to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from custom_components.crestron.crestron import CrestronXsig


class TestCrestronXsig:
    """Tests for CrestronXsig class."""

    def test_init(self):
        """Test CrestronXsig initialization."""
        xsig = CrestronXsig()

        assert xsig._digital == {}
        assert xsig._analog == {}
        assert xsig._serial == {}
        assert xsig._callbacks == set()
        assert xsig._available is False
        assert xsig._writer is None
        assert xsig._server is None

    def test_get_digital_default(self):
        """Test get_digital returns False for unset joins."""
        xsig = CrestronXsig()
        assert xsig.get_digital(1) is False
        assert xsig.get_digital(100) is False

    def test_get_analog_default(self):
        """Test get_analog returns 0 for unset joins."""
        xsig = CrestronXsig()
        assert xsig.get_analog(1) == 0
        assert xsig.get_analog(100) == 0

    def test_get_serial_default(self):
        """Test get_serial returns empty string for unset joins."""
        xsig = CrestronXsig()
        assert xsig.get_serial(1) == ""
        assert xsig.get_serial(100) == ""

    def test_has_value_methods(self):
        """Test has_*_value methods."""
        xsig = CrestronXsig()

        # Initially no values received
        assert xsig.has_digital_value(1) is False
        assert xsig.has_analog_value(1) is False
        assert xsig.has_serial_value(1) is False

        # Simulate receiving values
        xsig._digital_received.add(1)
        xsig._analog_received.add(2)
        xsig._serial_received.add(3)

        assert xsig.has_digital_value(1) is True
        assert xsig.has_analog_value(2) is True
        assert xsig.has_serial_value(3) is True

    def test_is_available(self):
        """Test is_available method."""
        xsig = CrestronXsig()

        assert xsig.is_available() is False

        xsig._available = True
        assert xsig.is_available() is True

    def test_register_callback(self):
        """Test callback registration."""
        xsig = CrestronXsig()

        async def callback(cbtype, value):
            pass

        xsig.register_callback(callback)
        assert callback in xsig._callbacks

    def test_remove_callback(self):
        """Test callback removal."""
        xsig = CrestronXsig()

        async def callback(cbtype, value):
            pass

        xsig.register_callback(callback)
        assert callback in xsig._callbacks

        xsig.remove_callback(callback)
        assert callback not in xsig._callbacks

    def test_remove_nonexistent_callback(self):
        """Test removing a callback that doesn't exist doesn't raise."""
        xsig = CrestronXsig()

        async def callback(cbtype, value):
            pass

        # Should not raise
        xsig.remove_callback(callback)

    def test_set_digital_no_writer(self):
        """Test set_digital with no connection."""
        xsig = CrestronXsig()

        # Should not raise, just log debug message
        xsig.set_digital(1, True)

    def test_set_analog_no_writer(self):
        """Test set_analog with no connection."""
        xsig = CrestronXsig()

        # Should not raise, just log debug message
        xsig.set_analog(1, 1000)

    def test_set_serial_no_writer(self):
        """Test set_serial with no connection."""
        xsig = CrestronXsig()

        # Should not raise, just log debug message
        xsig.set_serial(1, "test")

    def test_set_serial_too_long(self):
        """Test set_serial with string > 252 chars."""
        xsig = CrestronXsig()
        xsig._writer = MagicMock()

        # Should not raise, just log warning
        xsig.set_serial(1, "x" * 300)

        # Writer.write should not be called for too-long strings
        xsig._writer.write.assert_not_called()

    def test_set_digital_with_writer(self):
        """Test set_digital with active connection."""
        xsig = CrestronXsig()
        xsig._writer = MagicMock()

        xsig.set_digital(1, True)

        xsig._writer.write.assert_called_once()

    def test_set_analog_with_writer(self):
        """Test set_analog with active connection."""
        xsig = CrestronXsig()
        xsig._writer = MagicMock()

        xsig.set_analog(1, 32767)

        xsig._writer.write.assert_called_once()

    def test_request_update_no_writer(self):
        """Test request_update with no connection."""
        xsig = CrestronXsig()

        # Should not raise
        xsig.request_update()

    def test_request_update_with_writer(self):
        """Test request_update with active connection."""
        xsig = CrestronXsig()
        xsig._writer = MagicMock()

        xsig.request_update()

        # Should send 0xFD byte
        xsig._writer.write.assert_called_once_with(b"\xfd")


class TestCrestronXsigAsync:
    """Async tests for CrestronXsig class."""

    @pytest.mark.asyncio
    async def test_stop_without_server(self):
        """Test stop when server not started."""
        xsig = CrestronXsig()

        # Should not raise
        await xsig.stop()

    @pytest.mark.asyncio
    async def test_stop_with_server(self):
        """Test stop with active server."""
        xsig = CrestronXsig()
        xsig._server = AsyncMock()
        xsig._server.close = MagicMock()
        xsig._server.wait_closed = AsyncMock()

        await xsig.stop()

        xsig._server.close.assert_called_once()
        xsig._server.wait_closed.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_stop_with_writer(self):
        """Test stop closes writer properly."""
        xsig = CrestronXsig()
        xsig._writer = MagicMock()
        xsig._writer.close = MagicMock()
        xsig._writer.wait_closed = AsyncMock()
        xsig._server = AsyncMock()
        xsig._server.close = MagicMock()
        xsig._server.wait_closed = AsyncMock()

        await xsig.stop()

        xsig._writer.close.assert_called_once()
        xsig._writer.wait_closed.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_async_set_analog(self):
        """Test async_set_analog drains writer."""
        xsig = CrestronXsig()
        xsig._writer = MagicMock()
        xsig._writer.write = MagicMock()
        xsig._writer.drain = AsyncMock()

        await xsig.async_set_analog(1, 1000)

        xsig._writer.write.assert_called_once()
        xsig._writer.drain.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_async_set_digital(self):
        """Test async_set_digital drains writer."""
        xsig = CrestronXsig()
        xsig._writer = MagicMock()
        xsig._writer.write = MagicMock()
        xsig._writer.drain = AsyncMock()

        await xsig.async_set_digital(1, True)

        xsig._writer.write.assert_called_once()
        xsig._writer.drain.assert_awaited_once()
