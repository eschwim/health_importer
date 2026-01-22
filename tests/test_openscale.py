"""Tests for libs/openscale.py OpenScalePoller functionality."""

import json
from typing import TYPE_CHECKING
from unittest import mock

import pytest

if TYPE_CHECKING:
    from libs.openscale import OpenScalePoller


@pytest.fixture
def openscale_poller() -> "OpenScalePoller":
    """Create an OpenScalePoller instance for testing."""
    with mock.patch("libs.openscale.constants") as mock_constants:
        mock_constants.INFLUXDB_HOST = "localhost"
        mock_constants.INFLUXDB_PORT = 8086
        mock_constants.INFLUXDB_USER = "test"
        mock_constants.INFLUXDB_PASS = "test"
        mock_constants.INFLUXDB_DB = "test"
        mock_constants.OPENSCALE_MQTT_HOST = "localhost"
        mock_constants.OPENSCALE_MQTT_PORT = 1883
        mock_constants.OPENSCALE_MQTT_TOPIC = "openScaleSync"

        from libs.openscale import OpenScalePoller

        return OpenScalePoller()


class TestOpenScalePoller:
    """Tests for OpenScalePoller class."""

    async def test_influx_insert_parses_json(
        self, openscale_poller: "OpenScalePoller"
    ) -> None:
        """Test that influx_insert correctly parses JSON payload."""
        payload = json.dumps(
            {
                "date": "2024-01-01T10:00:00Z",
                "weight": 70.5,
                "bmi": 22.5,
                "fat": 15.0,
            }
        ).encode()

        with mock.patch("libs.openscale.InfluxDBClient") as mock_client:
            mock_instance = mock.AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance

            await openscale_poller.influx_insert(payload)

            # Verify the client was called
            mock_instance.write.assert_called_once()

            # Check the point structure
            call_args = mock_instance.write.call_args[0][0]
            assert call_args["measurement"] == "scale_metrics"
            assert call_args["time"] == "2024-01-01T10:00:00Z"
            assert call_args["fields"]["weight"] == 70.5
            assert call_args["fields"]["bmi"] == 22.5
            assert "date" not in call_args["fields"]  # date should be popped

    async def test_influx_insert_handles_minimal_data(
        self, openscale_poller: "OpenScalePoller"
    ) -> None:
        """Test that influx_insert handles minimal payload."""
        payload = json.dumps({"date": "2024-01-01T10:00:00Z", "weight": 70.5}).encode()

        with mock.patch("libs.openscale.InfluxDBClient") as mock_client:
            mock_instance = mock.AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance

            await openscale_poller.influx_insert(payload)
            mock_instance.write.assert_called_once()
