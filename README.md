# Shelly Automation

Homelab-based sunrise/sunset light control for Shelly devices.

## Architecture

```
Homelab Server → Cron (00:01 daily) → schedule_today.py → atd → switch_control.py → Shelly API
```

**How it works:**
1. Daily at 00:01, cron schedules 3 `at` jobs for today's times
2. At each time, `switch_control.py` sends Switch.Set API call to device
3. Retry logic ensures reliable switching (3 attempts with verification)

## Deployment

Deploy via homelab repo:

```bash
cd ~/git/homelab
./deploy.sh -s shelly
```

## Configuration

Edit `config.yaml` in this repo, then redeploy:

```yaml
shelly_ip: 192.168.50.191
latitude: 59.437
longitude: 24.7536
timezone: Europe/Tallinn

schedules:
  - time: "06:40"
    action: "on"
  - time: sunrise
    offset: 0
    action: "off"
  - time: sunset
    offset: 15      # 15 min AFTER sunset (negative = before)
    action: "on"
```

## Monitoring

```bash
ssh homelab.local
atq                          # Check scheduled jobs
tail -f /opt/shelly-automation/logs/scheduler.log

# Manual test
cd /opt/shelly-automation && source .venv/bin/activate && python switch_control.py on
```
