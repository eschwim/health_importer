#!/usr/bin/env python3

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from aiohttp import ClientSession
from aioinflux import InfluxDBClient

from . import constants

Tags = dict[str, str]
Fields = dict[str, int | float | str]
Point = dict[str, str | Tags | Fields]

# List of endpoints that use the datetime parameter instead of date
DATETIME_ENDPOINTS: tuple[str, ...] = ("heartrate",)


class OuraPoller:
    """
    Class to continuously poll the Oura Ring v2 API; massage the data
    into an appropriate format, and then cram it into an influxdb
    instance
    """
    def __init__(self, token_cfg: dict[str, str | int]) -> None:
        self.token_cfg = token_cfg

    @property
    def now(self) -> datetime:
        return datetime.now(tz=constants.TZ)

    async def handle_data(
        self,
        measurement: str,
        inputs: list[Fields] | Fields,
    ) -> None:
        data: list[Fields] = inputs if isinstance(inputs, list) else [inputs]

        if not data:
            logging.debug(f"Got no data for measurement '{measurement}'")
            return

        for datum in data:
            # Filter bad/weird data
            if not isinstance(datum, dict):
                logging.debug(
                    f"Got non-dict datum for measurement {measurement}: {datum}"
                )
                continue

            timestamp = datum.get("day", None) or datum.get("timestamp", None)
            if not timestamp:
                logging.debug(
                    f"No timestamp found for measurement {measurement}: {datum}"
                )
                continue

            # Validate data; process sub-objects if possible
            # Use ugly iterator here since we modify the dict
            for key in list(datum.keys()):
                val = datum[key]

                # Pass over simple values
                if any(
                    [isinstance(val, int), isinstance(val, str), isinstance(val, float)]
                ):
                    continue

                # Handle more complex values / sub-objects
                del datum[key]
                this: list[dict[str, Any]] = []

                if isinstance(val, dict):
                    # Handle SampleModel objects
                    if not {"interval", "items", "timestamp"} - set(val):
                        ts = datetime.fromisoformat(val["timestamp"])
                        intvl = int(val["interval"])
                        this = [
                            {
                                key: item,
                                "timestamp": (
                                    ts + timedelta(seconds=i * intvl)
                                ).isoformat(),
                            }
                            for i, item in enumerate(val["items"])
                            if item is not None
                        ]
                    # Handle bare dict sub-objects (with or without timestamps)
                    else:
                        # Add a timestamp if we don't have one
                        this = [{"timestamp": timestamp} | val]

                # Handle lists of dict sub-objects
                elif isinstance(val, list):
                    if val and isinstance(val[0], dict):
                        this = [{"timestamp": timestamp} | v for v in val]

                elif val is None:
                    pass

                # Weird data; skip it
                else:
                    logging.warning(
                        f"Got non-handleable type for measurement {measurement}, "
                        f"key {key}: {val}"
                    )

                if this:
                    await self.handle_data(f"{measurement}_{key}", this)

        await self.influxdb_insert(measurement, data)

    async def influxdb_insert(
        self,
        measurement: str,
        data: list[Fields],
    ) -> None:
        points: list[dict[str, Any]] = [
            {
                "measurement": measurement,
                "tags": {},
                "time": datum.pop("day", None) or datum.pop("timestamp", None),
                "fields": datum,
            }
            for datum in data
        ]

        async with InfluxDBClient(
            host=constants.INFLUXDB_HOST,
            port=constants.INFLUXDB_PORT,
            username=constants.INFLUXDB_USER,
            password=constants.INFLUXDB_PASS,
            database=constants.INFLUXDB_DB,
        ) as client:
            await client.write(points)

        logging.debug(f"Inserted {len(points)} point(s) to '{measurement}'")

    async def call_oura_api(self, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        """
        Make the actual call to our Oura v2 API
        """

        token = ""
        while not token:
            token = str(self.token_cfg.get("access_token", ""))
            if not token:
                logging.debug("No access token found; cannot call API")
                await asyncio.sleep(10)

        url: str = f"{constants.API_URL}/{endpoint}"
        headers: dict[str, str] = {"Authorization": f"Bearer {token}"}

        async with ClientSession() as session:
            async with session.get(url, headers=headers, params=kwargs) as resp:
                result: dict[str, Any] = await resp.json()
                return result

    async def poller(self, endpoint: str, poll_interval: int) -> None:
        """
        Infinite loop that pools a specific Oura API periodically, and
        then forwards the returned data on to our data handler
        """
        logging.debug(f"Starting poller for '{endpoint}' endpoint")

        start_time: datetime = datetime.now(tz=constants.TZ) - timedelta(
            days=constants.STARTUP_LOOKBACK
        )

        while True:
            end_time = self.now
            try:
                query_params = {"endpoint": endpoint}
                if endpoint in DATETIME_ENDPOINTS:
                    query_params["start_datetime"] = start_time.isoformat()
                    query_params["end_datetime"] = end_time.isoformat()
                else:
                    query_params["start_date"] = start_time.date().isoformat()
                    query_params["end_date"] = end_time.date().isoformat()

                logging.debug(f"Polling endpoints '{endpoint}' from {start_time} to {end_time}")
                result = await self.call_oura_api(**query_params)
                await self.handle_data(measurement=endpoint, inputs=result["data"])
            except Exception:
                logging.exception(f"{endpoint} poller exception")
                await asyncio.sleep(60)
                continue

            await asyncio.sleep(poll_interval - (self.now - end_time).total_seconds())

            # Note the fuzzing, here.  When polling windows that were too small
            # (e.g. 60 seconds or less), we would often see 0 datapoints returned.
            # Hence we make the window much larger, and then fall back to influxdb
            # doing transparent upserts to dedupe our data
            start_time = end_time - timedelta(seconds=constants.POLL_FUZZ)

    def create_poller(self, endpoint: str, interval: int) -> None:
        """
        Convenience method to create a poller
        """
        asyncio.create_task(self.poller(endpoint, interval))

    def create_daily_poller(self, endpoint: str) -> None:
        """
        Convenience method to create a poller using the fixed-interval daily poll
        """
        asyncio.create_task(self.poller(endpoint, constants.DAILY_POLL_INTERVAL))

    async def start(self) -> None:
        """
        Start all of our poll workers in the background and then return
        """
        logging.info(
            f"Starting Oura pollers; lookback period is {constants.STARTUP_LOOKBACK} days"
        )

        self.create_poller("heartrate", constants.HEARTRATE_POLL_INTVL)
        self.create_poller("enhanced_tag", constants.ENHANCED_TAG_POLL_INTVL)
        self.create_poller("workout", constants.WORKOUT_POLL_INTVL)
        self.create_poller("sleep", constants.SLEEP_POLL_INTVL)

        self.create_daily_poller("daily_activity")
        self.create_daily_poller("daily_cardiovascular_age")
        self.create_daily_poller("daily_readiness")
        self.create_daily_poller("daily_resilience")
        self.create_daily_poller("daily_sleep")
        self.create_daily_poller("daily_spo2")
        self.create_daily_poller("daily_stress")
        self.create_daily_poller("sleep_time")
        self.create_daily_poller("vO2_max")
