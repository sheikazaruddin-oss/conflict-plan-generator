import streamlit as st
import base64

from conflict_math import compute_conflict_geometry
from plan_writer import write_plan_file, write_waypoints_file, write_kml_file
from yaml_writer import write_yaml_file
from units import ft_to_m, m_to_ft, kt_to_mps, mps_to_kt, fpm_to_mps

# ==============================
# Logo
# ==============================

def show_logo_top_left(image_path, width=120):
    with open(image_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode()

    st.markdown(
        f"""
        <style>
        .top-left-logo {{
            position: fixed;
            top: 70px;
            left: 20px;
            z-index: 100;
        }}
        </style>
        <div class="top-left-logo">
            <img src="data:image/png;base64,{encoded}" width="{width}">
        </div>
        """,
        unsafe_allow_html=True,
    )

show_logo_top_left("logo.png")

st.set_page_config(page_title="Conflict Plan Generator")
st.title("✈️ Conflict Plan Generator")

# ==============================
# OWNERSHIP INPUTS (AVIATION UNITS)
# ==============================

st.subheader("Ownership Aircraft Parameters")

tcpa_sec = st.number_input("TCPA (s)", value=60.0)

cpa_dist_ft = st.number_input("CPA Distance (ft)", value=656.17)  # 200m default

os_lat = st.number_input("Ownership Latitude", value=37.618805)
os_lon = st.number_input("Ownership Longitude", value=-122.375416)

os_alt_ft = st.number_input("Ownership Altitude (ft)", value=164.0)  # 50m default

os_course = st.number_input("Ownership Course (deg)", value=90.0)

os_speed_kt = st.number_input("Ownership Speed (kt)", value=38.88)  # 20 m/s default

os_vspeed_fpm = st.number_input("Ownership Vertical Speed (ft/min)", value=0.0)

# ==============================
# TARGET INPUTS (AVIATION UNITS)
# ==============================

st.subheader("Target Aircraft Parameters")

rel_speed_kt = st.number_input("Relative Speed (kt)", value=19.44)

conflict_dh_ft = st.number_input("Conflict Relative Altitude (ft)", value=98.43)

tgt_alt_offset_ft = st.number_input("Target Alt Offset (ft)", value=164.0)

relative_heading = st.number_input("Relative Heading (deg)", value=95.0)

# ==============================
# GENERATE
# ==============================

if st.button("✅ Generate plan files"):

    try:

        # ==============================
        # CONVERT TO INTERNAL UNITS
        # ==============================

        cpa_dist_m = ft_to_m(cpa_dist_ft)
        os_alt_m = ft_to_m(os_alt_ft)
        os_speed_mps = kt_to_mps(os_speed_kt)
        os_vspeed_mps = fpm_to_mps(os_vspeed_fpm)

        rel_speed_mps = kt_to_mps(rel_speed_kt)
        conflict_dh_m = ft_to_m(conflict_dh_ft)
        tgt_alt_offset_m = ft_to_m(tgt_alt_offset_ft)

        # ==============================
        # COMPUTE CONFLICT
        # ==============================

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
            relative_heading_deg=relative_heading,
        )

        home = points["os_start"]

        # ==============================
        # FILE GENERATION
        # ==============================

        write_plan_file("ownership.plan",
                        [points["os_start"], points["os_cpa"]],
                        home)

        write_plan_file("target.plan",
                        [points["tgt_start"], points["tgt_cpa"]],
                        home)

        write_waypoints_file("ownership.waypoints",
                             [points["os_start"], points["os_cpa"]])

        write_waypoints_file("target.waypoints",
                             [points["tgt_start"], points["tgt_cpa"]])

        write_kml_file("ownership.kml",
                       [points["os_start"], points["os_cpa"]])

        write_kml_file("target.kml",
                       [points["tgt_start"], points["tgt_cpa"]])

        # ==============================
        # YAML GENERATION
        # ==============================

        write_yaml_file(
            path="ownership.yaml",
            callsign="OWN01",
            lat_deg=os_lat,
            lon_deg=os_lon,
            alt_ft=os_alt_ft,
            course_deg=os_course,
            ground_speed_kt=os_speed_kt,
            vertical_speed_fpm=os_vspeed_fpm,
            waypoints_file="ownership.waypoints"
        )

        tgt_start = points["tgt_start"]
        tgt_alt_ft = round(m_to_ft(tgt_start[2]), 2)

        write_yaml_file(
            path="target.yaml",
            callsign="TGT01",
            lat_deg=tgt_start[0],
            lon_deg=tgt_start[1],
            alt_ft=tgt_alt_ft,
            course_deg=points["tgt_course_deg"],
            ground_speed_kt=round(mps_to_kt(rel_speed_mps), 2),
            vertical_speed_fpm=0.0,
            waypoints_file="target.waypoints"
        )

        # ==============================
        # DOWNLOAD BUTTONS
        # ==============================

        with open("ownership.plan", "rb") as f:
            st.download_button("Download Ownership Plan", f, file_name="ownership.plan")

        with open("target.plan", "rb") as f:
            st.download_button("Download Target Plan", f, file_name="target.plan")

        with open("ownership.waypoints", "rb") as f:
            st.download_button("Download Ownership Waypoints", f, file_name="ownership.waypoints")

        with open("target.waypoints", "rb") as f:
            st.download_button("Download Target Waypoints", f, file_name="target.waypoints")

        with open("ownership.kml", "rb") as f:
            st.download_button("Download Ownership KML", f, file_name="ownership.kml")

        with open("target.kml", "rb") as f:
            st.download_button("Download Target KML", f, file_name="target.kml")

        with open("ownership.yaml", "rb") as f:
            st.download_button("Download Ownership YAML", f, file_name="ownership.yaml")

        with open("target.yaml", "rb") as f:
            st.download_button("Download Target YAML", f, file_name="target.yaml")

        st.success("✅ All files generated successfully!")

    except Exception as e:
        st.error(f"❌ Error: {e}")