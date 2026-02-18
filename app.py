import argparse
from conflict_math import compute_conflict_geometry
from plan_writer import write_plan_file, write_waypoints_file, write_kml_file
from units import ft_to_m, kt_to_mps, fpm_to_mps
import yaml


def write_yaml_file(filename, callsign, home, heading_deg,
                    speed_kt, vs_fpm, waypoints_file):

    lat, lon, alt_m = home
    alt_ft = alt_m / 0.3048

    data = {
        "version": 1,
        "vehicle": {
            "callsign": callsign
        },
        "sitl": {
            "home": {
                "lat_deg": lat,
                "lon_deg": lon,
                "alt_ft": round(alt_ft, 2)
            }
        },
        "initial_conditions": {
            "course_heading_deg": heading_deg,
            "ground_speed_kt": speed_kt,
            "vertical_speed_fpm": vs_fpm
        },
        "mission": {
            "waypoints_file": waypoints_file,
            "starting_waypoint_index": 0,
            "auto_set_mode": "AUTO",
            "start_automatically": True
        }
    }

    with open(filename, "w") as f:
        yaml.dump(data, f, sort_keys=False)


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--tcpa", type=float, required=True)
    parser.add_argument("--cpa", type=float, required=True, help="CPA distance (feet)")
    parser.add_argument("--os-lat", type=float, required=True)
    parser.add_argument("--os-lon", type=float, required=True)
    parser.add_argument("--os-alt", type=float, required=True, help="Ownship altitude (feet)")
    parser.add_argument("--os-course", type=float, required=True)
    parser.add_argument("--os-speed", type=float, required=True, help="Ownship speed (knots)")
    parser.add_argument("--os-vspeed", type=float, required=True, help="Ownship vertical speed (ft/min)")
    parser.add_argument("--rel-speed", type=float, required=True, help="Target speed (knots)")
    parser.add_argument("--conflict-dh", type=float, required=True, help="Vertical separation (feet)")
    parser.add_argument("--tgt-alto", type=float, required=True, help="Target altitude offset (feet)")
    parser.add_argument("--relative-heading", type=float, required=True)

    args = parser.parse_args()

    # 🔁 UNIT CONVERSIONS
    cpa_m = ft_to_m(args.cpa)
    os_alt_m = ft_to_m(args.os_alt)
    os_speed_mps = kt_to_mps(args.os_speed)
    os_vspeed_mps = fpm_to_mps(args.os_vspeed)
    rel_speed_mps = kt_to_mps(args.rel_speed)
    conflict_dh_m = ft_to_m(args.conflict_dh)
    tgt_alto_m = ft_to_m(args.tgt_alto)

    points = compute_conflict_geometry(
        tcpa_sec=args.tcpa,
        cpa_horiz_m=cpa_m,
        os_lat_deg=args.os_lat,
        os_lon_deg=args.os_lon,
        os_alt_m=os_alt_m,
        os_course_deg=args.os_course,
        os_speed_mps=os_speed_mps,
        os_vspeed_mps=os_vspeed_mps,
        rel_speed_mps=rel_speed_mps,
        conflict_dh_m=conflict_dh_m,
        target_alto_m=tgt_alto_m,
        relative_heading_deg=args.relative_heading
    )

    home = points["os_start"]

    # Standard files
    write_plan_file("ownship.plan",
                    [points["os_start"], points["os_cpa"]], home)
    write_plan_file("target.plan",
                    [points["tgt_start"], points["tgt_cpa"]], home)

    write_waypoints_file("ownship.waypoints",
                         [points["os_start"], points["os_cpa"]])
    write_waypoints_file("target.waypoints",
                         [points["tgt_start"], points["tgt_cpa"]])

    write_kml_file("ownship.kml",
                   [points["os_start"], points["os_cpa"]])
    write_kml_file("target.kml",
                   [points["tgt_start"], points["tgt_cpa"]])

    # YAML generation
    write_yaml_file("ownship.yaml", "OWNSHIP01",
                    home, args.os_course,
                    args.os_speed,
                    args.os_vspeed,
                    "ownship.waypoints")

    write_yaml_file("target.yaml", "TARGET01",
                    home, args.os_course,
                    args.rel_speed,
                    0.0,
                    "target.waypoints")

    print("✅ All files generated (.plan, .waypoints, .kml, .yaml)")


if __name__ == "__main__":
    main()