import math
from units import m_to_ft


def meters_to_latlon(lato_deg, lono_deg, dx_m, dy_m):
    R = 6378137.0
    lato_rad = math.radians(lato_deg)

    dlat = dy_m / R
    dlon = dx_m / (R * math.cos(lato_rad))

    lat = lato_deg + math.degrees(dlat)
    lon = lono_deg + math.degrees(dlon)
    return lat, lon


def latlon_to_local_m(ref_lat_deg, ref_lon_deg, lat_deg, lon_deg):
    R = 6378137.0
    ref_lat_rad = math.radians(ref_lat_deg)

    dlat = math.radians(lat_deg - ref_lat_deg)
    dlon = math.radians(lon_deg - ref_lon_deg)

    dy_m = dlat * R
    dx_m = dlon * R * math.cos(ref_lat_rad)

    return dx_m, dy_m


def compute_conflict_geometry(
    tcpa_sec,
    cpa_horiz_m,
    os_lat_deg,
    os_lon_deg,
    os_alt_m,
    os_course_deg,
    os_speed_mps,
    os_vspeed_mps,
    rel_speed_mps,
    conflict_dh_m,
    target_alto_m,
    relative_heading_deg,
    post_cpa_sec=0
):

    os_course_rad = math.radians(os_course_deg % 360.0)

    vx_os = os_speed_mps * math.sin(os_course_rad)
    vy_os = os_speed_mps * math.cos(os_course_rad)
    vz_os = os_vspeed_mps

    dx_os = vx_os * tcpa_sec
    dy_os = vy_os * tcpa_sec
    dz_os = vz_os * tcpa_sec

    os_alt_cpa = os_alt_m + dz_os

    tgt_course_deg = (os_course_deg + (relative_heading_deg % 360.0)) % 360.0
    tgt_course_rad = math.radians(tgt_course_deg)

    tgt_speed_mps = os_speed_mps + rel_speed_mps

    vx_tgt = tgt_speed_mps * math.sin(tgt_course_rad)
    vy_tgt = tgt_speed_mps * math.cos(tgt_course_rad)

    if abs(tcpa_sec) < 1e-9:
        vz_tgt = vz_os
    else:
        vz_tgt = vz_os + ((conflict_dh_m - target_alto_m) / tcpa_sec)

    dz_tgt = vz_tgt * tcpa_sec
    dx_tgt = vx_tgt * tcpa_sec
    dy_tgt = vy_tgt * tcpa_sec

    vx_rel = vx_tgt - vx_os
    vy_rel = vy_tgt - vy_os
    vz_rel = vz_tgt - vz_os

    vrel_h = math.hypot(vx_rel, vy_rel)

    if vrel_h < 1e-6:
        ux_perp = 0.0
        uy_perp = 1.0
    else:
        ux_perp = -vy_rel / vrel_h
        uy_perp = vx_rel / vrel_h

    r_cpa_x = ux_perp * cpa_horiz_m
    r_cpa_y = uy_perp * cpa_horiz_m
    r_cpa_z = conflict_dh_m

    r0_x = r_cpa_x - vx_rel * tcpa_sec
    r0_y = r_cpa_y - vy_rel * tcpa_sec
    r0_z = target_alto_m

    os_start = (os_lat_deg, os_lon_deg, os_alt_m)

    os_cpa_lat, os_cpa_lon = meters_to_latlon(os_lat_deg, os_lon_deg, dx_os, dy_os)
    os_cpa = (os_cpa_lat, os_cpa_lon, os_alt_cpa)

    tgt_start_lat, tgt_start_lon = meters_to_latlon(os_lat_deg, os_lon_deg, r0_x, r0_y)
    tgt_start_alt = os_alt_m + r0_z
    tgt_start = (tgt_start_lat, tgt_start_lon, tgt_start_alt)

    tgt_cpa_dx = r0_x + dx_tgt
    tgt_cpa_dy = r0_y + dy_tgt

    tgt_cpa_lat, tgt_cpa_lon = meters_to_latlon(os_lat_deg, os_lon_deg, tgt_cpa_dx, tgt_cpa_dy)
    tgt_alt_cpa = tgt_start_alt + dz_tgt
    tgt_cpa = (tgt_cpa_lat, tgt_cpa_lon, tgt_alt_cpa)

    # ============================================================
    # ✅ FIXED POST-CPA CONTINUATION (ONLY CHANGE)
    # ============================================================

    # Ownship continues forward AFTER CPA
    os_post_dx = vx_os * post_cpa_sec
    os_post_dy = vy_os * post_cpa_sec
    os_post_dz = vz_os * post_cpa_sec

    os_total_dx = dx_os + os_post_dx
    os_total_dy = dy_os + os_post_dy

    os_end_lat, os_end_lon = meters_to_latlon(os_lat_deg, os_lon_deg, os_total_dx, os_total_dy)
    os_end_alt = os_alt_cpa + os_post_dz
    os_end = (os_end_lat, os_end_lon, os_end_alt)

    # Target continues forward AFTER CPA
    tgt_post_dx = vx_tgt * post_cpa_sec
    tgt_post_dy = vy_tgt * post_cpa_sec
    tgt_post_dz = vz_tgt * post_cpa_sec

    tgt_total_dx = r0_x + dx_tgt + tgt_post_dx
    tgt_total_dy = r0_y + dy_tgt + tgt_post_dy

    tgt_end_lat, tgt_end_lon = meters_to_latlon(os_lat_deg, os_lon_deg, tgt_total_dx, tgt_total_dy)
    tgt_end_alt = tgt_alt_cpa + tgt_post_dz
    tgt_end = (tgt_end_lat, tgt_end_lon, tgt_end_alt)

    # ============================================================

    r_tcpa_x = r0_x + vx_rel * tcpa_sec
    r_tcpa_y = r0_y + vy_rel * tcpa_sec
    r_tcpa_z = r0_z + vz_rel * tcpa_sec

    cpa_sep_horiz_m = math.hypot(r_tcpa_x, r_tcpa_y)
    cpa_sep_vert_m = abs(r_tcpa_z)
    cpa_sep_3d_m = math.sqrt(r_tcpa_x**2 + r_tcpa_y**2 + r_tcpa_z**2)

    print("OS CPA ALT (ft):", round(m_to_ft(os_cpa[2]), 3))
    print("Target CPA ALT (ft):", round(m_to_ft(tgt_cpa[2]), 3))
    print("Conflict DH Input (ft):", round(m_to_ft(conflict_dh_m), 3))
    print("Target Alt Offset Input (ft):", round(m_to_ft(target_alto_m), 3))
    print("Horizontal CPA Separation (ft):", round(m_to_ft(cpa_sep_horiz_m), 3))
    print("Vertical CPA Separation (ft):", round(m_to_ft(cpa_sep_vert_m), 3))
    print("3D CPA Separation (ft):", round(m_to_ft(cpa_sep_3d_m), 3))

    return (
        {
            "os_start": os_start,
            "os_cpa": os_cpa,
            "os_end": os_end,

            "tgt_start": tgt_start,
            "tgt_cpa": tgt_cpa,
            "tgt_end": tgt_end,

            "tgt_course_deg": tgt_course_deg,
            "cpa_sep_horiz_m": cpa_sep_horiz_m,
            "cpa_sep_vert_m": cpa_sep_vert_m,
            "cpa_sep_3d_m": cpa_sep_3d_m,
            "os_speed_mps": os_speed_mps,
            "os_vspeed_mps": os_vspeed_mps,
            "os_course_deg": os_course_deg,

            "tgt_speed_mps": tgt_speed_mps,
            "tgt_course_deg": tgt_course_deg,

            "vx_os": vx_os,
            "vy_os": vy_os,
            "vz_os": vz_os,
            "vx_tgt": vx_tgt,
            "vy_tgt": vy_tgt,
            "vz_tgt": vz_tgt,
        }
    )


