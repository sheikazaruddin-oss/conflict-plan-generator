import argparse

from conflict_math import compute_conflict_geometry
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


# ----------------------------
# ARGUMENTS
# ----------------------------

parser = argparse.ArgumentParser()

parser.add_argument("--os_callsign", default="OWN01")
parser.add_argument("--tgt_callsign", default="TGT01")

parser.add_argument("--tcpa", default="01:00")
parser.add_argument("--cpa", type=float, default=20)

parser.add_argument("--os_lat", type=float, required=True)
parser.add_argument("--os_lon", type=float, required=True)

parser.add_argument("--os_alt", type=float, default=50)
parser.add_argument("--os_course", type=float, default=90)
parser.add_argument("--os_speed", type=float, default=20)
parser.add_argument("--os_vspeed", type=float, default=1)

parser.add_argument("--rel_speed", type=float, default=10)
parser.add_argument("--conflict_dh", type=float, default=30)
parser.add_argument("--tgt_alto", type=float, default=20)
parser.add_argument("--relative_heading", type=float, default=95)

args = parser.parse_args()


# ----------------------------
# CONVERSIONS
# ----------------------------

tcpa_sec = mmss_to_sec(args.tcpa)

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
    relative_heading_deg=args.relative_heading
)


# ----------------------------
# FILE NAMES
# ----------------------------

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


# ----------------------------
# WRITE FILES
# ----------------------------

home = points["os_start"]

write_plan_file(ownship_plan, [points["os_start"], points["os_cpa"]], home)
write_plan_file(target_plan, [points["tgt_start"], points["tgt_cpa"]], home)

write_waypoints_file(ownship_wp, [points["os_start"], points["os_cpa"]])
write_waypoints_file(target_wp, [points["tgt_start"], points["tgt_cpa"]])

write_kml_file(ownship_kml, [points["os_start"], points["os_cpa"]])
write_kml_file(target_kml, [points["tgt_start"], points["tgt_cpa"]])

write_combined_kml_file(
    combined_kml,
    [points["os_start"], points["os_cpa"]],
    [points["tgt_start"], points["tgt_cpa"]]
)

# ----------------------------
# YAML
# ----------------------------

write_yaml_file(
    path=ownship_yaml,
    callsign=args.os_callsign,
    sysid=1,
    lat_deg=args.os_lat,
    lon_deg=args.os_lon,
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
    ground_speed_kt=round(mps_to_kt(kt_to_mps(args.rel_speed)), 2),
    vertical_speed_fpm=0.0,
    waypoints_file=target_wp
)

print("✅ All files generated successfully!")