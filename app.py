import argparse

from conflict_math import compute_conflict_geometry, compute_initial_positions_type2
from plan_writer import (
    write_plan_file,
    write_waypoints_file,
    write_kml_file,
    write_combined_kml_file
)
from yaml_writer import write_yaml_file
from units import ft_to_m, m_to_ft, kt_to_mps, mps_to_kt, fpm_to_mps

def mmss_to_sec(mmss):
    m, s = mmss.split(":")
    return int(m) * 60 + int(s)

# =========================================================
# ARGUMENTS
# =========================================================

parser = argparse.ArgumentParser()

parser.add_argument("--mode", default="type1")

parser.add_argument("--os_callsign", default="OWN01")
parser.add_argument("--tgt_callsign", default="TGT01")

parser.add_argument("--tcpa", default="01:00")
parser.add_argument("--post_cpa", default="10:00")

parser.add_argument("--cpa", type=float, default=20)

parser.add_argument("--os_lat", type=float)
parser.add_argument("--os_lon", type=float)

parser.add_argument("--os_alt", type=float, default=50)
parser.add_argument("--os_course", type=float, default=90)
parser.add_argument("--os_speed", type=float, default=20)
parser.add_argument("--os_vspeed", type=float, default=1)

parser.add_argument("--rel_speed", type=float, default=10)

# ✅ NEW (only addition)
parser.add_argument("--tgt_speed", type=float, default=None)

parser.add_argument("--conflict_dh", type=float, default=30)
parser.add_argument("--tgt_alto", type=float, default=20)
parser.add_argument("--relative_heading", type=float, default=95)

# TYPE 2 INPUTS
parser.add_argument("--os_start_lat", type=float)
parser.add_argument("--os_start_lon", type=float)
parser.add_argument("--os_end_lat", type=float)
parser.add_argument("--os_end_lon", type=float)

parser.add_argument("--tgt_start_lat", type=float)
parser.add_argument("--tgt_start_lon", type=float)
parser.add_argument("--tgt_end_lat", type=float)
parser.add_argument("--tgt_end_lon", type=float)

parser.add_argument("--cpa_lat", type=float)
parser.add_argument("--cpa_lon", type=float)

args = parser.parse_args()

# =========================================================
# CONVERSIONS
# =========================================================

tcpa_sec = mmss_to_sec(args.tcpa)
post_cpa_sec = mmss_to_sec(args.post_cpa)

# =========================================================
# TYPE SWITCH
# =========================================================

if args.mode == "type1":

    points = compute_conflict_geometry(
        tcpa_sec=tcpa_sec,
        cpa_horiz_m=ft_to_m(args.cpa),
        os_lat_deg=args.os_lat,
        os_lon_deg=args.os_lon,
        os_alt_m=ft_to_m(args.os_alt),
        os_course_deg=args.os_course,
        os_speed_mps=kt_to_mps(args.os_speed),
        os_vspeed_mps=fpm_to_mps(args.os_vspeed),
        rel_speed_mps=kt_to_mps(args.rel_speed),
        conflict_dh_m=ft_to_m(args.conflict_dh),
        target_alto_m=ft_to_m(args.tgt_alto),
        relative_heading_deg=args.relative_heading,
        post_cpa_sec=post_cpa_sec
    )

else:

    init_t2 = compute_initial_positions_type2(
        tcpa_sec=tcpa_sec,
        cpa_lat=args.cpa_lat,
        cpa_lon=args.cpa_lon,
        os_s_lat=args.os_start_lat,
        os_s_lon=args.os_start_lon,
        os_e_lat=args.os_end_lat,
        os_e_lon=args.os_end_lon,
        tgt_s_lat=args.tgt_start_lat,
        tgt_s_lon=args.tgt_start_lon,
        tgt_e_lat=args.tgt_end_lat,
        tgt_e_lon=args.tgt_end_lon,
        os_speed_mps=kt_to_mps(args.os_speed),
        tgt_speed_mps=kt_to_mps(args.tgt_speed if args.tgt_speed is not None else args.os_speed + args.rel_speed)
    )

    os_course = init_t2["os_course_deg"]
    tgt_course = init_t2["tgt_course_deg"]

    relative_heading = (tgt_course - os_course + 360.0) % 360.0

    # ✅ FIXED: uses tgt_speed instead of rel_speed
    rel_speed_mps = kt_to_mps(
        (args.tgt_speed - args.os_speed)
        if args.tgt_speed is not None
        else args.rel_speed
    )

    points = compute_conflict_geometry(
        tcpa_sec=tcpa_sec,
        cpa_horiz_m=0.0,
        os_lat_deg=init_t2["os_init"][0],
        os_lon_deg=init_t2["os_init"][1],
        os_alt_m=ft_to_m(args.os_alt),
        os_course_deg=os_course,
        os_speed_mps=kt_to_mps(args.os_speed),
        os_vspeed_mps=fpm_to_mps(args.os_vspeed),
        rel_speed_mps=rel_speed_mps,
        conflict_dh_m=ft_to_m(args.conflict_dh),
        target_alto_m=ft_to_m(args.tgt_alto),
        relative_heading_deg=relative_heading,
        post_cpa_sec=post_cpa_sec
    )

