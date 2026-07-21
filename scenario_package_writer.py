import io
import os
import re
import zipfile


def validate_scenario_name(scenario_name):
    """
    Validate the scenario name.

    The scenario name is used for:
    - ZIP filename
    - vehicles_dir in runner.yaml
    - missions_dir in runner.yaml
    - state_dir in runner.yaml
    """

    scenario_name = str(scenario_name).strip()

    if not scenario_name:
        raise ValueError("Scenario name cannot be empty")

    if not re.fullmatch(r"[A-Za-z0-9_-]+", scenario_name):
        raise ValueError(
            "Scenario name may contain only letters, numbers, "
            "underscores, and hyphens"
        )

    return scenario_name


def validate_callsign(callsign, vehicle_label):
    """
    Validate an Ownship or Target callsign.
    """

    callsign = str(callsign).strip()

    if not callsign:
        raise ValueError(f"{vehicle_label} callsign cannot be empty")

    if not re.fullmatch(r"[A-Za-z0-9_-]+", callsign):
        raise ValueError(
            f"{vehicle_label} callsign may contain only letters, "
            "numbers, underscores, and hyphens"
        )

    return callsign


def build_runner_yaml(scenario_name):
    """
    Generate runner.yaml.

    Only these values are changed:
    - vehicles_dir
    - missions_dir
    - state_dir

    Everything else stays exactly as provided in the sample.
    """

    scenario_name = validate_scenario_name(scenario_name)

    return f"""version: 2.1
paths:
  # you CAN use the same directory for all three, ex: "../scenario_XXX"

  # Directory containing vehicle YAML files.
  # Vehicle files are YAMLs with a top-level `vehicle:` mapping.
  vehicles_dir: "../{scenario_name}"
  
  # Directory containing QGC .waypoints files referenced by vehicle mission configs.
  missions_dir: "../{scenario_name}"

  # Base directory for generated run artifacts.
  # sim_manager creates a timestamped run directory inside this directory.
  # If this directory does not exist, sim_manager creates it.
  state_dir: "../{scenario_name}"

run_mode: development_direct

clock_mode: backend_realtime

ardupilot:
  # Absolute path to sim_vehicle.py
  # Required.
  sitl_launcher: "/home/sheik/ardupilot/Tools/autotest/sim_vehicle.py"

  # Options below apply to ALL Vehicles
  no_rebuild: true
  sim_speedup: 1

multicast:
  enabled: true

  # Multicast group (must be 224.0.0.0 – 239.255.255.255)
  group_ip: "239.255.145.50"

  # Destination port receivers will listen on
  port: 14560

  # TTL for multicast packets
  ttl: 1

  # Optional: specific outbound interface IP (null = OS default)
  iface_ip: null

network:
  # All other endpoints

  endpoints:
    - name: "qgc_1"
      protocol: "udp"
      ip: "127.0.0.1"   # example: WSL2 host IP
      port: 14550

    # Example telemetry consumer
    - name: "collector_1"
      protocol: "udp"
      ip: "127.0.0.1"
      port: 15000

logging:
  level: "INFO"

artifacts:
  debug_logs: 
    manager: true
    per_vehicle: false
  telemetry:
    enabled: true
    rate_hz: 5.0
  scratch:
    keep_on_success: false # keep instance files (eeprombin, etc) on successful run
    keep_on_failure: true  # keep instance files (eeprombin, etc.) on failed run

spawn:
  settle_time_s: 5.0
  min_offset_m: 30.0
  max_offset_m: 500.0

  bootstrap_s: 5.0
  settle_margin_s: 1.0
  stable_dwell_s: 0.7
  scheduler_guard_s: 0.5
  v_xy_min_mps: 1.0
  v_xy_max_mps: 60.0
  vz_default_max_mps: 2.0
  min_t0_lead_s: 0
  t0_rounding_s: 0.5

ready:
  radius_m: 2.0
"""


def build_vehicle_yaml(
    callsign,
    sysid,
    lat_deg,
    lon_deg,
    alt_ft,
    course_heading_deg,
    ground_speed_kt,
    vertical_speed_fpm,
    waypoints_file,
    to_waypoint_index
):
    """
    Generate the new package-specific vehicle YAML.

    This does not replace or modify the YAML files already generated
    by the existing Conflict Plan Generator.
    """

    callsign = validate_callsign(callsign, "Vehicle")

    sysid = int(sysid)
    to_waypoint_index = int(to_waypoint_index)

    if sysid < 1 or sysid > 255:
        raise ValueError("Vehicle SysID must be between 1 and 255")

    if to_waypoint_index < 0:
        raise ValueError("To Waypoint Index cannot be negative")

    return f"""version: 2
vehicle:
  callsign: {callsign}
  sysid: {sysid}
  frame: NasaReaper
  backend: kinematic_vehicle
  control_type: ArduPlane
initial_conditions:
  start_mode: midflight
  lat_deg: {float(lat_deg)}
  lon_deg: {float(lon_deg)}
  alt_ft: {float(alt_ft)}
  course_heading_deg: {float(course_heading_deg)}
  ground_speed_kt: {float(ground_speed_kt)}
  vertical_speed_fpm: {float(vertical_speed_fpm)}
missions:
- name: Primary Mission
  primary: true
  waypoints_file: {waypoints_file}
  to_waypoint_index: {to_waypoint_index}
  start_automatically: true
  turn_mode: fly_by
  descent_mode: slope
control:
  quick_maneuver_disable_behavior: maintain
"""


