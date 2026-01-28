# Shelly Sunrise/Sunset Automation

Local sunrise/sunset automation for Shelly Gen 3 devices.

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your settings

# Run
python setup_sunrise_sunset.py
```

## Configuration (.env)

```bash
SHELLY_IP=192.168.50.191
SWITCH_ID=0
LATITUDE=59.437
LONGITUDE=24.7536
TIMEZONE=Europe/Tallinn
SUNRISE_OFFSET=0          # Minutes: + after, - before
ENABLE_SUNSET_AUTOMATION=true
LOG_LEVEL=INFO
LOG_FILE=logs/shelly_automation.log
```

All fields required.

## What it does

Creates 2 recurring daily schedules:
- Turn lights OFF at sunrise + offset
- Turn lights ON at sunset (if enabled)

Schedules drift ~2min/day. Run weekly/monthly to update:

```bash
# Weekly cron (Sundays at 1am)
0 1 * * 0 cd /path/to/shelly-automation && .venv/bin/python setup_sunrise_sunset.py
```

## Verify

```bash
curl http://192.168.50.191/rpc/Schedule.List
```
