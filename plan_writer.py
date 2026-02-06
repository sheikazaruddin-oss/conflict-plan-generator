import json

def make_waypoint(lat, lon, alt, idx):
    return {
        "AMSLAltAboveTerrain": False,
        "Altitude": alt,
        "AltitudeMode": 1,
        "autoContinue": True,
        "command": 16,
        "doJumpId": idx,
        "frame": 3,
        "params": [0, 0, 0, None, lat, lon, alt],
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
                make_waypoint(waypoints[0][0], waypoints[0][1], waypoints[0][2], 1),
                make_waypoint(waypoints[1][0], waypoints[1][1], waypoints[1][2], 2)
            ],
            "plannedHomePosition": list(home_position),
            "vehicleType": 2,
            "version": 2
        },
        "rallyPoints": {"points": [], "version": 2},
        "version": 1
    }
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)

def write_waypoints_file(path, waypoints):
    """
    Write ArduPilot .waypoints file for QGroundControl (text format).
    Each entry is a standard MAVLink waypoint (command 16).
    """
    with open(path, 'w') as f:
        f.write("QGC WPL 110\n") # Header

        for i, (lat, lon, alt) in enumerate(waypoints):
            current = 1 if i == 0 else 0 # Mark first waypoint as current
            frame = 0 # 0 = MAV_FRAME_GLOBAL
            command = 16 # NAV_WAYPOINT
            param1, param2, param3, param4 = 0, 0, 0, 0
            autocontinue = 1

            f.write(f"{i}\t{current}\t{frame}\t{command}\t")
            f.write(f"{param1}\t{param2}\t{param3}\t{param4}\t")
            f.write(f"{lat:.8f}\t{lon:.8f}\t{alt:.2f}\t{autocontinue}\n")