import math


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

    vx_os = os_speed_mps * math.cos(os_course_rad)
    vy_os = os_speed_mps * math.sin(os_course_rad)
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
    # This mapping makes:
    # 0 => target heading opposite ownship (head-on)
    # 180 => target same heading as ownship (overtaking)
    # ----------------------------
    tgt_course_deg = (os_course_deg + 180.0 + (relative_heading_deg % 360.0)) % 360.0
    tgt_course_rad = math.radians(tgt_course_deg)

    vx_tgt = rel_speed_mps * math.cos(tgt_course_rad)
    vy_tgt = rel_speed_mps * math.sin(tgt_course_rad)
    vz_tgt = 0.0  # keep as 0 unless you later add target vertical speed input

    dx_tgt = vx_tgt * tcpa_sec
    dy_tgt = vy_tgt * tcpa_sec
    dz_tgt = vz_tgt * tcpa_sec

    # ----------------------------
    # REALISTIC CPA SETUP (key change):
    #
    # We want CPA at t = tcpa_sec with:
    #   horizontal separation magnitude = cpa_horiz_m
    #   vertical separation = conflict_dh_m
    #
    # For CPA at tcpa_sec, the relative position vector at CPA must be
    # perpendicular to relative velocity (in the horizontal plane).
    #
    # r_cpa · v_rel = 0  (horizontal)
    # ----------------------------
    vx_rel = vx_tgt - vx_os
    vy_rel = vy_tgt - vy_os
    vz_rel = vz_tgt - vz_os

    vrel_h = math.hypot(vx_rel, vy_rel)

    # If relative horizontal speed is ~0, CPA is undefined in horizontal plane.
    # Fallback: place separation along +Y.
    if vrel_h < 1e-6:
        ux_perp = 0.0
        uy_perp = 1.0
    else:
        # unit vector perpendicular to v_rel (rotate by +90 degrees)
        ux_perp = -vy_rel / vrel_h
        uy_perp = vx_rel / vrel_h

    # Relative position at CPA (target - ownship) at time tcpa_sec
    r_cpa_x = ux_perp * cpa_horiz_m
    r_cpa_y = uy_perp * cpa_horiz_m
    r_cpa_z = conflict_dh_m

    # Back-compute target initial relative position so that at tcpa_sec it becomes r_cpa:
    # r(tcpa) = r0 + v_rel * tcpa  => r0 = r(tcpa) - v_rel * tcpa
    r0_x = r_cpa_x - vx_rel * tcpa_sec
    r0_y = r_cpa_y - vy_rel * tcpa_sec
    r0_z = r_cpa_z - vz_rel * tcpa_sec

    # ----------------------------
    # Build start + CPA positions in lat/lon/alt
    # ----------------------------
    os_start = (os_lat_deg, os_lon_deg, os_alt_m)
    os_cpa_lat, os_cpa_lon = meters_to_latlon(os_lat_deg, os_lon_deg, dx_os, dy_os)
    os_cpa = (os_cpa_lat, os_cpa_lon, os_alt_cpa)

    # Target start is offset from ownship start by r0 (in meters)
    tgt_start_lat, tgt_start_lon = meters_to_latlon(os_lat_deg, os_lon_deg, r0_x, r0_y)
    tgt_start_alt = os_alt_m + r0_z + target_alto_m
    tgt_start = (tgt_start_lat, tgt_start_lon, tgt_start_alt)

    # Target CPA = target start + target motion
    tgt_cpa_lat, tgt_cpa_lon = meters_to_latlon(tgt_start_lat, tgt_start_lon, dx_tgt, dy_tgt)
    tgt_alt_cpa = tgt_start_alt + dz_tgt
    tgt_cpa = (tgt_cpa_lat, tgt_cpa_lon, tgt_alt_cpa)

    # ----------------------------
    # Debug/validation metrics at CPA
    # (added keys; existing keys preserved)
    # ----------------------------
    # Relative separation at CPA in local meters:
    # r(tcpa) = r0 + v_rel*tcpa => should equal r_cpa
    r_tcpa_x = r0_x + vx_rel * tcpa_sec
    r_tcpa_y = r0_y + vy_rel * tcpa_sec
    r_tcpa_z = r0_z + vz_rel * tcpa_sec

    cpa_sep_horiz_m = math.hypot(r_tcpa_x, r_tcpa_y)
    cpa_sep_vert_m = abs(r_tcpa_z)
    cpa_sep_3d_m = math.sqrt(r_tcpa_x**2 + r_tcpa_y**2 + r_tcpa_z**2)

    return {
        "os_start": os_start,
        "os_cpa": os_cpa,
        "tgt_start": tgt_start,
        "tgt_cpa": tgt_cpa,

        # ✅ Added debug outputs (safe additions)
        "tgt_course_deg": tgt_course_deg,
        "cpa_sep_horiz_m": cpa_sep_horiz_m,
        "cpa_sep_vert_m": cpa_sep_vert_m,
        "cpa_sep_3d_m": cpa_sep_3d_m
    }