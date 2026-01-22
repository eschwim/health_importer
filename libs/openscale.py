#!/usr/bin/env python3

import asyncio
import json
import logging

import aiomqtt
from aioinflux import InfluxDBClient

from . import constants

Tags = dict[str, str]
Fields = dict[str, int | float | str]
Point = dict[str, str | Tags | Fields]


class OpenScalePoller:
    """
    Quick and dirty poller that takes data uploaded to an MQTT topic
    from openScale (https://github.com/oliexdev/openScale ; you need
    the "openScale sync" app to make this happe) and forwards it
    to an influxdb meaurement.
    """

    async def poller(self) -> None:
        """
        Do a blocking read on the MQTT topic using a wildcard path, and then
        insert data into the influxdb measurement as it is read.

        NB:  openScale sync currently supports a delete topic, which we do
        not support here.  So any data that is deleted in the app will actually
        not be deleted here.
        """

        topic = f"{constants.OPENSCALE_MQTT_TOPIC}/#"
        logging.info(
            f"Connecting to openscale MQTT {constants.OPENSCALE_MQTT_HOST}"
            f":{constants.OPENSCALE_MQTT_PORT}, using topic '{topic}'"
        )
        async with aiomqtt.Client(
            hostname=constants.OPENSCALE_MQTT_HOST,
            port=constants.OPENSCALE_MQTT_PORT,
        ) as client:
            await client.subscribe(topic)
            async for message in client.messages:
                await self.influx_insert(message.payload)

    async def influx_insert(self, payload: bytes) -> None:
        """
        What it says on the tin.  Inserts into influx.
        """

        input_str = payload.decode()
        logging.debug(f"Will try to insert {input_str}")

        inputs = json.loads(input_str)

        point: Point = {
            "measurement": "scale_metrics",
            "tags": {},
            "time": inputs.pop("date"),
            "fields": inputs,
        }

        async with InfluxDBClient(
            host=constants.INFLUXDB_HOST,
            port=constants.INFLUXDB_PORT,
            username=constants.INFLUXDB_USER,
            password=constants.INFLUXDB_PASS,
            database=constants.INFLUXDB_DB,
        ) as client:
            await client.write(point)

        logging.debug("Inserted openscale data into scale_metrics")

    async def start(self) -> None:
        """
        Start the poller worker and then returns
        """
        logging.info("Starting openscale MQTT poller")
        asyncio.create_task(self.poller())