def build_scenario_zip(
    scenario_name,
    ownship_callsign,
    target_callsign,
    ownship_sysid,
    target_sysid,
    ownship_lat_deg,
    ownship_lon_deg,
    ownship_alt_ft,
    ownship_course_deg,
    ownship_speed_kt,
    ownship_vertical_speed_fpm,
    target_lat_deg,
    target_lon_deg,
    target_alt_ft,
    target_course_deg,
    target_speed_kt,
    target_vertical_speed_fpm,
    ownship_to_waypoint_index,
    target_to_waypoint_index,
    existing_ownship_waypoints_path,
    existing_target_waypoints_path
):
    """
    Build the independent scenario ZIP.

    ZIP contents:
    - runner.yaml
    - <OwnshipCallsign>.waypoints
    - <TargetCallsign>.waypoints
    - <OwnshipCallsign>.yaml
    - <TargetCallsign>.yaml

    Existing files are only read. They are not modified.
    """

    scenario_name = validate_scenario_name(scenario_name)

    ownship_callsign = validate_callsign(
        ownship_callsign,
        "Ownship"
    )

    target_callsign = validate_callsign(
        target_callsign,
        "Target"
    )

    if ownship_callsign == target_callsign:
        raise ValueError(
            "Ownship and Target callsigns must be different"
        )

    if int(ownship_sysid) == int(target_sysid):
        raise ValueError(
            "Ownship and Target SysIDs must be different"
        )

    if not os.path.isfile(existing_ownship_waypoints_path):
        raise FileNotFoundError(
            "Ownship waypoint file was not found: "
            f"{existing_ownship_waypoints_path}"
        )

    if not os.path.isfile(existing_target_waypoints_path):
        raise FileNotFoundError(
            "Target waypoint file was not found: "
            f"{existing_target_waypoints_path}"
        )

    # Names used only inside the new ZIP.
    ownship_waypoints_name = (
        f"{ownship_callsign}.waypoints"
    )

    target_waypoints_name = (
        f"{target_callsign}.waypoints"
    )

    ownship_yaml_name = (
        f"{ownship_callsign}.yaml"
    )

    target_yaml_name = (
        f"{target_callsign}.yaml"
    )

    runner_yaml = build_runner_yaml(
        scenario_name
    )

    ownship_vehicle_yaml = build_vehicle_yaml(
        callsign=ownship_callsign,
        sysid=ownship_sysid,
        lat_deg=ownship_lat_deg,
        lon_deg=ownship_lon_deg,
        alt_ft=ownship_alt_ft,
        course_heading_deg=ownship_course_deg,
        ground_speed_kt=ownship_speed_kt,
        vertical_speed_fpm=ownship_vertical_speed_fpm,
        waypoints_file=ownship_waypoints_name,
        to_waypoint_index=ownship_to_waypoint_index
    )

    target_vehicle_yaml = build_vehicle_yaml(
        callsign=target_callsign,
        sysid=target_sysid,
        lat_deg=target_lat_deg,
        lon_deg=target_lon_deg,
        alt_ft=target_alt_ft,
        course_heading_deg=target_course_deg,
        ground_speed_kt=target_speed_kt,
        vertical_speed_fpm=target_vertical_speed_fpm,
        waypoints_file=target_waypoints_name,
        to_waypoint_index=target_to_waypoint_index
    )

    # Read the existing waypoint files without changing them.
    with open(
        existing_ownship_waypoints_path,
        "rb"
    ) as waypoint_file:
        ownship_waypoints_data = waypoint_file.read()

    with open(
        existing_target_waypoints_path,
        "rb"
    ) as waypoint_file:
        target_waypoints_data = waypoint_file.read()

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(
        zip_buffer,
        mode="w",
        compression=zipfile.ZIP_DEFLATED
    ) as zip_file:

        zip_file.writestr(
            "runner.yaml",
            runner_yaml.encode("utf-8")
        )

        zip_file.writestr(
            ownship_waypoints_name,
            ownship_waypoints_data
        )

        zip_file.writestr(
            target_waypoints_name,
            target_waypoints_data
        )

        zip_file.writestr(
            ownship_yaml_name,
            ownship_vehicle_yaml.encode("utf-8")
        )

        zip_file.writestr(
            target_yaml_name,
            target_vehicle_yaml.encode("utf-8")
        )

    zip_buffer.seek(0)

    return zip_buffer.getvalue()