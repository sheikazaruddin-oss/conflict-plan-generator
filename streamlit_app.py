import streamlit as st
import base64
import zipfile
import io
import matplotlib.pyplot as plt
import pandas as pd

from conflict_math import (
    compute_conflict_geometry,
    compute_initial_positions_type2
)
from plan_writer import (
    write_plan_file,
    write_waypoints_file,
    write_kml_file,
    write_combined_kml_file
)
from yaml_writer import write_yaml_file
from scenario_package_writer import build_scenario_zip
from units import (
    ft_to_m,
    m_to_ft,
    kt_to_mps,
    mps_to_kt,
    fpm_to_mps
)
from validation_logger import save_validation_log


# -------------------------------------------------
# SESSION STATE
# -------------------------------------------------

if "files_generated" not in st.session_state:
    st.session_state.files_generated = False

if "generated_points" not in st.session_state:
    st.session_state.generated_points = None

if "files_generated_type2" not in st.session_state:
    st.session_state.files_generated_type2 = False

if "generated_points_type2" not in st.session_state:
    st.session_state.generated_points_type2 = None


# -------------------------------------------------
# SCENARIO PACKAGE SESSION STATE
# -------------------------------------------------

if "scenario_zip_tct" not in st.session_state:
    st.session_state.scenario_zip_tct = None

if "scenario_zip_name_tct" not in st.session_state:
    st.session_state.scenario_zip_name_tct = None

if "scenario_zip_tct_plus" not in st.session_state:
    st.session_state.scenario_zip_tct_plus = None

if "scenario_zip_name_tct_plus" not in st.session_state:
    st.session_state.scenario_zip_name_tct_plus = None


# -------------------------------------------------
# TIME CONVERSION
# -------------------------------------------------

def mmss_to_sec(mmss: str) -> int:

    mmss = mmss.strip()
    parts = mmss.split(":")

    if len(parts) != 2:
        raise ValueError(
            "TCPA must be in mm:ss format (example: 01:30)"
        )

    minutes = int(parts[0])
    seconds = int(parts[1])

    if seconds < 0 or seconds >= 60:
        raise ValueError(
            "Seconds must be between 0 and 59"
        )

    return minutes * 60 + seconds


# -------------------------------------------------
# CPA VISUALIZATION
# -------------------------------------------------

def plot_cpa_encounter(points):

    os_start = points["os_start"]
    os_cpa = points["os_cpa"]
    os_end = points["os_end"]

    tgt_start = points["tgt_start"]
    tgt_cpa = points["tgt_cpa"]
    tgt_end = points["tgt_end"]

    x_os = [
        os_start[1],
        os_cpa[1],
        os_end[1]
    ]

    y_os = [
        os_start[0],
        os_cpa[0],
        os_end[0]
    ]

    x_tgt = [
        tgt_start[1],
        tgt_cpa[1],
        tgt_end[1]
    ]

    y_tgt = [
        tgt_start[0],
        tgt_cpa[0],
        tgt_end[0]
    ]

    fig, ax = plt.subplots(figsize=(7, 7))

    ax.plot(
        x_os,
        y_os,
        marker="o",
        label="Ownship Path"
    )

    ax.plot(
        x_tgt,
        y_tgt,
        marker="o",
        label="Target Path"
    )

    ax.annotate(
        "OS Start",
        (os_start[1], os_start[0]),
        xytext=(-25, 10),
        textcoords="offset points"
    )

    ax.annotate(
        "TGT Start",
        (tgt_start[1], tgt_start[0]),
        xytext=(10, -15),
        textcoords="offset points"
    )

    ax.scatter(
        os_cpa[1],
        os_cpa[0],
        s=120,
        marker="X",
        color="black"
    )

    ax.annotate(
        "CPA",
        (os_cpa[1], os_cpa[0]),
        xytext=(10, 10),
        textcoords="offset points"
    )

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("CPA Encounter Visualization")

    ax.legend()
    ax.grid(True)

    all_lon = x_os + x_tgt
    all_lat = y_os + y_tgt

    margin = 0.01

    ax.set_xlim(
        min(all_lon) - margin,
        max(all_lon) + margin
    )

    ax.set_ylim(
        min(all_lat) - margin,
        max(all_lat) + margin
    )

    ax.ticklabel_format(
        useOffset=False,
        style="plain"
    )

    return fig


# -------------------------------------------------
# LOGO
# -------------------------------------------------