# ============================================================
# TYPE 2
# Given:
# - line path of ownship (start/end lat/lon)
# - velocity of ownship
# - line path of target (start/end lat/lon)
# - velocity of target
# - tcpa
# - cpa location
#
# Calculate:
# - initial position of ownship
# - initial position of target
# - ownship course
# - target course
# ============================================================

def compute_initial_positions_type2(
    tcpa_sec,
    cpa_lat,
    cpa_lon,
    os_s_lat, os_s_lon, os_e_lat, os_e_lon,
    tgt_s_lat, tgt_s_lon, tgt_e_lat, tgt_e_lon,
    os_speed_mps,
    tgt_speed_mps
):
    # Ownship line direction
    os_dx_line, os_dy_line = latlon_to_local_m(cpa_lat, cpa_lon, os_e_lat, os_e_lon)
    os_mag = math.hypot(os_dx_line, os_dy_line)
    if os_mag < 1e-9:
        raise ValueError("Ownship path start/end cannot be identical")

    os_ux = os_dx_line / os_mag
    os_uy = os_dy_line / os_mag

    # Target line direction
    tgt_dx_line, tgt_dy_line = latlon_to_local_m(cpa_lat, cpa_lon, tgt_e_lat, tgt_e_lon)
    tgt_mag = math.hypot(tgt_dx_line, tgt_dy_line)
    if tgt_mag < 1e-9:
        raise ValueError("Target path start/end cannot be identical")

    tgt_ux = tgt_dx_line / tgt_mag
    tgt_uy = tgt_dy_line / tgt_mag

    # Reverse from CPA by tcpa to find initial positions
    os_back_dx = os_ux * os_speed_mps * tcpa_sec
    os_back_dy = os_uy * os_speed_mps * tcpa_sec

    tgt_back_dx = tgt_ux * tgt_speed_mps * tcpa_sec
    tgt_back_dy = tgt_uy * tgt_speed_mps * tcpa_sec

    os_init_lat, os_init_lon = meters_to_latlon(
        cpa_lat, cpa_lon,
        -os_back_dx, -os_back_dy
    )

    tgt_init_lat, tgt_init_lon = meters_to_latlon(
        cpa_lat, cpa_lon,
        -tgt_back_dx, -tgt_back_dy
    )

    os_course_deg = (math.degrees(math.atan2(os_ux, os_uy)) + 360.0) % 360.0
    tgt_course_deg = (math.degrees(math.atan2(tgt_ux, tgt_uy)) + 360.0) % 360.0

    return {
        "os_init": (os_init_lat, os_init_lon),
        "tgt_init": (tgt_init_lat, tgt_init_lon),
        "os_course_deg": os_course_deg,
        "tgt_course_deg": tgt_course_deg
    }