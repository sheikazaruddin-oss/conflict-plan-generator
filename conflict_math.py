import math
from units import m_to_ft


def meters_to_latlon(lato_deg, lono_deg, dx_m, dy_m):
    # Converts local (dx, dy) in meters to (lat, lon) around reference
    R = 6378137.0  # Earth radius in meters
    lato_rad = math.radians(lato_deg)

    dlat = dy_m / R
    dlon = dx_m / (R * math.cos(lato_rad))

    lat = lato_deg + math.degrees(dlat)
    lon = lono_deg + math.degrees(dlon)
    return lat, lon


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
    relative_heading_deg
):
    # ----------------------------
    # Ownship motion vector (local meters)
    # NOTE: Preserving your original convention:
    # dx = speed*cos(course), dy = speed*sin(course)
    # ----------------------------
    os_course_rad = math.radians(os_course_deg % 360.0)

    vx_os = os_speed_mps * math.sin(os_course_rad)
    vy_os = os_speed_mps * math.cos(os_course_rad)
    vz_os = os_vspeed_mps

    dx_os = vx_os * tcpa_sec
    dy_os = vy_os * tcpa_sec
    dz_os = vz_os * tcpa_sec

    os_alt_cpa = os_alt_m + dz_os

    # ----------------------------
    # Target motion vector
    # relative_heading_deg meaning (your definition):
    # 0=head-on, 90=crossing from right, 180=overtaking, 270=crossing from left
    #
    # Correct mapping:
    # 0   -> target heading opposite ownship (os + 180)
    # 180 -> target heading same as ownship (os)
    # So: tgt = os + (180 - relative_heading)
    # ----------------------------
    tgt_course_deg = (os_course_deg + 180.0 - (relative_heading_deg % 360.0)) % 360.0
    tgt_course_rad = math.radians(tgt_course_deg)

    vx_tgt = rel_speed_mps * math.sin(tgt_course_rad)
    vy_tgt = rel_speed_mps * math.cos(tgt_course_rad)

    # ----------------------------
    # Vertical consistency fix (key change):
    # target_alto_m = target vertical offset at t=0  (target - ownship)
    # conflict_dh_m = desired vertical separation at CPA (target - ownship at t=tcpa)
    #
    # Solve for vz_tgt so BOTH are true:
    # r_z(t) = target_alto_m + (vz_tgt - vz_os)*t
    # r_z(tcpa) = conflict_dh_m
    # => vz_tgt = vz_os + (conflict_dh_m - target_alto_m)/tcpa_sec
    # ----------------------------
    if abs(tcpa_sec) < 1e-9:
        # Degenerate case: tcpa_sec ~ 0, can't solve slope.
        # Best effort: keep target vertical speed same as ownship.
        vz_tgt = vz_os
    else:
        vz_tgt = vz_os + ((conflict_dh_m - target_alto_m) / tcpa_sec)

    dz_tgt = vz_tgt * tcpa_sec
    dx_tgt = vx_tgt * tcpa_sec
    dy_tgt = vy_tgt * tcpa_sec

    # ----------------------------
    # REALISTIC CPA SETUP:
    # We want CPA at t = tcpa_sec with:
    #   horizontal separation magnitude = cpa_horiz_m
    #   vertical separation = conflict_dh_m
    #
    # For CPA at tcpa_sec, the relative position vector at CPA must be
    # perpendicular to relative velocity (in horizontal plane):
    # r_cpa . v_rel = 0 (horizontal)
    # ----------------------------
    vx_rel = vx_tgt - vx_os
    vy_rel = vy_tgt - vy_os
    vz_rel = vz_tgt - vz_os

    vrel_h = math.hypot(vx_rel, vy_rel)

    # Unit vector perpendicular to v_rel (rotate by +90 deg)
    if vrel_h < 1e-6:
        ux_perp = 0.0
        uy_perp = 1.0
    else:
        ux_perp = -vy_rel / vrel_h
        uy_perp = vx_rel / vrel_h

    # Relative position at CPA (target - ownship) at time tcpa_sec
    r_cpa_x = ux_perp * cpa_horiz_m
    r_cpa_y = uy_perp * cpa_horiz_m
    r_cpa_z = conflict_dh_m

    # Back-compute target initial relative position (x,y) so that at tcpa_sec it becomes r_cpa:
    # r(tcpa) = r0 + v_rel * tcpa  =>  r0 = r(tcpa) - v_rel * tcpa
    r0_x = r_cpa_x - vx_rel * tcpa_sec
    r0_y = r_cpa_y - vy_rel * tcpa_sec

    # IMPORTANT:
    # We force the initial vertical offset to be target_alto_m by definition.
    r0_z = target_alto_m

    # ----------------------------
    # Build start + CPA positions in lat/lon/alt
    # ----------------------------
    os_start = (os_lat_deg, os_lon_deg, os_alt_m)
    os_cpa_lat, os_cpa_lon = meters_to_latlon(os_lat_deg, os_lon_deg, dx_os, dy_os)
    os_cpa = (os_cpa_lat, os_cpa_lon, os_alt_cpa)

    # Target start is offset from ownship start by r0 (in meters)
    tgt_start_lat, tgt_start_lon = meters_to_latlon(os_lat_deg, os_lon_deg, r0_x, r0_y)
    tgt_start_alt = os_alt_m + r0_z
    tgt_start = (tgt_start_lat, tgt_start_lon, tgt_start_alt)

    # Target CPA in local ENU meters relative to ownship origin
    tgt_cpa_dx = r0_x + dx_tgt
    tgt_cpa_dy = r0_y + dy_tgt

    # Convert using OWN origin (same reference as ownship CPA)
    tgt_cpa_lat, tgt_cpa_lon = meters_to_latlon(os_lat_deg, os_lon_deg, tgt_cpa_dx, tgt_cpa_dy)

    tgt_alt_cpa = tgt_start_alt + dz_tgt
    tgt_cpa = (tgt_cpa_lat, tgt_cpa_lon, tgt_alt_cpa)
    
    # ----------------------------
    # Debug/validation metrics at CPA
    # r(tcpa) = r0 + v_rel*tcpa  (should match r_cpa)
    # ----------------------------
    r_tcpa_x = r0_x + vx_rel * tcpa_sec
    r_tcpa_y = r0_y + vy_rel * tcpa_sec
    r_tcpa_z = r0_z + vz_rel * tcpa_sec

    cpa_sep_horiz_m = math.hypot(r_tcpa_x, r_tcpa_y)
    cpa_sep_vert_m = abs(r_tcpa_z)
    cpa_sep_3d_m = math.sqrt(r_tcpa_x**2 + r_tcpa_y**2 + r_tcpa_z**2)

    # DEBUG PRINTS (safe to keep)
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
            "tgt_start": tgt_start,
            "tgt_cpa": tgt_cpa,

            # Added debug outputs (safe additions)
            "tgt_course_deg": tgt_course_deg,
            "cpa_sep_horiz_m": cpa_sep_horiz_m,
            "cpa_sep_vert_m": cpa_sep_vert_m,
            "cpa_sep_3d_m": cpa_sep_3d_m,
            "os_speed_mps": os_speed_mps,
            "os_vspeed_mps": os_vspeed_mps,
            "os_course_deg": os_course_deg,

            "tgt_speed_mps": rel_speed_mps,
            "tgt_course_deg": tgt_course_deg,

            "vx_os": vx_os,
            "vy_os": vy_os,
            "vz_os": vz_os,
            "vx_tgt": vx_tgt,
            "vy_tgt": vy_tgt,
            "vz_tgt": vz_tgt,
        }
    )