import streamlit as st
from conflict_math import compute_conflict_geometry
from plan_writer import write_plan_file
import base64

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

show_logo_top_left("logo.png")  # Call the logo
st.set_page_config(page_title="Conflict Plan Generator")
st.title("✈️ Conflict Plan Generator")
st.subheader("Ownership Aircraft Parameters")

tcpa = st.number_input("TCPA (s)", value=60.0)
cpa_dist = st.number_input("CPA Distance (m)", value=200.0)
os_lat = st.number_input("Ownership Latitude", value=37.618805)
os_lon = st.number_input("Ownership Longitude", value=-122.375416)
os_alt = st.number_input("Ownership Altitude (m)", value=50.0)
os_course = st.number_input("Ownership Course (deg)", value=90.0)
os_speed = st.number_input("Ownership Speed (m/s)", value=20.0)
os_vspeed = st.number_input("Ownership Vertical Speed (m/s)", value=1.0)

st.subheader("Target Aircraft Parameters")

rel_speed = st.number_input("Relative Speed (m/s)", value=10.0)
conflict_dh = st.number_input("Conflict Altitude Diff (m)", value=30.0)
tgt_alt_offset = st.number_input("Target Alt Offset (m)", value=50.0)

cpa_side = st.radio("CPA Side", ["left", "right"])

if st.button("✅ Generate .plan Files"):
    try:
        points = compute_conflict_geometry(
        tcpa_sec=tcpa,
        cpa_horiz_m=cpa_dist,
        os_lat_deg=os_lat,
        os_lon_deg=os_lon,
        os_alt_m=os_alt,
        os_course_deg=os_course,
        os_speed_mps=os_speed,
        os_vspeed_mps=os_vspeed,
        rel_speed_mps=rel_speed,
        conflict_dh_m=conflict_dh,
        target_alt0_m=tgt_alt_offset,
        cpa_side=cpa_side
        )
        home_position = points["os_start"]
        write_plan_file("ownership.plan", [points["os_start"], points["os_cpa"], points["os_start"]], home_position)
        write_plan_file("target.plan", [points["tgt_start"], points["tgt_cpa"], points["tgt_start"]], home_position)

        st.success("✅ .plan files generated: ownership.plan & target.plan")
        
        with open("ownership.plan", "rb") as f:
            st.download_button("Download Ownership Plan", f, file_name="ownership.plan")

        with open("target.plan", "rb") as f:
            st.download_button("Download Target Plan", f, file_name="target.plan")

        
    except Exception as e:
        st.error(f"❌ Error: {e}")
