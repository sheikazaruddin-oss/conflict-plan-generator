import streamlit as st
import base64
import zipfile
import io

from conflict_math import compute_conflict_geometry
from plan_writer import write_plan_file, write_waypoints_file, write_kml_file
from yaml_writer import write_yaml_file
from units import ft_to_m, m_to_ft, kt_to_mps, mps_to_kt, fpm_to_mps
from validation_logger import save_validation_log


# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "files_generated" not in st.session_state:
    st.session_state.files_generated = False


# --------------------------------------------------
# UTIL FUNCTIONS
# --------------------------------------------------

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


# --------------------------------------------------
# LOGO
# --------------------------------------------------

def show_logo_top_left(image_path, width=120):

    with open(image_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode()

    st.markdown(
        f"""
        <style>
        .top-left-logo {{
            position: fixed;
            top: 50px;
            left: 20px;
            z-index: 100;
        }}
        </style>

        <div class="top-left-logo">
            <img src="data:image/png;base64,{encoded}" width="{width}">
        </div>
        """,
        unsafe_allow_html=True
    )


show_logo_top_left("logo.png")


# --------------------------------------------------
# PAGE
# --------------------------------------------------

st.set_page_config(page_title="Conflict Plan Generator")

st.title("✈ Conflict Plan Generator")


# --------------------------------------------------
# OWNSHIP INPUTS
# --------------------------------------------------

st.subheader("Ownship Aircraft Parameters")

tcpa_mmss = st.text_input("TCPA (mm:ss)", value="01:00")

cpa_dist_ft = st.number_input("CPA Distance (ft)", value=20)

os_lat = st.number_input("Ownship Latitude", value=37.618805, format="%.6f")
os_lon = st.number_input("Ownship Longitude", value=-122.375416, format="%.6f")

os_alt_ft = st.number_input("Ownship Altitude (ft)", value=50)

os_course = st.number_input("Ownship Course (deg)", value=90.0)

os_speed_kt = st.number_input("Ownship Speed (kt)", value=20)

os_vspeed_fpm = st.number_input("Ownship Vertical Speed (ft/min)", value=1)


# --------------------------------------------------
# TARGET INPUTS
# --------------------------------------------------

st.subheader("Target Aircraft Parameters")

rel_speed_kt = st.number_input("Relative Speed (kt)", value=10)

conflict_dh_ft = st.number_input("Conflict Relative Altitude (ft)", value=30)

tgt_alt_offset_ft = st.number_input("Target Alt Offset (ft)", value=20)

relative_heading = st.number_input("Relative Heading (deg)", value=95.0)


# --------------------------------------------------
# GENERATE BUTTON
# --------------------------------------------------

if st.button("Generate Plan Files"):

    try:

        st.session_state.files_generated = True

        tcpa_sec = mmss_to_sec(tcpa_mmss)

        # ----------------------------------
        # UNIT CONVERSIONS
        # ----------------------------------

        cpa_dist_m = ft_to_m(cpa_dist_ft)

        os_alt_m = ft_to_m(os_alt_ft)

        os_speed_mps = kt_to_mps(os_speed_kt)

        os_vspeed_mps = fpm_to_mps(os_vspeed_fpm)

        rel_speed_mps = kt_to_mps(rel_speed_kt)

        conflict_dh_m = ft_to_m(conflict_dh_ft)

        tgt_alt_offset_m = ft_to_m(tgt_alt_offset_ft)


        # ----------------------------------
        # COMPUTE GEOMETRY
        # ----------------------------------

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


        # ----------------------------------
        # VALIDATION LOG
        # ----------------------------------

        inputs_dict = {
            "tcpa_mmss": tcpa_mmss,
            "tcpa_sec": tcpa_sec,
            "cpa_ft": cpa_dist_ft,
            "os_lat_deg": os_lat,
            "os_lon_deg": os_lon,
            "os_alt_ft": os_alt_ft,
            "os_course_deg": os_course,
            "os_speed_kt": os_speed_kt,
            "os_vspeed_fpm": os_vspeed_fpm,
            "rel_speed_kt": rel_speed_kt,
            "conflict_dh_ft": conflict_dh_ft,
            "tgt_alt_offset_ft": tgt_alt_offset_ft,
            "relative_heading_deg": relative_heading,
        }

        save_validation_log(
            "scenario_log.json",
            inputs_dict,
            points,
            tcpa_sec
        )


        # ----------------------------------
        # FILE GENERATION
        # ----------------------------------

        home = points["os_start"]


        write_plan_file(
            "ownship.plan",
            [points["os_start"], points["os_cpa"]],
            home
        )

        write_plan_file(
            "target.plan",
            [points["tgt_start"], points["tgt_cpa"]],
            home
        )


        write_waypoints_file(
            "ownship.waypoints",
            [points["os_start"], points["os_cpa"]]
        )

        write_waypoints_file(
            "target.waypoints",
            [points["tgt_start"], points["tgt_cpa"]]
        )


        write_kml_file(
            "ownship.kml",
            [points["os_start"], points["os_cpa"]]
        )

        write_kml_file(
            "target.kml",
            [points["tgt_start"], points["tgt_cpa"]]
        )


        write_yaml_file(
            path="ownship.yaml",
            callsign="OWN01",
            sysid=1,
            lat_deg=os_lat,
            lon_deg=os_lon,
            alt_ft=os_alt_ft,
            course_deg=os_course,
            ground_speed_kt=os_speed_kt,
            vertical_speed_fpm=os_vspeed_fpm,
            waypoints_file="ownship.waypoints"
        )


        tgt_start = points["tgt_start"]

        tgt_alt_ft = round(m_to_ft(tgt_start[2]), 2)


        write_yaml_file(
            path="target.yaml",
            callsign="TGT01",
            sysid=2,
            lat_deg=tgt_start[0],
            lon_deg=tgt_start[1],
            alt_ft=tgt_alt_ft,
            course_deg=points["tgt_course_deg"],
            ground_speed_kt=round(mps_to_kt(rel_speed_mps), 2),
            vertical_speed_fpm=0.0,
            waypoints_file="target.waypoints"
        )


        st.success("All files generated successfully!")

    except Exception as e:

        st.error(f"Error: {e}")


# --------------------------------------------------
# DOWNLOAD BUTTONS
# --------------------------------------------------

if st.session_state.files_generated:

    st.markdown("---")

    # -----------------------------
    # PLAN FILES
    # -----------------------------

    st.subheader(".PLAN FILES")

    plan_zip = io.BytesIO()

    with zipfile.ZipFile(plan_zip, "w") as z:
        z.write("ownship.plan")
        z.write("target.plan")

    st.download_button(
        "Download Plan Files",
        data=plan_zip.getvalue(),
        file_name="plan_files.zip",
        mime="application/zip"
    )


    # -----------------------------
    # WAYPOINT FILES
    # -----------------------------

    st.markdown("---")

    st.subheader(".WAYPOINT FILES")

    waypoint_zip = io.BytesIO()

    with zipfile.ZipFile(waypoint_zip, "w") as z:
        z.write("ownship.waypoints")
        z.write("target.waypoints")

    st.download_button(
        "Download Waypoint Files",
        data=waypoint_zip.getvalue(),
        file_name="waypoint_files.zip",
        mime="application/zip"
    )


    # -----------------------------
    # YAML FILES
    # -----------------------------

    st.markdown("---")

    st.subheader(".YAML FILES")

    yaml_zip = io.BytesIO()

    with zipfile.ZipFile(yaml_zip, "w") as z:
        z.write("ownship.yaml")
        z.write("target.yaml")

    st.download_button(
        "Download YAML Files",
        data=yaml_zip.getvalue(),
        file_name="yaml_files.zip",
        mime="application/zip"
    )


    # -----------------------------
    # VALIDATION LOG (UNCHANGED)
    # -----------------------------

    with open("scenario_log.json", "rb") as f:

        st.markdown("---")

        st.subheader("VALIDATION LOG")

        st.download_button(
            "Download Validation Log",
            f,
            file_name="scenario_log.json",
            mime="application/json"
        )