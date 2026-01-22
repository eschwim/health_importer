#!/usr/bin/env python3

import os
import sys
import zoneinfo

# Fixed constants

AUTHORIZE_URL = "https://cloud.ouraring.com/oauth/authorize"
TOKEN_URL = "https://api.ouraring.com/oauth/token"
API_URL = "https://api.ouraring.com/v2/usercollection"
SCOPES: list[str] = []  # Leave empty to request all scopes by default


def get_env_str(varname: str, default: str | None = None) -> str:
    try:
        return os.environ[varname]
    except KeyError:
        if default is not None:
            return default
        else:
            sys.exit(f"Missing required environment variable: {varname}")


def get_env_int(varname: str, default: str | None = None) -> int:
    try:
        return int(get_env_str(varname, default))
    except ValueError:
        sys.exit(f"variable {varname} must be an integer")


def get_env_bool(varname: str, default: str | None = None) -> bool:
    val = get_env_str(varname, default).lower()
    if val == "true":
        return True
    elif val == "false":
        return False
    else:
        sys.exit(f"variable {varname} must be true/false")


# Process control vars
LOG_LEVEL: str = get_env_str("LOG_LEVEL", "INFO")
ENABLE_OURA_POLLER: bool = get_env_bool("ENABLE_OURA_POLLER", "True")
ENABLE_OPENSCALE_POLLER: bool = get_env_bool("ENABLE_OPENSCALE_POLLER", "True")
TZ = zoneinfo.ZoneInfo(get_env_str("TZ"))

# InfluxDB connection details
INFLUXDB_HOST: str = get_env_str("INFLUXDB_HOST")
INFLUXDB_PORT: int = get_env_int("INFLUXDB_PORT")
INFLUXDB_USER: str = get_env_str("INFLUXDB_USER")
INFLUXDB_PASS: str = get_env_str("INFLUXDB_PASS")
INFLUXDB_DB: str = get_env_str("INFLUXDB_DB")

# Oura API credentials
if ENABLE_OURA_POLLER:
    OURA_CLIENT_ID: str = get_env_str("OURA_CLIENT_ID")
    OURA_CLIENT_SECRET: str = get_env_str("OURA_CLIENT_SECRET")
    REDIRECT_URI: str = get_env_str("REDIRECT_URI")

    # Port our oauth proxy should listen on
    HTTP_PORT = get_env_int("HTTP_PORT", "8080")
    # Path inside our container to write token data to
    TOKEN_FILE: str = get_env_str("TOKEN_FILE", "/cache/tokens")
    # 24H time to run poll for daily metrics
    DAILY_POLL_TIME: str = get_env_str("DAILY_POLL_TIME", "08:00")
    # Amount of random jitter to add to above time
    DAILY_JITTER: int = get_env_int("DAILY_JITTER", "300")

    # How frequently to poll our once-daily data
    DAILY_POLL_INTERVAL: int = get_env_int("DAILY_POLL_INTVL", "3600")

    # How frequently to poll for continuous data (e.g. heartbeat)
    HEARTRATE_POLL_INTVL: int = get_env_int("HEARTRATE_POLL_INTVL", "60")
    ACTIVITY_POLL_INTVL: int = get_env_int("ACTIVITY_POLL_INTVL", "1800")
    WORKOUT_POLL_INTVL: int = get_env_int("WORKOUT_POLL_INTVL", "1800")
    ENHANCED_TAG_POLL_INTVL: int = get_env_int("ENHANCED_TAG_POLL_INTVL", "600")
    SLEEP_POLL_INTVL: int = get_env_int("SLEEP_POLL_INTVL", "1800")

    # Amount to subtract from "start" value when polling continuous data;  adjust
    # upwards if you see missing values between polling periods
    POLL_FUZZ: int = get_env_int("POLL_FUZZ", "86400")
    STARTUP_LOOKBACK: int = get_env_int("STARTUP_LOOKBACK", "7")

# Openscale MQTT params
if ENABLE_OPENSCALE_POLLER:
    OPENSCALE_MQTT_HOST: str = get_env_str("OPENSCALE_MQTT_HOST")
    OPENSCALE_MQTT_PORT: int = get_env_int("OPENSCALE_MQTT_PORT")
    OPENSCALE_MQTT_TOPIC: str = get_env_str("OPENSCALE_MQTT_TOPIC", "openScaleSync")
