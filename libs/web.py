#!/usr/bin/env python3

import asyncio
import json
import logging
import time
from urllib.parse import urlencode

from aiohttp import ClientSession, FormData, web

from . import constants


class OAuthFetchWebServer:
    """
    A very bare-bones web service that will fetch oauth tokens from the
    oura auth service (requires the user to click the link on the web
    page at least once) and then refreshes them periodically as they age.

    _Ideally_ we would be using webhooks/callbacks, since that is what
    Oura wants us to do (reduces continuous poll load on their side).
    Unfortunately this isn't an option for us that are running a
    privately hosted service, so we have to fall back to polling.
    """

    def __init__(self, token_cfg: dict[str, str | int]) -> None:
        self.client_id = constants.OURA_CLIENT_ID
        self.client_secret = constants.OURA_CLIENT_SECRET
        self.redirect_uri = constants.REDIRECT_URI
        self.auth_params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
        }
        if constants.SCOPES:
            self.auth_params["scope"] = " ".join(constants.SCOPES)
        self.token_cfg = token_cfg

    def _write_token_file(self) -> None:
        """Write token configuration to file (blocking, run via to_thread)."""
        with open(constants.TOKEN_FILE, "w") as f:
            json.dump(self.token_cfg, f)

    def _read_token_file(self) -> dict[str, str | int]:
        """Read token configuration from file (blocking, run via to_thread)."""
        with open(constants.TOKEN_FILE) as f:
            data: dict[str, str | int] = json.load(f)
            return data

    async def handle_get(self, request: web.Request) -> web.Response:
        """
        Our ugly, but effective, web page to allow users to request
        and oura token.
        """
        auth_url = f"{constants.AUTHORIZE_URL}?{urlencode(self.auth_params)}"
        try:
            token_result = await self.fetch_token(request.query.get("code"))
        except Exception as e:
            token_result = f"Error fetching access token: {e}"

        return web.Response(
            text=f"""
                {token_result}
                <br>
                <a href="{auth_url}">Click to authorize</a>
            """,
            content_type="text/html",
        )

    async def fetch_token(self, code: str | None) -> str:
        """
        Interstitial to catch the response if/when user returns from oauth
        portal
        """
        if code is None:
            return "No authorization code found; please click link below"

        logging.info(f"Fetching access token w/ code: {code}")

        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
        }

        await self.download_tokens(token_data)

        logging.info("Token downloaded")
        return "Tokens successfully fetched!"

    async def download_tokens(self, params: dict[str, str]) -> None:
        """
        Code to actually forward the user on to the Oura oauth portal
        and process the callback when they return to this our web page
        """
        async with ClientSession() as session:
            post_data = FormData(fields=params)
            async with session.post(constants.TOKEN_URL, data=post_data) as resp:
                response = await resp.json()
                assert (
                    "access_token" in response
                ), f"No access token received: {response}"

                self.token_cfg.update(await resp.json())
                self.token_cfg["last_updated"] = int(time.time())
                await asyncio.to_thread(self._write_token_file)

        logging.info(f"Successfully wrote tokens to '{constants.TOKEN_FILE}'")

    async def refresh_worker(self) -> None:
        """
        Oauth tokens periodically expire;  this method launches as a background
        task and refreshes them when they get to age/2 seconds;  since the token
        TTLs are currently 86400 this gives us plenty of wiggle room.
        """

        while True:
            if not self.token_cfg:
                logging.info("No token configuration found, loading from file")
                try:
                    token_data = await asyncio.to_thread(self._read_token_file)
                    self.token_cfg.update(token_data)
                except FileNotFoundError:
                    logging.error(f"Token file {constants.TOKEN_FILE} not found")
                    await asyncio.sleep(60)
                    continue
                except json.JSONDecodeError:
                    logging.error(
                        f"Error decoding JSON from token file {constants.TOKEN_FILE}"
                    )
                    await asyncio.sleep(60)
                    continue

            token_ttl = self.token_cfg["expires_in"]
            last_updated = self.token_cfg.get("last_updated", 0)
            assert isinstance(
                last_updated, int
            ), "last_updated must be an integer timestamp"
            assert isinstance(token_ttl, int), "expires_in must be an integer"
            expires_at = last_updated + token_ttl
            time_remaining = int(expires_at - time.time())

            if time_remaining > token_ttl // 2:
                logging.debug(f"Access token expires in {time_remaining}s")
                await asyncio.sleep(60)
                continue

            logging.info(f"Access token expires in {time_remaining}s, refreshing...")
            try:
                refresh_params: dict[str, str] = {
                    "grant_type": "refresh_token",
                    "refresh_token": str(self.token_cfg["refresh_token"]),
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                }

                await self.download_tokens(refresh_params)
            except Exception as e:
                logging.error(f"Error when resfreshing token: {e}")

    async def start(self) -> None:
        """
        Fire ze missiles!  Start the web server and token refresh worker, and
        then return.
        """
        logging.info("Starting http server")
        app = web.Application()
        app.add_routes([web.get("/", self.handle_get)])
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", int(constants.HTTP_PORT))
        await site.start()
        asyncio.create_task(self.refresh_worker())
