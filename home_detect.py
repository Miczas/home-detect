import requests
import subprocess
import time
import logging
import os
from datetime import datetime
from dotenv import load_dotenv

# ----------------------------
# Logging setup
# ----------------------------
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("/home/michal/homeDetect.log"), logging.StreamHandler()]
)

# ----------------------------
# Home Assistant settings
# ----------------------------
HA_BASE = os.getenv("HA_BASE", "http://localhost:8123")
TOKEN = os.getenv("HA_TOKEN")

# The entity_id of your light
LIGHTS = [
    "light.hallwaylights"
]

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}

# ----------------------------
# User Configuration
# ----------------------------
USERS = {
    "Pixel-6-Pro": {
        "color": (255, 191, 13),
        "brightness": 200,
    },
}

ABSENCE_THRESHOLD = 10  # minutes before considered truly gone
absence_timers = {user: None for user in USERS}  # tracks when they first went missing
# ----------------------------
# Function to turn all lights ON
# ----------------------------
def turn_all_on(**kwargs):
    url = f"{HA_BASE}/api/services/light/turn_on"

    for light in LIGHTS:
        payload = {"entity_id": light}
        payload.update(kwargs)

        try:
            r = requests.post(url, headers=HEADERS, json=payload, timeout=(1, 2))
            r.raise_for_status()
            logging.info(f"{light} turned ON with {kwargs}")
        except requests.exceptions.Timeout:
            logging.warning(f"Timeout turning ON {light}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error turning ON {light}: {e}")
  # ----------------------------
# Function to turn all lights OFF
# ----------------------------
def turn_all_off():
    for light in LIGHTS:
        url = f"{HA_BASE}/api/services/light/turn_off"
        payload = {"entity_id": light}
        try:
            r = requests.post(url, headers=HEADERS, json=payload, timeout=(1, 2))
            r.raise_for_status()
            logging.info(f"{light} turned OFF")
        except requests.exceptions.Timeout:
            logging.warning(f"Timeout turning OFF {light}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error turning OFF {light}: {e}") 


def is_home(hostname_or_ip, retries=5):
    """
    Check if a device is reachable via ping.
    Returns True immediately on first success, otherwise retries up to 5 times.
    """
    for attempt in range(1, retries + 1):
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "1", hostname_or_ip],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            if result.returncode == 0:
                return True  # success — return immediately
            logging.debug(f"Ping attempt {attempt}/{retries} failed for {hostname_or_ip}")
        except Exception as e:
            logging.error(f"Error pinging {hostname_or_ip} (attempt {attempt}): {e}")

    return False  # all attempts exhausted
# ----------------------------
# Main: toggle all lights
# ----------------------------
def main():
    user_states = {user: True for user in USERS}
    last_seen = {user: time.time() for user in USERS}

    logging.info("Home detection service started")

    while True:
        try:
            anyone_home = True
            now = datetime.now()

            for user, settings in USERS.items():
                currently_home = is_home(user)
                previously_home = user_states[user]

                if currently_home:
                    # Reset absence timer whenever we see them
                    absence_timers[user] = None

                    # User just arrived (was marked as gone)
                    if not previously_home:
                        logging.info(f"{user} arrived → turning lights ON")
                        turn_all_on(
                            brightness=settings["brightness"],
                            rgb_color=settings["color"],
                            transition=2,
                        )
                    user_states[user] = True

                else:
                    # Not detected — start or check absence timer
                    if absence_timers[user] is None:
                        # First missed ping — start the clock
                        absence_timers[user] = now
                        logging.debug(f"{user} missed ping, starting absence timer")

                    minutes_gone = (now - absence_timers[user]).total_seconds() / 60

                    if minutes_gone >= ABSENCE_THRESHOLD:
                        # Only mark as gone after 20 minutes of no pings
                        if previously_home:
                            logging.info(f"{user} gone for {ABSENCE_THRESHOLD}min → marking absent")
                        user_states[user] = False
                    else:
                        # Still within grace period — treat as home
                        logging.debug(f"{user} absent for {minutes_gone:.1f}min, within grace period")
                        user_states[user] = True  # keep them as "home" during grace period

                if user_states[user]:
                    anyone_home = True

            if not anyone_home:
                logging.info("Nobody home → turning lights OFF")
                turn_all_off()

            if any(not state for state in user_states.values()):
                time.sleep(2)
            else:
                time.sleep(60)

        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            time.sleep(5)
# ----------------------------
# Proper Python entry point
# ----------------------------
if __name__ == "__main__":
    main()

   