# =========================================================
# EVERYTHING BELOW UNCHANGED
# =========================================================

import pandas as pd

positions_df = pd.DataFrame([
    {
        "start_lat": points["os_start"][0],
        "start_lon": points["os_start"][1],
        "start_alt": args.os_alt,
        "end_lat": points["os_end"][0],
        "end_lon": points["os_end"][1],
        "end_alt": round(m_to_ft(points["os_end"][2]), 2),
        "gspeed": args.os_speed,
        "vspeed": args.os_vspeed,
        "course": args.os_course
    },
    {
        "start_lat": points["tgt_start"][0],
        "start_lon": points["tgt_start"][1],
        "start_alt": round(m_to_ft(points["tgt_start"][2]), 2),
        "end_lat": points["tgt_end"][0],
        "end_lon": points["tgt_end"][1],
        "end_alt": round(m_to_ft(points["tgt_end"][2]), 2),
        "gspeed": args.rel_speed,
        "vspeed": 0.0,
        "course": points["tgt_course_deg"]
    }
])

positions_df.to_csv("positions.csv", index=False)

print("positions.csv generated successfully")

ownship_prefix = f"Ownship_{args.os_callsign}"
target_prefix = f"Target_{args.tgt_callsign}"

ownship_plan = f"{ownship_prefix}.plan"
target_plan = f"{target_prefix}.plan"

ownship_wp = f"{ownship_prefix}.waypoints"
target_wp = f"{target_prefix}.waypoints"

ownship_yaml = f"{ownship_prefix}.yaml"
target_yaml = f"{target_prefix}.yaml"

ownship_kml = f"{ownship_prefix}.kml"
target_kml = f"{target_prefix}.kml"

combined_kml = f"{ownship_prefix}_{target_prefix}.kml"

home = points["os_start"]

write_plan_file(ownship_plan, [points["os_start"], points["os_cpa"], points["os_end"]], home)
write_plan_file(target_plan, [points["tgt_start"], points["tgt_cpa"], points["tgt_end"]], home)

write_waypoints_file(ownship_wp, [points["os_start"], points["os_cpa"], points["os_end"]])
write_waypoints_file(target_wp, [points["tgt_start"], points["tgt_cpa"], points["tgt_end"]])

write_kml_file(ownship_kml, [points["os_start"], points["os_cpa"], points["os_end"]])
write_kml_file(target_kml, [points["tgt_start"], points["tgt_cpa"], points["tgt_end"]])

write_combined_kml_file(
    combined_kml,
    [points["os_start"], points["os_cpa"], points["os_end"]],
    [points["tgt_start"], points["tgt_cpa"], points["tgt_end"]]
)

write_yaml_file(
    path=ownship_yaml,
    callsign=args.os_callsign,
    sysid=1,
    lat_deg=points["os_start"][0],
    lon_deg=points["os_start"][1],
    alt_ft=args.os_alt,
    course_deg=args.os_course,
    ground_speed_kt=args.os_speed,
    vertical_speed_fpm=args.os_vspeed,
    waypoints_file=ownship_wp
)

tgt_start = points["tgt_start"]
tgt_alt_ft = round(m_to_ft(tgt_start[2]), 2)

write_yaml_file(
    path=target_yaml,
    callsign=args.tgt_callsign,
    sysid=2,
    lat_deg=tgt_start[0],
    lon_deg=tgt_start[1],
    alt_ft=tgt_alt_ft,
    course_deg=points["tgt_course_deg"],
    ground_speed_kt=args.tgt_speed,
    vertical_speed_fpm=0.0,
    waypoints_file=target_wp
)

print("✅ All files generated successfully!")