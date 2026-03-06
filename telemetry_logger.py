import argparse
import time
import json
import math
from pymavlink import mavutil

# ==========================================
# UNIT CONVERSIONS (AVIATION)
# ==========================================

FT_PER_M = 3.28084
KT_PER_MPS = 1.94384

def m_to_ft(m):
    return m * FT_PER_M

def mps_to_kt(mps):
    return mps * KT_PER_MPS

def mps_to_fpm(mps):
    return m_to_ft(mps) * 60.0


# ==========================================
# HORIZONTAL DISTANCE (Haversine)
# ==========================================

def compute_horizontal_distance(p1, p2):
    R = 6371000  # meters

    lat1 = math.radians(p1["lat"])
    lon1 = math.radians(p1["lon"])
    lat2 = math.radians(p2["lat"])
    lon2 = math.radians(p2["lon"])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat/2)**2 + \
        math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c


# ==========================================
# MAIN
# ==========================================

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--mcast-ip", required=True, help="Multicast IP")
    parser.add_argument("--port", required=True, help="Multicast Port")
    parser.add_argument("--log-file", default="telemetry_log.json")

    args = parser.parse_args()

    connection_string = f"udpin:{args.mcast_ip}:{args.port}"

    print(f"Connecting to {connection_string}...")
    connection = mavutil.mavlink_connection(connection_string, source_system=255, autoreconnect=True)

    print("Waiting for heartbeat...")
    msg = connection.recv_match(type='HEARTBEAT', blocking=True)
    print("First Heartbeat from SYSID:", msg.get_srcSystem())
    
    
    # Request GLOBAL_POSITION_INT at 10Hz
    connection.mav.command_long_send(
        msg.get_srcSystem(), # target system
        msg.get_srcComponent(), # target component
        mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL,
        0,
        mavutil.mavlink.MAVLINK_MSG_ID_GLOBAL_POSITION_INT,
        100000, # 100ms = 10Hz
        0, 0, 0, 0, 0
    )

    # Request VFR_HUD at 10Hz
    connection.mav.command_long_send(
        msg.get_srcSystem(),
        msg.get_srcComponent(),
        mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL,
        0,
        mavutil.mavlink.MAVLINK_MSG_ID_VFR_HUD,
        100000,
        0, 0, 0, 0, 0
    )


    vehicle_states = {}
    telemetry_log = []

    min_sep_ft = float("inf")
    min_sep_time = None

    try:
        while True:
            msg = connection.recv_match(blocking=True)
            
            if msg:
                print("TYPE:", msg.get_type(), "SYSID:", msg.get_srcSystem())
            if not msg:
                continue

            sysid = msg.get_srcSystem()
            msg_type = msg.get_type()

            vehicle_states.setdefault(sysid, {})
            
            # --------------------------------------------------
            # REQUEST TELEMETRY STREAM WHEN HEARTBEAT RECEIVED
            # --------------------------------------------------

            if msg_type == "HEARTBEAT":
                print(f"Requesting telemetry stream from SYSID {sysid}")

                connection.mav.command_long_send(
                    sysid,
                    msg.get_srcComponent(),
                    mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL,
                    0,
                    mavutil.mavlink.MAVLINK_MSG_ID_GLOBAL_POSITION_INT,
                    100000, # 10 Hz
                    0, 0, 0, 0, 0
                )

                connection.mav.command_long_send(
                    sysid,
                    msg.get_srcComponent(),
                    mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL,
                    0,
                    mavutil.mavlink.MAVLINK_MSG_ID_VFR_HUD,
                    100000, # 10 Hz
                    0, 0, 0, 0, 0
                )


            # ======================================
            # POSITION DATA
            # ======================================
            if msg_type == "GLOBAL_POSITION_INT":
                vehicle_states[sysid]["lat"] = msg.lat / 1e7
                vehicle_states[sysid]["lon"] = msg.lon / 1e7
                vehicle_states[sysid]["alt_m"] = msg.alt / 1000.0
                vehicle_states[sysid]["timestamp"] = time.time()

            # ======================================
            # SPEED + HEADING
            # ======================================
            if msg_type == "VFR_HUD":
                vehicle_states[sysid]["groundspeed_kt"] = msg.groundspeed * 1.94384
                vehicle_states[sysid]["climb_fpm"] = msg.climb * 196.850394
                vehicle_states[sysid]["heading_deg"] = msg.heading

            # ======================================
            # PROCESS ONLY IF SYSID 1 AND 2 EXIST
            # ======================================
            if 1 in vehicle_states and 2 in vehicle_states and "lat" in vehicle_states[1] and "lat" in vehicle_states[2]:

                os = vehicle_states[1]
                tgt = vehicle_states[2]

                required_keys = ["lat", "lon", "alt_m"]

                if all(k in os for k in required_keys) and \
                   all(k in tgt for k in required_keys):

                    # Compute separations
                    horizontal_m = compute_horizontal_distance(os, tgt)
                    vertical_m = abs(os["alt_m"] - tgt["alt_m"])
                    sep3d_m = math.sqrt(horizontal_m**2 + vertical_m**2)

                    # Convert to aviation units
                    horizontal_ft = m_to_ft(horizontal_m)
                    vertical_ft = m_to_ft(vertical_m)
                    sep3d_ft = m_to_ft(sep3d_m)

                    # Track minimum separation
                    if sep3d_ft < min_sep_ft:
                        min_sep_ft = sep3d_ft
                        min_sep_time = time.time()

                    telemetry_log.append({
                        "timestamp": time.time(),

                        "ownship": {
                            "lat": os["lat"],
                            "lon": os["lon"],
                            "alt_ft": m_to_ft(os["alt_m"]),
                            "groundspeed_kt": mps_to_kt(os.get("groundspeed_mps", 0)),
                            "vertical_speed_fpm": mps_to_fpm(os.get("climb_mps", 0)),
                            "heading_deg": os.get("heading_deg", 0)
                        },

                        "target": {
                            "lat": tgt["lat"],
                            "lon": tgt["lon"],
                            "alt_ft": m_to_ft(tgt["alt_m"]),
                            "groundspeed_kt": mps_to_kt(tgt.get("groundspeed_mps", 0)),
                            "vertical_speed_fpm": mps_to_fpm(tgt.get("climb_mps", 0)),
                            "heading_deg": tgt.get("heading_deg", 0)
                        },

                        "horizontal_sep_ft": horizontal_ft,
                        "vertical_sep_ft": vertical_ft,
                        "separation_3d_ft": sep3d_ft
                    })

    except KeyboardInterrupt:

        print("\nStopping logger...")
        print(f"Minimum separation observed: {min_sep_ft:.2f} ft")

        final_output = {
            "minimum_separation_ft": min_sep_ft,
            "minimum_separation_timestamp": min_sep_time,
            "frames": telemetry_log
        }

        with open(args.log_file, "w") as f:
            json.dump(final_output, f, indent=4)

        print(f"Telemetry saved to {args.log_file}")


if __name__ == "__main__":
    main()
    
    