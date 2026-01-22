# Health Importer

A Python async service that aggregates health metrics from multiple sources and stores them in InfluxDB for time-series analysis and visualization.

## Supported Data Sources

- **Oura Ring** - Polls the Oura Ring v2 API for heart rate, sleep, activity, workouts, daily readiness, stress, SpO2, and more
- **OpenScale** - Receives weight and body composition data via MQTT from [openScale](https://github.com/oliexdev/openScale) (requires [openScale sync](https://github.com/AnyTimeTraveler/openScale-sync))

## Prerequisites

- Python 3.10+
- InfluxDB instance
- Oura Ring with API access (requires creating an application at [Oura Developer Portal](https://cloud.ouraring.com/oauth/applications))
- MQTT broker (for OpenScale integration)

## Installation

```bash
git clone <repository-url>
cd health_importer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Copy and edit the environment variables file:

```bash
cp envvars.example envvars.local
# Edit envvars.local with your values
```

### Required Environment Variables

| Variable | Description |
|----------|-------------|
| `TZ` | Timezone (e.g., `PST8PDT`, `America/Los_Angeles`) |
| `INFLUXDB_HOST` | InfluxDB hostname |
| `INFLUXDB_PORT` | InfluxDB port |
| `INFLUXDB_USER` | InfluxDB username |
| `INFLUXDB_PASS` | InfluxDB password |
| `INFLUXDB_DB` | InfluxDB database name |

### Oura Ring Configuration

Required when `ENABLE_OURA_POLLER=True`:

| Variable | Description |
|----------|-------------|
| `OURA_CLIENT_ID` | OAuth client ID from Oura Developer Portal |
| `OURA_CLIENT_SECRET` | OAuth client secret |
| `REDIRECT_URI` | OAuth callback URL (e.g., `http://localhost:8080/`) |

Optional Oura settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `TOKEN_FILE` | `/cache/tokens` | Path to store OAuth tokens |
| `HTTP_PORT` | `8080` | Port for OAuth web server |
| `STARTUP_LOOKBACK` | `7` | Days of historical data to fetch on startup |
| `HEARTRATE_POLL_INTVL` | `60` | Heart rate polling interval (seconds) |
| `SLEEP_POLL_INTVL` | `1800` | Sleep data polling interval (seconds) |
| `WORKOUT_POLL_INTVL` | `1800` | Workout polling interval (seconds) |
| `DAILY_POLL_INTVL` | `3600` | Daily metrics polling interval (seconds) |
| `POLL_FUZZ` | `86400` | Overlap window to avoid missing data (seconds) |

### OpenScale Configuration

Required when `ENABLE_OPENSCALE_POLLER=True`:

| Variable | Description |
|----------|-------------|
| `OPENSCALE_MQTT_HOST` | MQTT broker hostname |
| `OPENSCALE_MQTT_PORT` | MQTT broker port |
| `OPENSCALE_MQTT_TOPIC` | MQTT topic (default: `openScaleSync`) |

### Feature Toggles

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_OURA_POLLER` | `True` | Enable Oura Ring integration |
| `ENABLE_OPENSCALE_POLLER` | `True` | Enable OpenScale integration |
| `LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

## Usage

### Local

```bash
source .venv/bin/activate
set -a && source envvars.local && set +a
python3 main.py
```

### Docker

```bash
docker compose up -d
```

On first run with Oura integration enabled, visit `http://localhost:8080` (or your configured port) and click the authorization link to complete OAuth setup. Tokens are persisted and automatically refreshed.

## InfluxDB Measurements

Data is written to the following InfluxDB measurements:

**Oura Ring:**
- `heartrate` - Continuous heart rate data
- `sleep` - Sleep sessions with stages and metrics
- `workout` - Exercise sessions
- `daily_activity`, `daily_readiness`, `daily_sleep`, `daily_stress`, `daily_spo2`, `daily_resilience`, `daily_cardiovascular_age`
- `enhanced_tag` - User-created tags
- `vO2_max`, `sleep_time`

**OpenScale:**
- `scale_metrics` - Weight and body composition data

## Grafana Dashboard

A sample Grafana dashboard configuration is included in `extra/grafana_dashboard.json`. Import it into your Grafana instance to visualize the collected health metrics.
