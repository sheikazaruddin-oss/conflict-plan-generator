import streamlit as st
from conflict_math import calculate_cpa_geometry
from plan_writer import write_plan_file, write_waypoint_file

st.set_page_config(page_title="CPA Conflict Geometry Generator")

st.title("🛩️ Conflict Geometry Generator")

with st.form("cpa_form"):
    st.subheader("Ownship Info")
    os_lat = st.number_input("Latitude", value=37.0)
    os_lon = st.number_input("Longitude", value=-122.0)
    os_alt = st.number_input("Altitude (m)", value=50)
    os_course = st.number_input("Course (deg)", value=90)
    os_speed = st.number_input("Speed (knots)", value=30)
    os_vspeed = st.number_input("Vertical Speed (m/s)", value=1)

    st.subheader("Conflict Settings")
    tcpa = st.number_input("Time to CPA (s)", value=60)
    cpa_distance = st.number_input("CPA Separation (m)", value=30)
    tgt_alt_offset = st.number_input("Target Altitude Offset (m)", value=30)
    tgt_rel_speed = st.number_input("Target Relative Speed (knots)", value=30)
    relative_heading = st.slider("Relative Heading to Ownship (deg)", 0, 359, value=0)

    submitted = st.form_submit_button("Generate")

if submitted:
    os_wp1, os_wp2, tgt_wp1, tgt_wp2 = calculate_cpa_geometry(
        tcpa,
        cpa_distance,
        os_lat,
        os_lon,
        os_alt,
        os_course,
        os_speed,
        os_vspeed,
        tgt_rel_speed,
        tgt_alt_offset,
        relative_heading
    )

    # File names
    write_plan_file("ownership.plan", os_wp1, os_wp2)
    write_plan_file("target.plan", tgt_wp1, tgt_wp2)

    write_waypoint_file("ownership.waypoints", os_wp1, os_wp2)
    write_waypoint_file("target.waypoints", tgt_wp1, tgt_wp2)

    st.success("✅ Files generated!")

    for fname in ["ownership.plan", "target.plan", "ownership.waypoints", "target.waypoints"]:
        with open(fname, "rb") as f:
            st.download_button(label=f"Download {fname}", data=f, file_name=fname)