def show_logo_top_left(image_path, width=120):

    with open(image_path, "rb") as image_file:
        encoded = base64.b64encode(
            image_file.read()
        ).decode()

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
            <img
                src="data:image/png;base64,{encoded}"
                width="{width}"
            >
        </div>
        """,
        unsafe_allow_html=True
    )


show_logo_top_left("logo.png")


# -------------------------------------------------
# PAGE
# -------------------------------------------------

st.set_page_config(
    page_title="Conflict Plan Generator"
)

st.title("✈ Conflict Plan Generator")

tab1, tab2 = st.tabs([
    "TCT",
    "TCT+"
])


# =========================================================
# ===================== TYPE 1 =============================
# =========================================================

with tab1:

    # -------------------------------------------------
    # CALLSIGN INPUTS
    # -------------------------------------------------

    os_callsign = st.text_input(
        "Ownship Callsign",
        value="OWN01"
    )

    tgt_callsign = st.text_input(
        "Target Callsign",
        value="TGT01"
    )


    # -------------------------------------------------
    # SCENARIO PACKAGE INPUTS
    # -------------------------------------------------

    scenario_name = st.text_input(
        "Scenario:",
        value="",
        placeholder="Enter scenario name",
        key="tct_scenario_name"
    )

    st.subheader(
        "Scenario Package Configuration"
    )

    ownship_sysid = st.number_input(
        "Ownship SysID",
        min_value=1,
        max_value=255,
        value=1,
        step=1,
        key="tct_ownship_sysid"
    )

    target_sysid = st.number_input(
        "Target SysID",
        min_value=1,
        max_value=255,
        value=2,
        step=1,
        key="tct_target_sysid"
    )

    ownship_to_waypoint_index = st.number_input(
        "Ownship To Waypoint Index",
        min_value=0,
        value=3,
        step=1,
        key="tct_ownship_to_waypoint_index"
    )

    target_to_waypoint_index = st.number_input(
        "Target To Waypoint Index",
        min_value=0,
        value=2,
        step=1,
        key="tct_target_to_waypoint_index"
    )


    # -------------------------------------------------
    # OWNSHIP INPUTS
    # -------------------------------------------------

    st.subheader(
        "Ownship Aircraft Parameters"
    )

    tcpa_mmss = st.text_input(
        "TCPA (mm:ss)",
        value="01:00"
    )

    post_cpa_mmss = st.text_input(
        "Post-CPA Time (mm:ss)",
        value="10:00"
    )

    cpa_dist_ft = st.number_input(
        "CPA Distance (ft)",
        value=20
    )

    os_lat = st.number_input(
        "Ownship Latitude",
        value=37.618805,
        format="%.6f"
    )

    os_lon = st.number_input(
        "Ownship Longitude",
        value=-122.375416,
        format="%.6f"
    )

    os_alt_ft = st.number_input(
        "Ownship Altitude (ft)",
        value=50
    )

    os_course = st.number_input(
        "Ownship Course (deg)",
        value=90.0
    )

    os_speed_kt = st.number_input(
        "Ownship Speed (kt)",
        value=20
    )

    os_vspeed_fpm = st.number_input(
        "Ownship Vertical Speed (ft/min)",
        value=1
    )


    # -------------------------------------------------
    # TARGET INPUTS
    # -------------------------------------------------

    st.subheader(
        "Target Aircraft Parameters"
    )

    rel_speed_kt = st.number_input(
        "Relative Speed (kt)",
        value=10
    )

    conflict_dh_ft = st.number_input(
        "Conflict Relative Altitude (ft)",
        value=30
    )

    tgt_alt_offset_ft = st.number_input(
        "Target Alt Offset (ft)",
        value=20
    )

    relative_heading = st.number_input(
        "Relative Heading (deg)",
        value=95.0
    )


    # -------------------------------------------------
    # GENERATE FILES
    # -------------------------------------------------

    if st.button(
        "Generate Plan Files",
        key="t1_generate"
    ):

        try:

            st.session_state.files_generated = True

            tcpa_sec = mmss_to_sec(
                tcpa_mmss
            )

            post_cpa_sec = mmss_to_sec(
                post_cpa_mmss
            )

            cpa_dist_m = ft_to_m(
                cpa_dist_ft
            )

            os_alt_m = ft_to_m(
                os_alt_ft
            )

            os_speed_mps = kt_to_mps(
                os_speed_kt
            )

            os_vspeed_mps = fpm_to_mps(
                os_vspeed_fpm
            )

            rel_speed_mps = kt_to_mps(
                rel_speed_kt
            )

            conflict_dh_m = ft_to_m(
                conflict_dh_ft
            )

            tgt_alt_offset_m = ft_to_m(
                tgt_alt_offset_ft
            )

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
                post_cpa_sec=post_cpa_sec
            )

            positions_df = pd.DataFrame([
                {
                    "start_lat": points["os_start"][0],
                    "start_lon": points["os_start"][1],
                    "start_alt": points["os_start"][2],

                    "end_lat": points["os_end"][0],
                    "end_lon": points["os_end"][1],
                    "end_alt": points["os_end"][2],

                    "gspeed": os_speed_kt,
                    "vspeed": os_vspeed_fpm,
                    "course": os_course
                },
                {
                    "start_lat": points["tgt_start"][0],
                    "start_lon": points["tgt_start"][1],
                    "start_alt": points["tgt_start"][2],

                    "end_lat": points["tgt_end"][0],
                    "end_lon": points["tgt_end"][1],
                    "end_alt": points["tgt_end"][2],

                    "gspeed": (
                        os_speed_kt
                        + rel_speed_kt
                    ),
                    "vspeed": 0.0,
                    "course": points[
                        "tgt_course_deg"
                    ]
                }
            ])

            positions_df.to_csv(
                "positions.csv",
                index=False
            )

            print(
                "positions.csv generated successfully"
            )

            st.session_state.generated_points = points


            # -------------------------------------------------
            # FILENAMES
            # -------------------------------------------------

            ownship_plan = (
                f"Ownship_{os_callsign}.plan"
            )

            target_plan = (
                f"Target_{tgt_callsign}.plan"
            )

            ownship_wp = (
                f"Ownship_{os_callsign}.waypoints"
            )

            target_wp = (
                f"Target_{tgt_callsign}.waypoints"
            )

            ownship_yaml = (
                f"Ownship_{os_callsign}.yaml"
            )

            target_yaml = (
                f"Target_{tgt_callsign}.yaml"
            )

            ownship_kml = (
                f"Ownship_{os_callsign}.kml"
            )

            target_kml = (
                f"Target_{tgt_callsign}.kml"
            )

            combined_kml = (
                f"Ownship_{os_callsign}_"
                f"Target_{tgt_callsign}.kml"
            )


            # -------------------------------------------------
            # VALIDATION LOG
            # -------------------------------------------------

            save_validation_log(
                "scenario_log.json",
                {
                    "tcpa_mmss": tcpa_mmss,
                    "tcpa_sec": tcpa_sec,
                    "cpa_ft": cpa_dist_ft
                },
                points,
                tcpa_sec
            )


            # -------------------------------------------------
            # EXISTING FILE GENERATION
            # -------------------------------------------------

            home = points["os_start"]

            write_plan_file(
                ownship_plan,
                [
                    points["os_start"],
                    points["os_cpa"],
                    points["os_end"]
                ],
                home
            )

            write_plan_file(
                target_plan,
                [
                    points["tgt_start"],
                    points["tgt_cpa"],
                    points["tgt_end"]
                ],
                home
            )

            write_waypoints_file(
                ownship_wp,
                [
                    points["os_start"],
                    points["os_cpa"],
                    points["os_end"]
                ]
            )

            write_waypoints_file(
                target_wp,
                [
                    points["tgt_start"],
                    points["tgt_cpa"],
                    points["tgt_end"]
                ]
            )


            # -------------------------------------------------
            # INDEPENDENT TCT SCENARIO PACKAGE
            # -------------------------------------------------

            target_start_for_package = (
                points["tgt_start"]
            )

            target_alt_ft_for_package = round(
                m_to_ft(
                    target_start_for_package[2]
                ),
                2
            )

            target_speed_kt_for_package = (
                os_speed_kt
                + rel_speed_kt
            )

            scenario_zip_data = build_scenario_zip(
                scenario_name=scenario_name,

                ownship_callsign=os_callsign,
                target_callsign=tgt_callsign,

                ownship_sysid=ownship_sysid,
                target_sysid=target_sysid,

                ownship_lat_deg=points["os_start"][0],
                ownship_lon_deg=points["os_start"][1],
                ownship_alt_ft=os_alt_ft,
                ownship_course_deg=points[
                    "os_course_deg"
                ],
                ownship_speed_kt=os_speed_kt,
                ownship_vertical_speed_fpm=(
                    os_vspeed_fpm
                ),

                target_lat_deg=(
                    target_start_for_package[0]
                ),
                target_lon_deg=(
                    target_start_for_package[1]
                ),
                target_alt_ft=(
                    target_alt_ft_for_package
                ),
                target_course_deg=points[
                    "tgt_course_deg"
                ],
                target_speed_kt=(
                    target_speed_kt_for_package
                ),
                target_vertical_speed_fpm=0.0,

                ownship_to_waypoint_index=(
                    ownship_to_waypoint_index
                ),
                target_to_waypoint_index=(
                    target_to_waypoint_index
                ),

                existing_ownship_waypoints_path=(
                    ownship_wp
                ),
                existing_target_waypoints_path=(
                    target_wp
                )
            )

            st.session_state.scenario_zip_tct = (
                scenario_zip_data
            )

            st.session_state.scenario_zip_name_tct = (
                f"{scenario_name.strip()}.zip"
            )


            # -------------------------------------------------
            # EXISTING KML GENERATION
            # -------------------------------------------------

            write_kml_file(
                ownship_kml,
                [
                    points["os_start"],
                    points["os_cpa"],
                    points["os_end"]
                ]
            )

            write_kml_file(
                target_kml,
                [
                    points["tgt_start"],
                    points["tgt_cpa"],
                    points["tgt_end"]
                ]
            )

            write_combined_kml_file(
                combined_kml,
                [
                    points["os_start"],
                    points["os_cpa"],
                    points["os_end"]
                ],
                [
                    points["tgt_start"],
                    points["tgt_cpa"],
                    points["tgt_end"]
                ]
            )


            # -------------------------------------------------
            # EXISTING YAML GENERATION
            # -------------------------------------------------

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

            tgt_alt_ft = round(
                m_to_ft(
                    tgt_start[2]
                ),
                2
            )

            write_yaml_file(
                path=target_yaml,
                callsign=tgt_callsign,
                sysid=2,
                lat_deg=tgt_start[0],
                lon_deg=tgt_start[1],
                alt_ft=tgt_alt_ft,
                course_deg=points[
                    "tgt_course_deg"
                ],
                ground_speed_kt=round(
                    mps_to_kt(
                        rel_speed_mps
                    ),
                    2
                ),
                vertical_speed_fpm=0.0,
                waypoints_file=target_wp
            )

            st.success(
                "All files generated successfully!"
            )

        except Exception as e:

            st.session_state.files_generated = False
            st.session_state.scenario_zip_tct = None
            st.session_state.scenario_zip_name_tct = None

            st.error(
                f"Error: {e}"
            )


    # -------------------------------------------------
    # GRAPH
    # -------------------------------------------------

    if (
        st.session_state.generated_points
        is not None
    ):

        st.markdown("---")
        st.subheader(
            "CPA Encounter Visualization"
        )

        fig = plot_cpa_encounter(
            st.session_state.generated_points
        )

        st.pyplot(fig)


    # -------------------------------------------------
    # DOWNLOAD BUTTONS
    # -------------------------------------------------

    if st.session_state.files_generated:

        ownship_plan = (
            f"Ownship_{os_callsign}.plan"
        )

        target_plan = (
            f"Target_{tgt_callsign}.plan"
        )

        ownship_wp = (
            f"Ownship_{os_callsign}.waypoints"
        )

        target_wp = (
            f"Target_{tgt_callsign}.waypoints"
        )

        ownship_yaml = (
            f"Ownship_{os_callsign}.yaml"
        )

        target_yaml = (
            f"Target_{tgt_callsign}.yaml"
        )

        ownship_kml = (
            f"Ownship_{os_callsign}.kml"
        )

        target_kml = (
            f"Target_{tgt_callsign}.kml"
        )

        combined_kml = (
            f"Ownship_{os_callsign}_"
            f"Target_{tgt_callsign}.kml"
        )


        # -------------------------------------------------
        # PLAN DOWNLOAD
        # -------------------------------------------------

        st.markdown("---")
        st.subheader(".PLAN FILES")

        plan_zip = io.BytesIO()

        with zipfile.ZipFile(
            plan_zip,
            "w"
        ) as z:

            z.write(
                ownship_plan
            )

            z.write(
                target_plan
            )

        st.download_button(
            "Download Plan Files",
            plan_zip.getvalue(),
            "plan_files.zip",
            key="t1_plan"
        )


        # -------------------------------------------------
        # WAYPOINT DOWNLOAD
        # -------------------------------------------------

        st.markdown("---")
        st.subheader(".WAYPOINT FILES")

        wp_zip = io.BytesIO()

        with zipfile.ZipFile(
            wp_zip,
            "w"
        ) as z:

            z.write(
                ownship_wp
            )

            z.write(
                target_wp
            )

        st.download_button(
            "Download Waypoint Files",
            wp_zip.getvalue(),
            "waypoints.zip",
            key="t1_wp"
        )


        # -------------------------------------------------
        # YAML DOWNLOAD
        # -------------------------------------------------

        st.markdown("---")
        st.subheader(".YAML FILES")

        yaml_zip = io.BytesIO()

        with zipfile.ZipFile(
            yaml_zip,
            "w"
        ) as z:

            z.write(
                ownship_yaml
            )

            z.write(
                target_yaml
            )

        st.download_button(
            "Download YAML Files",
            data=yaml_zip.getvalue(),
            file_name="yaml_files.zip",
            mime="application/zip",
            key="t1_yaml"
        )


        # -------------------------------------------------
        # KML DOWNLOAD
        # -------------------------------------------------

        st.markdown("---")
        st.subheader(".KML FILES")

        kml_zip = io.BytesIO()

        with zipfile.ZipFile(
            kml_zip,
            "w"
        ) as z:

            z.write(
                ownship_kml
            )

            z.write(
                target_kml
            )

            z.write(
                combined_kml
            )

        st.download_button(
            "Download KML Files",
            data=kml_zip.getvalue(),
            file_name="kml_files.zip",
            mime="application/zip",
            key="t1_kml"
        )


        # -------------------------------------------------
        # VALIDATION LOG DOWNLOAD
        # -------------------------------------------------

        with open(
            "scenario_log.json",
            "rb"
        ) as f:

            st.markdown("---")
            st.subheader(
                "VALIDATION LOG"
            )

            st.download_button(
                "Download Validation Log",
                f,
                "scenario_log.json",
                key="t1_log"
            )


        # -------------------------------------------------
        # POSITIONS DOWNLOAD
        # -------------------------------------------------

        st.markdown("---")
        st.subheader(
            "POSITIONS FILE (FOR WORLD PLOT)"
        )

        with open(
            "positions.csv",
            "rb"
        ) as f:

            st.download_button(
                "Download positions.csv",
                data=f,
                file_name="positions.csv",
                mime="text/csv",
                key="t1_csv"
            )


        # -------------------------------------------------
        # TCT SCENARIO PACKAGE DOWNLOAD
        # -------------------------------------------------

        if (
            st.session_state.scenario_zip_tct
            is not None
        ):

            st.markdown("---")
            st.subheader(
                "SCENARIO PACKAGE"
            )

            st.download_button(
                label="Download Scenario Package",
                data=(
                    st.session_state
                    .scenario_zip_tct
                ),
                file_name=(
                    st.session_state
                    .scenario_zip_name_tct
                ),
                mime="application/zip",
                key=(
                    "tct_scenario_package_download"
                )
            )


# =========================================================
# ===================== TYPE 2 =============================
# =========================================================

with tab2:

    # -------------------------------------------------
    # CALLSIGN INPUTS
    # -------------------------------------------------

    os_callsign_t2 = st.text_input(
        "Ownship Callsign",
        value="OWN01",
        key="t2_os_callsign"
    )

    tgt_callsign_t2 = st.text_input(
        "Target Callsign",
        value="TGT01",
        key="t2_tgt_callsign"
    )


    # -------------------------------------------------
    # SCENARIO PACKAGE INPUTS
    # -------------------------------------------------

    scenario_name_t2 = st.text_input(
        "Scenario:",
        value="",
        placeholder="Enter scenario name",
        key="tct_plus_scenario_name"
    )

    st.subheader(
        "Scenario Package Configuration"
    )

    ownship_sysid_t2 = st.number_input(
        "Ownship SysID",
        min_value=1,
        max_value=255,
        value=1,
        step=1,
        key="tct_plus_ownship_sysid"
    )

    target_sysid_t2 = st.number_input(
        "Target SysID",
        min_value=1,
        max_value=255,
        value=2,
        step=1,
        key="tct_plus_target_sysid"
    )

    ownship_to_waypoint_index_t2 = (
        st.number_input(
            "Ownship To Waypoint Index",
            min_value=0,
            value=3,
            step=1,
            key=(
                "tct_plus_ownship_"
                "to_waypoint_index"
            )
        )
    )

    target_to_waypoint_index_t2 = (
        st.number_input(
            "Target To Waypoint Index",
            min_value=0,
            value=2,
            step=1,
            key=(
                "tct_plus_target_"
                "to_waypoint_index"
            )
        )
    )


    # -------------------------------------------------
    # TYPE 2 INPUTS
    # -------------------------------------------------

    st.subheader(
        "Ownship Path Inputs"
    )

    tcpa_mmss_t2 = st.text_input(
        "TCPA (mm:ss)",
        value="01:00",
        key="t2_tcpa"
    )

    post_cpa_mmss_t2 = st.text_input(
        "Post-CPA Time (mm:ss)",
        value="10:00",
        key="t2_post_cpa"
    )

    cpa_lat_t2 = st.number_input(
        "CPA Latitude",
        value=37.618805,
        format="%.6f",
        key="t2_cpa_lat"
    )

    cpa_lon_t2 = st.number_input(
        "CPA Longitude",
        value=-122.375416,
        format="%.6f",
        key="t2_cpa_lon"
    )

    os_path_start_lat = st.number_input(
        "Ownship Path Start Latitude",
        value=37.610000,
        format="%.6f",
        key="t2_os_path_start_lat"
    )

    os_path_start_lon = st.number_input(
        "Ownship Path Start Longitude",
        value=-122.390000,
        format="%.6f",
        key="t2_os_path_start_lon"
    )

    os_path_end_lat = st.number_input(
        "Ownship Path End Latitude",
        value=37.630000,
        format="%.6f",
        key="t2_os_path_end_lat"
    )

    os_path_end_lon = st.number_input(
        "Ownship Path End Longitude",
        value=-122.360000,
        format="%.6f",
        key="t2_os_path_end_lon"
    )

    os_speed_kt_t2 = st.number_input(
        "Ownship Speed (kt)",
        value=20.0,
        key="t2_os_speed"
    )

    os_alt_ft_t2 = st.number_input(
        "Ownship Altitude (ft)",
        value=50.0,
        key="t2_os_alt"
    )

    os_vspeed_fpm_t2 = st.number_input(
        "Ownship Vertical Speed (ft/min)",
        value=0.0,
        key="t2_os_vspeed"
    )

    st.subheader(
        "Target Path Inputs"
    )

    tgt_path_start_lat = st.number_input(
        "Target Path Start Latitude",
        value=37.630000,
        format="%.6f",
        key="t2_tgt_path_start_lat"
    )

    tgt_path_start_lon = st.number_input(
        "Target Path Start Longitude",
        value=-122.360000,
        format="%.6f",
        key="t2_tgt_path_start_lon"
    )

    tgt_path_end_lat = st.number_input(
        "Target Path End Latitude",
        value=37.600000,
        format="%.6f",
        key="t2_tgt_path_end_lat"
    )

    tgt_path_end_lon = st.number_input(
        "Target Path End Longitude",
        value=-122.390000,
        format="%.6f",
        key="t2_tgt_path_end_lon"
    )

    tgt_speed_kt_t2 = st.number_input(
        "Target Speed (kt)",
        value=25.0,
        key="t2_tgt_speed"
    )

    conflict_dh_ft_t2 = st.number_input(
        "Conflict Relative Altitude (ft)",
        value=30.0,
        key="t2_conflict_dh"
    )

    tgt_alt_offset_ft_t2 = st.number_input(
        "Target Alt Offset (ft)",
        value=20.0,
        key="t2_tgt_alt_offset"
    )


    # -------------------------------------------------
    # GENERATE FILES
    # -------------------------------------------------

    if st.button(
        "Generate Plan File",
        key="t2_generate"
    ):

        try:

            st.session_state.files_generated_type2 = True

            tcpa_sec_t2 = mmss_to_sec(
                tcpa_mmss_t2
            )

            post_cpa_sec_t2 = mmss_to_sec(
                post_cpa_mmss_t2
            )

            os_speed_mps_t2 = kt_to_mps(
                os_speed_kt_t2
            )

            tgt_speed_mps_t2 = kt_to_mps(
                tgt_speed_kt_t2
            )

            os_alt_m_t2 = ft_to_m(
                os_alt_ft_t2
            )

            os_vspeed_mps_t2 = fpm_to_mps(
                os_vspeed_fpm_t2
            )

            conflict_dh_m_t2 = ft_to_m(
                conflict_dh_ft_t2
            )

            tgt_alt_offset_m_t2 = ft_to_m(
                tgt_alt_offset_ft_t2
            )

            init_t2 = compute_initial_positions_type2(
                tcpa_sec=tcpa_sec_t2,
                cpa_lat=cpa_lat_t2,
                cpa_lon=cpa_lon_t2,

                os_s_lat=os_path_start_lat,
                os_s_lon=os_path_start_lon,
                os_e_lat=os_path_end_lat,
                os_e_lon=os_path_end_lon,

                tgt_s_lat=tgt_path_start_lat,
                tgt_s_lon=tgt_path_start_lon,
                tgt_e_lat=tgt_path_end_lat,
                tgt_e_lon=tgt_path_end_lon,

                os_speed_mps=os_speed_mps_t2,
                tgt_speed_mps=tgt_speed_mps_t2
            )

            os_init_lat_t2 = (
                init_t2["os_init"][0]
            )

            os_init_lon_t2 = (
                init_t2["os_init"][1]
            )

            tgt_init_lat_t2 = (
                init_t2["tgt_init"][0]
            )

            tgt_init_lon_t2 = (
                init_t2["tgt_init"][1]
            )

            os_course_t2 = (
                init_t2["os_course_deg"]
            )

            tgt_course_t2 = (
                init_t2["tgt_course_deg"]
            )

            relative_heading_t2 = (
                tgt_course_t2
                - os_course_t2
                + 360.0
            ) % 360.0

            rel_speed_mps_t2 = (
                tgt_speed_mps_t2
                - os_speed_mps_t2
            )

            points_t2 = compute_conflict_geometry(
                tcpa_sec=tcpa_sec_t2,
                cpa_horiz_m=0.0,

                os_lat_deg=os_init_lat_t2,
                os_lon_deg=os_init_lon_t2,
                os_alt_m=os_alt_m_t2,
                os_course_deg=os_course_t2,
                os_speed_mps=os_speed_mps_t2,
                os_vspeed_mps=os_vspeed_mps_t2,

                rel_speed_mps=rel_speed_mps_t2,
                conflict_dh_m=conflict_dh_m_t2,
                target_alto_m=tgt_alt_offset_m_t2,
                relative_heading_deg=(
                    relative_heading_t2
                ),
                post_cpa_sec=post_cpa_sec_t2
            )

            st.session_state.generated_points_type2 = (
                points_t2
            )

            positions_df_t2 = pd.DataFrame([
                {
                    "start_lat": (
                        points_t2["os_start"][0]
                    ),
                    "start_lon": (
                        points_t2["os_start"][1]
                    ),
                    "start_alt": (
                        points_t2["os_start"][2]
                    ),

                    "end_lat": (
                        points_t2["os_end"][0]
                    ),
                    "end_lon": (
                        points_t2["os_end"][1]
                    ),
                    "end_alt": (
                        points_t2["os_end"][2]
                    ),

                    "gspeed": os_speed_kt_t2,
                    "vspeed": os_vspeed_fpm_t2,
                    "course": os_course_t2
                },
                {
                    "start_lat": (
                        points_t2["tgt_start"][0]
                    ),
                    "start_lon": (
                        points_t2["tgt_start"][1]
                    ),
                    "start_alt": (
                        points_t2["tgt_start"][2]
                    ),

                    "end_lat": (
                        points_t2["tgt_end"][0]
                    ),
                    "end_lon": (
                        points_t2["tgt_end"][1]
                    ),
                    "end_alt": (
                        points_t2["tgt_end"][2]
                    ),

                    "gspeed": tgt_speed_kt_t2,
                    "vspeed": 0.0,
                    "course": tgt_course_t2
                }
            ])

            positions_df_t2.to_csv(
                "positions_type2.csv",
                index=False
            )

            save_validation_log(
                "scenario_log_type2.json",
                {
                    "tcpa_mmss": tcpa_mmss_t2,
                    "tcpa_sec": tcpa_sec_t2,
                    "cpa_lat": cpa_lat_t2,
                    "cpa_lon": cpa_lon_t2
                },
                points_t2,
                tcpa_sec_t2
            )


            # -------------------------------------------------
            # FILENAMES
            # -------------------------------------------------

            ownship_plan_t2 = (
                f"Ownship_{os_callsign_t2}.plan"
            )

            target_plan_t2 = (
                f"Target_{tgt_callsign_t2}.plan"
            )

            ownship_wp_t2 = (
                f"Ownship_{os_callsign_t2}.waypoints"
            )

            target_wp_t2 = (
                f"Target_{tgt_callsign_t2}.waypoints"
            )

            ownship_yaml_t2 = (
                f"Ownship_{os_callsign_t2}.yaml"
            )

            target_yaml_t2 = (
                f"Target_{tgt_callsign_t2}.yaml"
            )

            ownship_kml_t2 = (
                f"Ownship_{os_callsign_t2}.kml"
            )

            target_kml_t2 = (
                f"Target_{tgt_callsign_t2}.kml"
            )

            combined_kml_t2 = (
                f"Ownship_{os_callsign_t2}_"
                f"Target_{tgt_callsign_t2}.kml"
            )

            home_t2 = (
                points_t2["os_start"]
            )


            # -------------------------------------------------
            # EXISTING FILE GENERATION
            # -------------------------------------------------

            write_plan_file(
                ownship_plan_t2,
                [
                    points_t2["os_start"],
                    points_t2["os_cpa"],
                    points_t2["os_end"]
                ],
                home_t2
            )

            write_plan_file(
                target_plan_t2,
                [
                    points_t2["tgt_start"],
                    points_t2["tgt_cpa"],
                    points_t2["tgt_end"]
                ],
                home_t2
            )

            write_waypoints_file(
                ownship_wp_t2,
                [
                    points_t2["os_start"],
                    points_t2["os_cpa"],
                    points_t2["os_end"]
                ]
            )

            write_waypoints_file(
                target_wp_t2,
                [
                    points_t2["tgt_start"],
                    points_t2["tgt_cpa"],
                    points_t2["tgt_end"]
                ]
            )


            # -------------------------------------------------
            # INDEPENDENT TCT+ SCENARIO PACKAGE
            # -------------------------------------------------

            target_start_for_package_t2 = (
                points_t2["tgt_start"]
            )

            target_alt_ft_for_package_t2 = round(
                m_to_ft(
                    target_start_for_package_t2[2]
                ),
                2
            )

            scenario_zip_data_t2 = (
                build_scenario_zip(
                    scenario_name=scenario_name_t2,

                    ownship_callsign=os_callsign_t2,
                    target_callsign=tgt_callsign_t2,

                    ownship_sysid=ownship_sysid_t2,
                    target_sysid=target_sysid_t2,

                    ownship_lat_deg=(
                        points_t2["os_start"][0]
                    ),
                    ownship_lon_deg=(
                        points_t2["os_start"][1]
                    ),
                    ownship_alt_ft=os_alt_ft_t2,
                    ownship_course_deg=(
                        points_t2["os_course_deg"]
                    ),
                    ownship_speed_kt=os_speed_kt_t2,
                    ownship_vertical_speed_fpm=(
                        os_vspeed_fpm_t2
                    ),

                    target_lat_deg=(
                        target_start_for_package_t2[0]
                    ),
                    target_lon_deg=(
                        target_start_for_package_t2[1]
                    ),
                    target_alt_ft=(
                        target_alt_ft_for_package_t2
                    ),
                    target_course_deg=(
                        points_t2["tgt_course_deg"]
                    ),
                    target_speed_kt=tgt_speed_kt_t2,
                    target_vertical_speed_fpm=0.0,

                    ownship_to_waypoint_index=(
                        ownship_to_waypoint_index_t2
                    ),
                    target_to_waypoint_index=(
                        target_to_waypoint_index_t2
                    ),

                    existing_ownship_waypoints_path=(
                        ownship_wp_t2
                    ),
                    existing_target_waypoints_path=(
                        target_wp_t2
                    )
                )
            )

            st.session_state.scenario_zip_tct_plus = (
                scenario_zip_data_t2
            )

            st.session_state.scenario_zip_name_tct_plus = (
                f"{scenario_name_t2.strip()}.zip"
            )


            # -------------------------------------------------
            # EXISTING KML GENERATION
            # -------------------------------------------------

            write_kml_file(
                ownship_kml_t2,
                [
                    points_t2["os_start"],
                    points_t2["os_cpa"],
                    points_t2["os_end"]
                ]
            )

            write_kml_file(
                target_kml_t2,
                [
                    points_t2["tgt_start"],
                    points_t2["tgt_cpa"],
                    points_t2["tgt_end"]
                ]
            )

            write_combined_kml_file(
                combined_kml_t2,
                [
                    points_t2["os_start"],
                    points_t2["os_cpa"],
                    points_t2["os_end"]
                ],
                [
                    points_t2["tgt_start"],
                    points_t2["tgt_cpa"],
                    points_t2["tgt_end"]
                ]
            )


            # -------------------------------------------------
            # EXISTING YAML GENERATION
            # -------------------------------------------------

            write_yaml_file(
                path=ownship_yaml_t2,
                callsign=os_callsign_t2,
                sysid=1,
                lat_deg=os_init_lat_t2,
                lon_deg=os_init_lon_t2,
                alt_ft=os_alt_ft_t2,
                course_deg=os_course_t2,
                ground_speed_kt=os_speed_kt_t2,
                vertical_speed_fpm=os_vspeed_fpm_t2,
                waypoints_file=ownship_wp_t2
            )

            tgt_start_t2 = (
                points_t2["tgt_start"]
            )

            tgt_alt_ft_t2 = round(
                m_to_ft(
                    tgt_start_t2[2]
                ),
                2
            )

            write_yaml_file(
                path=target_yaml_t2,
                callsign=tgt_callsign_t2,
                sysid=2,
                lat_deg=tgt_start_t2[0],
                lon_deg=tgt_start_t2[1],
                alt_ft=tgt_alt_ft_t2,
                course_deg=tgt_course_t2,
                ground_speed_kt=tgt_speed_kt_t2,
                vertical_speed_fpm=0.0,
                waypoints_file=target_wp_t2
            )

            st.success(
                "Files generated successfully!"
            )

        except Exception as e:

            st.session_state.files_generated_type2 = False
            st.session_state.scenario_zip_tct_plus = None
            st.session_state.scenario_zip_name_tct_plus = None

            st.error(
                f"Error: {e}"
            )


    # -------------------------------------------------
    # GRAPH
    # -------------------------------------------------

    if (
        st.session_state.generated_points_type2
        is not None
    ):

        st.markdown("---")
        st.subheader(
            "CPA Encounter Visualization"
        )

        fig_t2 = plot_cpa_encounter(
            st.session_state.generated_points_type2
        )

        st.pyplot(fig_t2)


    # -------------------------------------------------
    # DOWNLOAD BUTTONS
    # -------------------------------------------------

    if st.session_state.files_generated_type2:

        ownship_plan_t2 = (
            f"Ownship_{os_callsign_t2}.plan"
        )

        target_plan_t2 = (
            f"Target_{tgt_callsign_t2}.plan"
        )

        ownship_wp_t2 = (
            f"Ownship_{os_callsign_t2}.waypoints"
        )

        target_wp_t2 = (
            f"Target_{tgt_callsign_t2}.waypoints"
        )

        ownship_yaml_t2 = (
            f"Ownship_{os_callsign_t2}.yaml"
        )

        target_yaml_t2 = (
            f"Target_{tgt_callsign_t2}.yaml"
        )

        ownship_kml_t2 = (
            f"Ownship_{os_callsign_t2}.kml"
        )

        target_kml_t2 = (
            f"Target_{tgt_callsign_t2}.kml"
        )

        combined_kml_t2 = (
            f"Ownship_{os_callsign_t2}_"
            f"Target_{tgt_callsign_t2}.kml"
        )


        # -------------------------------------------------
        # PLAN DOWNLOAD
        # -------------------------------------------------

        st.markdown("---")
        st.subheader(".PLAN FILES")

        plan_zip_t2 = io.BytesIO()

        with zipfile.ZipFile(
            plan_zip_t2,
            "w"
        ) as z:

            z.write(
                ownship_plan_t2
            )

            z.write(
                target_plan_t2
            )

        st.download_button(
            "Download Plan Files",
            plan_zip_t2.getvalue(),
            "plan_files.zip",
            key="t2_plan"
        )


        # -------------------------------------------------
        # WAYPOINT DOWNLOAD
        # -------------------------------------------------

        st.markdown("---")
        st.subheader(".WAYPOINT FILES")

        wp_zip_t2 = io.BytesIO()

        with zipfile.ZipFile(
            wp_zip_t2,
            "w"
        ) as z:

            z.write(
                ownship_wp_t2
            )

            z.write(
                target_wp_t2
            )

        st.download_button(
            "Download Waypoint Files",
            wp_zip_t2.getvalue(),
            "waypoints.zip",
            key="t2_wp"
        )


        # -------------------------------------------------
        # YAML DOWNLOAD
        # -------------------------------------------------

        st.markdown("---")
        st.subheader(".YAML FILES")

        yaml_zip_t2 = io.BytesIO()

        with zipfile.ZipFile(
            yaml_zip_t2,
            "w"
        ) as z:

            z.write(
                ownship_yaml_t2
            )

            z.write(
                target_yaml_t2
            )

        st.download_button(
            "Download YAML Files",
            data=yaml_zip_t2.getvalue(),
            file_name="yaml_files.zip",
            mime="application/zip",
            key="t2_yaml"
        )


        # -------------------------------------------------
        # KML DOWNLOAD
        # -------------------------------------------------

        st.markdown("---")
        st.subheader(".KML FILES")

        kml_zip_t2 = io.BytesIO()

        with zipfile.ZipFile(
            kml_zip_t2,
            "w"
        ) as z:

            z.write(
                ownship_kml_t2
            )

            z.write(
                target_kml_t2
            )

            z.write(
                combined_kml_t2
            )

        st.download_button(
            "Download KML Files",
            data=kml_zip_t2.getvalue(),
            file_name="kml_files.zip",
            mime="application/zip",
            key="t2_kml"
        )


        # -------------------------------------------------
        # VALIDATION LOG DOWNLOAD
        # -------------------------------------------------

        with open(
            "scenario_log_type2.json",
            "rb"
        ) as f:

            st.markdown("---")
            st.subheader(
                "VALIDATION LOG"
            )

            st.download_button(
                "Validation Log",
                f,
                "scenario_log.json",
                key="t2_log"
            )


        # -------------------------------------------------
        # POSITIONS DOWNLOAD
        # -------------------------------------------------

        st.markdown("---")
        st.subheader(
            "POSITIONS FILE (FOR WORLD PLOT)"
        )

        with open(
            "positions_type2.csv",
            "rb"
        ) as f:

            st.download_button(
                "Download positions.csv",
                data=f,
                file_name="positions.csv",
                mime="text/csv",
                key="t2_csv"
            )


        # -------------------------------------------------
        # TCT+ SCENARIO PACKAGE DOWNLOAD
        # -------------------------------------------------

        if (
            st.session_state.scenario_zip_tct_plus
            is not None
        ):

            st.markdown("---")
            st.subheader(
                "SCENARIO PACKAGE"
            )

            st.download_button(
                label="Download Scenario Package",
                data=(
                    st.session_state
                    .scenario_zip_tct_plus
                ),
                file_name=(
                    st.session_state
                    .scenario_zip_name_tct_plus
                ),
                mime="application/zip",
                key=(
                    "tct_plus_"
                    "scenario_package_download"
                )
            )
