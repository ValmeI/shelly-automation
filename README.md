# Shelly Sunrise/Sunset Automation

Local sunrise/sunset automation for Shelly Gen 3 devices.

## Setup

```bash
pip install -r requirements.txt
cp config.yaml.example config.yaml
# Edit config.yaml with your device IP and schedules
python main.py
```

## Maintenance

Run weekly to update times:
```bash
0 1 * * 0 cd /path/to/shelly-automation && python main.py
```
