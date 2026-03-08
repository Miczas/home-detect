# Home Detect Service

Presence detection using:
- nslookup
- ping
- Home Assistant REST API

Turns Innr Zigbee lights on when arriving home.

## Setup

Install dependencies:

pip install -r requirements.txt

Set environment variables:

export HA_TOKEN=your_token

Run:

python3 home_detect.py
