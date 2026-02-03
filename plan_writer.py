import json

def make_waypoint(lat, lon, alt, idx):
    return {
        "AMSLAltAboveTerrain": None,
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
                make_waypoint(*waypoints[0], 1),
                make_waypoint(*waypoints[1], 2),
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