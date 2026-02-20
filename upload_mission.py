from pymavlink import mavutil
from pathlib import Path
import time

BASE_DIR = Path(__file__).resolve().parent

def upload(port, filename):
    m = mavutil.mavlink_connection(port)
    m.wait_heartbeat()
    time.sleep(1)

    m.waypoint_clear_all_send()
    time.sleep(1)

    m.waypoint_load(str(BASE_DIR / filename))
    time.sleep(1)

    m.waypoint_set_current_send(0)
    print(f"Uploaded {filename}")

upload("udp:127.0.0.1:14550", "ownership.waypoints")
upload("udp:127.0.0.1:14551", "target.waypoints")
