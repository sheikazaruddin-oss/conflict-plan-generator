import streamlit as st
from conflict_math import calculate_cpa_geometry
from plan_writer import write_plan_file, write_waypoint_file
import base64

# Show logo at top-left (exact style from your original)
def show_logo_top_left(image_path, width=120):
    with open(image_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode()
    st.markdown(
        f"""
        <style>
        .top-left-logo {{
            position: fixed;
            top: 15px;
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

# Call logo before layout
show_logo_top_left("logo.png")

st.set_page_config(page_title="Conflict Plan Generator")
st.title("✈️ Conflict Plan Generator")
st.subheader("Ownership Aircraft Parameters")

tcpa_sec = st.number_input("TCPA (s)", value=60.0)
cpa_dist_m = st.number_input("CPA Distance (m)", value=200.0)
os_lat_deg = st.number_input("Ownership Latitude", value=37.618805)
os_lon_deg = st.number_input("Ownership Longitude", value=-122.375416)
os_alt_m = st.number_input("Ownership Altitude (m)", value=50.0)
os_course_deg = st.number_input("Ownership Course (deg)", value=90.0)
os_speed_mps = st.number_input("Ownership Speed (m/s)", value=20.0)
os_vspeed_mps = st.number_input("Ownership Vertical Speed (m/s)", value=1.0)

st.subheader("Target Aircraft Parameters")

rel_speed_mps = st.number_input("Relative Speed (m/s)", value=10.0)
conflict_dh_m = st.number_input("Conflict Altitude Diff (m)", value=30.0)
target_alto_m = st.number_input("Target Alt Offset (m)", value=50.0)
relative_heading_deg = st.number_input("Relative Heading (deg)", value=0.0)

if st.button("✅ Generate plan files"):
    try:
        points = calculate_cpa_geometry(
            tcpa_sec=tcpa_sec,
            cpa_horiz_m=cpa_dist_m,
            os_lat_deg=os_lat_deg,
            os_lon_deg=os_lon_deg,
            os_alt_m=os_alt_m,
            os_course_deg=os_course_deg,
            os_speed_mps=os_speed_mps,
            os_vspeed_mps=os_vspeed_mps,
            rel_speed_mps=rel_speed_mps,
            conflict_dh_m=conflict_dh_m,
            target_alto_m=target_alto_m,
            relative_heading_deg=relative_heading_deg
        )

        home_position = points["os_start"]

        # Write .plan files
        write_plan_file("ownership.plan", [points["os_start"], points["os_cpa"]], home_position)
        write_plan_file("target.plan", [points["tgt_start"], points["tgt_cpa"]], home_position)

        # Write .waypoints files
        write_waypoint_file("ownership.waypoints", [points["os_start"], points["os_cpa"]])
        write_waypoint_file("target.waypoints", [points["tgt_start"], points["tgt_cpa"]])

        st.success("✅ Plan and waypoint files generated!")

        # Downloads
        with open("ownership.plan", "rb") as f:
            st.download_button("Download Ownership Plan (.plan)", f, file_name="ownership.plan")

        with open("target.plan", "rb") as f:
            st.download_button("Download Target Plan (.plan)", f, file_name="target.plan")

        with open("ownership.waypoints", "rb") as f:
            st.download_button("Download Ownership Waypoints", f, file_name="ownership.waypoints")

        with open("target.waypoints", "rb") as f:
            st.download_button("Download Target Waypoints", f, file_name="target.waypoints")

    except Exception as e:
        st.error(f"❌ Error: {e}")