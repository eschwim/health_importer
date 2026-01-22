"""Tests for libs/oura.py OuraPoller functionality."""

from datetime import datetime
from typing import TYPE_CHECKING
from unittest import mock

import pytest

if TYPE_CHECKING:
    from libs.oura import OuraPoller


@pytest.fixture
def oura_poller() -> "OuraPoller":
    """Create an OuraPoller instance for testing."""
    # Mock the constants module to avoid needing real env vars
    with mock.patch("libs.oura.constants") as mock_constants:
        mock_constants.TZ = datetime.now().astimezone().tzinfo
        mock_constants.INFLUXDB_HOST = "localhost"
        mock_constants.INFLUXDB_PORT = 8086
        mock_constants.INFLUXDB_USER = "test"
        mock_constants.INFLUXDB_PASS = "test"
        mock_constants.INFLUXDB_DB = "test"

        from libs.oura import OuraPoller

        token_cfg: dict[str, str | int] = {"access_token": "test_token"}
        return OuraPoller(token_cfg)


class TestOuraPoller:
    """Tests for OuraPoller class."""

    async def test_handle_data_empty_list(self, oura_poller: "OuraPoller") -> None:
        """Test that handle_data handles empty data gracefully."""
        with mock.patch.object(oura_poller, "influxdb_insert") as mock_insert:
            await oura_poller.handle_data("test_measurement", [])
            mock_insert.assert_not_called()

    async def test_handle_data_filters_non_dict(self, oura_poller: "OuraPoller") -> None:
        """Test that handle_data filters out non-dict data."""
        with mock.patch.object(oura_poller, "influxdb_insert") as mock_insert:
            await oura_poller.handle_data("test_measurement", ["not_a_dict"])  # type: ignore
            # Should still call insert but with filtered data
            mock_insert.assert_called_once()

    async def test_handle_data_requires_timestamp(self, oura_poller: "OuraPoller") -> None:
        """Test that handle_data requires a timestamp field."""
        with mock.patch.object(oura_poller, "influxdb_insert") as mock_insert:
            await oura_poller.handle_data("test_measurement", [{"value": 1}])
            # Should call insert with empty filtered list
            mock_insert.assert_called_once()

    async def test_handle_data_with_day_field(self, oura_poller: "OuraPoller") -> None:
        """Test that handle_data accepts 'day' as timestamp."""
        with mock.patch.object(oura_poller, "influxdb_insert") as mock_insert:
            data: list[dict[str, int | float | str]] = [
                {"day": "2024-01-01", "value": 100}
            ]
            await oura_poller.handle_data("test_measurement", data)
            mock_insert.assert_called_once()
            # Check that the data was passed through
            call_args = mock_insert.call_args
            assert call_args[0][0] == "test_measurement"

    async def test_handle_data_with_timestamp_field(
        self, oura_poller: "OuraPoller"
    ) -> None:
        """Test that handle_data accepts 'timestamp' as timestamp."""
        with mock.patch.object(oura_poller, "influxdb_insert") as mock_insert:
            data: list[dict[str, int | float | str]] = [
                {"timestamp": "2024-01-01T00:00:00Z", "value": 100}
            ]
            await oura_poller.handle_data("test_measurement", data)
            mock_insert.assert_called_once()

    async def test_handle_data_single_dict_input(
        self, oura_poller: "OuraPoller"
    ) -> None:
        """Test that handle_data wraps single dict in list."""
        with mock.patch.object(oura_poller, "influxdb_insert") as mock_insert:
            data: dict[str, int | float | str] = {"day": "2024-01-01", "value": 100}
            await oura_poller.handle_data("test_measurement", data)
            mock_insert.assert_called_once()


class TestOuraPollerAPI:
    """Tests for OuraPoller API interaction."""

    async def test_call_oura_api_waits_for_token(self) -> None:
        """Test that call_oura_api waits when no token is available."""
        with mock.patch("libs.oura.constants") as mock_constants:
            mock_constants.API_URL = "https://api.ouraring.com/v2/usercollection"

            from libs.oura import OuraPoller

            token_cfg: dict[str, str | int] = {}  # No token initially
            poller = OuraPoller(token_cfg)

            # Add token after a short delay in another task
            async def add_token() -> None:
                import asyncio

                await asyncio.sleep(0.1)
                token_cfg["access_token"] = "test_token"

            import asyncio

            from aioresponses import aioresponses

            with aioresponses() as mocked:
                mocked.get(
                    "https://api.ouraring.com/v2/usercollection/heartrate",
                    payload={"data": []},
                )

                # Start token addition in background
                asyncio.create_task(add_token())

                # This should wait for the token then make the request
                result = await poller.call_oura_api("heartrate")
                assert result == {"data": []}
