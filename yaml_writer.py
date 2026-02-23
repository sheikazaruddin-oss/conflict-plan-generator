# yaml_writer.py

def write_yaml_file(
    path,
    callsign,
    lat_deg,
    lon_deg,
    alt_ft,
    course_deg,
    ground_speed_kt,
    vertical_speed_fpm,
    waypoints_file
):

    content = f"""# Vehicle initialization file for multi-SITL runner
# Units:
#   - heading/course: degrees true (0–360)
#   - ground_speed: knots
#   - vertical_speed: feet per minute (positive = climb)
#   - waypoint_index: define in runner (recommended: 0-based)

version: 1

vehicle:
  callsign: "{callsign}"

sitl:
  home:
    lat_deg: {lat_deg}
    lon_deg: {lon_deg}
    alt_ft: {alt_ft}

initial_conditions:
  course_heading_deg: {course_deg}
  ground_speed_kt: {ground_speed_kt}
  vertical_speed_fpm: {vertical_speed_fpm}
  start_mode : midflight

mission:
  waypoints_file: "{waypoints_file}"
  starting_waypoint_index: 0
  auto_set_mode: "AUTO"
  start_automatically: true
"""

    with open(path, "w") as f:
        f.write(content)