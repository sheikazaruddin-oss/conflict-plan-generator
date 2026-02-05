import json
import os

def write_plan_file(filename, wp1, wp2, vehicle_id="Generic"):
    plan = {
        "fileType": "Plan",
        "geoFence": {"circles": [], "polygons": [], "version": 2},
        "groundStation": "QGroundControl",
        "mission": {
            "cruiseSpeed": 15,
            "firmwareType": 12,
            "hoverSpeed": 5,
            "items": [
                {
                    "AMSLAltAboveTerrain": None,
                    "Altitude": wp1[2],
                    "AltitudeMode": 1,
                    "autoContinue": True,
                    "command": 16,
                    "doJumpId": 1,
                    "frame": 3,
                    "params": [0, 0, 0, None, wp1[0], wp1[1], wp1[2]],
                    "type": "SimpleItem"
                },
                {
                    "AMSLAltAboveTerrain": None,
                    "Altitude": wp2[2],
                    "AltitudeMode": 1,
                    "autoContinue": True,
                    "command": 16,
                    "doJumpId": 2,
                    "frame": 3,
                    "params": [0, 0, 0, None, wp2[0], wp2[1], wp2[2]],
                    "type": "SimpleItem"
                }
            ],
            "plannedHomePosition": [wp1[0], wp1[1], wp1[2]],
            "vehicleType": 2,
            "version": 2
        },
        "rallyPoints": {"points": [], "version": 2},
        "version": 1
    }

    with open(filename, 'w') as f:
        json.dump(plan, f, indent=4)

def write_waypoint_file(filename, wp1, wp2):
    lines = [
        "QGC WPL 110",
        f"0\t1\t0\t16\t0\t0\t0\t0\t{wp1[0]}\t{wp1[1]}\t{wp1[2]}\t1",
        f"1\t0\t0\t16\t0\t0\t0\t0\t{wp2[0]}\t{wp2[1]}\t{wp2[2]}\t1"
    ]
    with open(filename, 'w') as f:
        f.write('\n'.join(lines))