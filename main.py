#!/usr/bin/env python3

import asyncio
import logging

import libs.constants as constants
from libs.openscale import OpenScalePoller
from libs.oura import OuraPoller
from libs.web import OAuthFetchWebServer


async def main() -> None:
    logging.basicConfig(
        format="[%(asctime)s][%(levelname)s] %(message)s",
        datefmt="%y%m%d@%I:%M:%S",
        level=getattr(logging, constants.LOG_LEVEL, logging.INFO),
    )

    if constants.ENABLE_OURA_POLLER:
        token_cfg: dict[str, str | int] = {}
        oath_fetch_web_server = OAuthFetchWebServer(token_cfg)
        await oath_fetch_web_server.start()

        oura_poller = OuraPoller(token_cfg)
        await oura_poller.start()

    if constants.ENABLE_OPENSCALE_POLLER:
        openscale_poller = OpenScalePoller()
        await openscale_poller.start()

    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
