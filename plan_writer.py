import json

def make_waypoint(lat, lon, alt, idx):
    return {
        "AMSLAltAboveTerrain": 0.0,  # ✅ ADDED (must be Double)
        "Altitude": alt,
        "AltitudeMode": 1,
        "autoContinue": True,
        "command": 16,              # NAV_WAYPOINT
        "doJumpId": idx,
        "frame": 3,
        "params": [0, 0, 0, 0, lat, lon, alt],  # param4 must NOT be None
        "type": "SimpleItem"
    }

# ✅ ADDED: Takeoff item (new function, no existing function changed)
def make_takeoff(alt, idx):
    return {
        "AMSLAltAboveTerrain": 0.0,
        "Altitude": alt,
        "AltitudeMode": 1,
        "autoContinue": True,
        "command": 22,              # MAV_CMD_NAV_TAKEOFF
        "doJumpId": idx,
        "frame": 0,
        "params": [0, 0, 0, 0, 0, 0, alt],
        "type": "SimpleItem"
    }

def write_plan_file(path, waypoints, home_position):
    data = {
        "fileType": "Plan",
        "geoFence": {"circles": [], "polygons": [], "version": 2},
        "groundStation": "QGroundControl",
        "mission": {
            "cruiseSpeed": 15,
            "firmwareType": 12,
            "hoverSpeed": 5,
            "items": [
                # ✅ ADDED: Takeoff must be FIRST
                make_takeoff(waypoints[0][2], 0),

                # Existing waypoints (unchanged)
                make_waypoint(waypoints[0][0], waypoints[0][1], waypoints[0][2], 1),
                make_waypoint(waypoints[1][0], waypoints[1][1], waypoints[1][2], 2),
            ],
            "plannedHomePosition": list(home_position),
            "vehicleType": 2,
            "version": 2
        },
        "rallyPoints": {"points": [], "version": 2},
        "version": 1
    }

    with open(path, "w") as f:
        json.dump(data, f, indent=4)

def write_waypoints_file(path, waypoints):
    """
    Write ArduPilot .waypoints file for QGroundControl (text format).
    Each entry is a standard MAVLink waypoint.
    """
    with open(path, "w") as f:
        f.write("QGC WPL 110\n")

        # ✅ ADDED: TAKEOFF command (index 0)
        f.write(
            f"0\t1\t0\t22\t0\t0\t0\t0\t0\t0\t{waypoints[0][2]:.2f}\t1\n"
        )

        for i, (lat, lon, alt) in enumerate(waypoints, start=1):
            current = 1 if i == 1 else 0
            frame = 0
            command = 16
            param1 = param2 = param3 = param4 = 0
            autocontinue = 1

            f.write(
                f"{i}\t{current}\t{frame}\t{command}\t"
                f"{param1}\t{param2}\t{param3}\t{param4}\t"
                f"{lat:.8f}\t{lon:.8f}\t{alt:.2f}\t{autocontinue}\n"
            )