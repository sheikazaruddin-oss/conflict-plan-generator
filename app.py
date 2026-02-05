import argparse
from conflict_math import compute_conflict_geometry
from plan_writer import write_plan_file, write_waypoints_file

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tcpa", type=float, required=True)
    parser.add_argument("--cpa", type=float, required=True)
    parser.add_argument("--os-lat", type=float, required=True)
    parser.add_argument("--os-lon", type=float, required=True)
    parser.add_argument("--os-alt", type=float, required=True)
    parser.add_argument("--os-course", type=float, required=True)
    parser.add_argument("--os-speed", type=float, required=True)
    parser.add_argument("--os-vspeed", type=float, required=True)
    parser.add_argument("--rel-speed", type=float, required=True)
    parser.add_argument("--conflict-dh", type=float, required=True)
    parser.add_argument("--tgt-alto", type=float, default=50.0)
    parser.add_argument("--relative-heading", type=float, required=True)
    args = parser.parse_args()

    points = compute_conflict_geometry(
        tcpa_sec=args.tcpa,
        cpa_horiz_m=args.cpa,
        os_lat_deg=args.os_lat,
        os_lon_deg=args.os_lon,
        os_alt_m=args.os_alt,
        os_course_deg=args.os_course,
        os_speed_mps=args.os_speed,
        os_vspeed_mps=args.os_vspeed,
        rel_speed_mps=args.rel_speed,
        conflict_dh_m=args.conflict_dh,
        target_alto_m=args.tgt_alto,
        relative_heading_deg=args.relative_heading
    )

    home = points["os_start"]
    write_plan_file("ownership.plan", [points["os_start"], points["os_cpa"]], home)
    write_plan_file("target.plan", [points["tgt_start"], points["tgt_cpa"]], home)
    write_waypoints_file("ownership.waypoints", [points["os_start"], points["os_cpa"]])
    write_waypoints_file("target.waypoints", [points["tgt_start"], points["tgt_cpa"]])

    print("✅ Plan and waypoint files generated.")

if __name__ == "__main__":
    main()