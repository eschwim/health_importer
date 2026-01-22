"""Pytest configuration and fixtures."""

import os

# Set required environment variables before any imports from libs/
# This runs before test collection
os.environ.setdefault("TZ", "UTC")
os.environ.setdefault("INFLUXDB_HOST", "localhost")
os.environ.setdefault("INFLUXDB_PORT", "8086")
os.environ.setdefault("INFLUXDB_USER", "test")
os.environ.setdefault("INFLUXDB_PASS", "test")
os.environ.setdefault("INFLUXDB_DB", "test")
os.environ.setdefault("ENABLE_OURA_POLLER", "False")
os.environ.setdefault("ENABLE_OPENSCALE_POLLER", "False")
