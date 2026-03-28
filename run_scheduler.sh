#!/bin/bash
# Shelly Automation scheduler - runs daily at 00:01
# Deployed by deploy.sh

LOCKFILE="/tmp/shelly_scheduler.lock"
APP_DIR="/opt/shelly-automation"

# Check if already running (with stale lock detection)
if [ -e "$LOCKFILE" ]; then
    OLD_PID=$(cat "$LOCKFILE" 2>/dev/null)
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "$(date '+%Y-%m-%d %H:%M:%S'): Scheduler already running (PID $OLD_PID), skipping"
        exit 0
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S'): Removing stale lock file (PID $OLD_PID no longer running)"
        rm -f "$LOCKFILE"
    fi
fi

# Create lock file with PID and cleanup on exit
echo $$ > "$LOCKFILE"
trap "rm -f $LOCKFILE" EXIT

# Go to app directory
cd "$APP_DIR" || exit 1

# Activate venv and schedule today's jobs
# All logging handled by loguru -> logs/shelly_automation.log
source .venv/bin/activate
python schedule_today.py
