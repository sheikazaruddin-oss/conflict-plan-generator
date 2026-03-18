import streamlit as st
import base64
import zipfile
import io
import matplotlib.pyplot as plt

from conflict_math import compute_conflict_geometry
from plan_writer import write_plan_file, write_waypoints_file, write_kml_file, write_combined_kml_file
from yaml_writer import write_yaml_file
from units import ft_to_m, m_to_ft, kt_to_mps, mps_to_kt, fpm_to_mps
from validation_logger import save_validation_log


# ----------------------------
# SESSION STATE
# ----------------------------

if "files_generated" not in st.session_state:
    st.session_state.files_generated = False

if "generated_points" not in st.session_state:
    st.session_state.generated_points = None


# ----------------------------
# TIME CONVERSION
# ----------------------------

def mmss_to_sec(mmss: str) -> int:
    mmss = mmss.strip()
    parts = mmss.split(":")
    if len(parts) != 2:
        raise ValueError("TCPA must be in mm:ss format (example: 01:30)")
    minutes = int(parts[0])
    seconds = int(parts[1])
    if seconds < 0 or seconds >= 60:
        raise ValueError("Seconds must be between 0 and 59")
    return minutes * 60 + seconds


# ----------------------------
# PAGE
# ----------------------------

st.set_page_config(page_title="Conflict Plan Generator")
st.title("✈️ Conflict Plan Generator")


# ----------------------------
# CALLSIGNS (NEW)
# ----------------------------

os_callsign = st.text_input("Ownship Callsign", value="OWN01")
tgt_callsign = st.text_input("Target Callsign", value="TGT01")


# ----------------------------
# OWNERSHIP INPUTS
# ----------------------------

st.subheader("Ownship Aircraft Parameters")

tcpa_mmss = st.text_input("TCPA (mm:ss)", value="01:00")
cpa_dist_ft = st.number_input("CPA Distance (ft)", value=20)

os_lat = st.number_input("Ownship Latitude", value=37.618805, format="%.6f")
os_lon = st.number_input("Ownship Longitude", value=-122.375416, format="%.6f")

os_alt_ft = st.number_input("Ownship Altitude (ft)", value=50)
os_course = st.number_input("Ownship Course (deg)", value=90.0)
os_speed_kt = st.number_input("Ownship Speed (kt)", value=20)
os_vspeed_fpm = st.number_input("Ownship Vertical Speed (ft/min)", value=1)


# ----------------------------
# TARGET INPUTS
# ----------------------------

st.subheader("Target Aircraft Parameters")

rel_speed_kt = st.number_input("Relative Speed (kt)", value=10)
conflict_dh_ft = st.number_input("Conflict Relative Altitude (ft)", value=30)
tgt_alt_offset_ft = st.number_input("Target Alt Offset (ft)", value=20)
relative_heading = st.number_input("Relative Heading (deg)", value=95.0)


# ----------------------------
# GENERATE FILES
# ----------------------------

if st.button("Generate Plan Files"):
    try:
        st.session_state.files_generated = True

        tcpa_sec = mmss_to_sec(tcpa_mmss)

        cpa_dist_m = ft_to_m(cpa_dist_ft)
        os_alt_m = ft_to_m(os_alt_ft)
        os_speed_mps = kt_to_mps(os_speed_kt)
        os_vspeed_mps = fpm_to_mps(os_vspeed_fpm)
        rel_speed_mps = kt_to_mps(rel_speed_kt)
        conflict_dh_m = ft_to_m(conflict_dh_ft)
        tgt_alt_offset_m = ft_to_m(tgt_alt_offset_ft)

        points = compute_conflict_geometry(
            tcpa_sec=tcpa_sec,
            cpa_horiz_m=cpa_dist_m,
            os_lat_deg=os_lat,
            os_lon_deg=os_lon,
            os_alt_m=os_alt_m,
            os_course_deg=os_course,
            os_speed_mps=os_speed_mps,
            os_vspeed_mps=os_vspeed_mps,
            rel_speed_mps=rel_speed_mps,
            conflict_dh_m=conflict_dh_m,
            target_alto_m=tgt_alt_offset_m,
            relative_heading_deg=relative_heading
        )

        st.session_state.generated_points = points

        # ----------------------------
        # FILE NAMES (NEW)
        # ----------------------------

        ownship_prefix = f"Ownship_{os_callsign}"
        target_prefix = f"Target_{tgt_callsign}"

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
            callsign=os_callsign,
            sysid=1,
            lat_deg=os_lat,
            lon_deg=os_lon,
            alt_ft=os_alt_ft,
            course_deg=os_course,
            ground_speed_kt=os_speed_kt,
            vertical_speed_fpm=os_vspeed_fpm,
            waypoints_file=ownship_wp
        )

        tgt_start = points["tgt_start"]
        tgt_alt_ft = round(m_to_ft(tgt_start[2]), 2)

        write_yaml_file(
            path=target_yaml,
            callsign=tgt_callsign,
            sysid=2,
            lat_deg=tgt_start[0],
            lon_deg=tgt_start[1],
            alt_ft=tgt_alt_ft,
            course_deg=points["tgt_course_deg"],
            ground_speed_kt=round(mps_to_kt(rel_speed_mps), 2),
            vertical_speed_fpm=0.0,
            waypoints_file=target_wp
        )

        st.success("All files generated successfully!")

    except Exception as e:
        st.error(f"Error: {e}")


# ----------------------------
# DOWNLOADS
# ----------------------------

if st.session_state.files_generated:

    ownship_prefix = f"Ownship_{os_callsign}"
    target_prefix = f"Target_{tgt_callsign}"

    ownship_plan = f"{ownship_prefix}.plan"
    target_plan = f"{target_prefix}.plan"

    ownship_wp = f"{ownship_prefix}.waypoints"
    target_wp = f"{target_prefix}.waypoints"

    ownship_yaml = f"{ownship_prefix}.yaml"
    target_yaml = f"{target_prefix}.yaml"

    ownship_kml = f"{ownship_prefix}.kml"
    target_kml = f"{target_prefix}.kml"

    combined_kml = f"{ownship_prefix}_{target_prefix}.kml"

    st.subheader("Download Files")

    # PLAN ZIP
    plan_zip = io.BytesIO()
    with zipfile.ZipFile(plan_zip, "w") as z:
        z.write(ownship_plan)
        z.write(target_plan)

    st.download_button("Download Plan Files", plan_zip.getvalue(), "plan_files.zip")

    # WAYPOINT ZIP
    wp_zip = io.BytesIO()
    with zipfile.ZipFile(wp_zip, "w") as z:
        z.write(ownship_wp)
        z.write(target_wp)

    st.download_button("Download Waypoint Files", wp_zip.getvalue(), "waypoints.zip")

    # YAML ZIP
    yaml_zip = io.BytesIO()
    with zipfile.ZipFile(yaml_zip, "w") as z:
        z.write(ownship_yaml)
        z.write(target_yaml)

    st.download_button("Download YAML Files", yaml_zip.getvalue(), "yaml.zip")

    # KML ZIP
    kml_zip = io.BytesIO()
    with zipfile.ZipFile(kml_zip, "w") as z:
        z.write(ownship_kml)
        z.write(target_kml)
        z.write(combined_kml)

    st.download_button("Download KML Files", kml_zip.getvalue(), "kml.zip")