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
    target_alto_m,
    relative_heading_deg
):
    # Ownship motion vector
    os_course_rad = math.radians(os_course_deg % 360)
    dx_os = os_speed_mps * tcpa_sec * math.cos(os_course_rad)
    dy_os = os_speed_mps * tcpa_sec * math.sin(os_course_rad)
    dz_os = os_vspeed_mps * tcpa_sec
    os_alt_cpa = os_alt_m + dz_os

    # CPA position of ownship
    os_cpa_x = dx_os
    os_cpa_y = dy_os

    # Target motion vector based on relative heading
    tgt_course_deg = (os_course_deg + relative_heading_deg) % 360
    tgt_course_rad = math.radians(tgt_course_deg)
    dx_tgt = rel_speed_mps * tcpa_sec * math.cos(tgt_course_rad)
    dy_tgt = rel_speed_mps * tcpa_sec * math.sin(tgt_course_rad)

    # Target altitude at CPA
    tgt_alt_cpa = os_alt_cpa + conflict_dh_m
    tgt_start_alt = tgt_alt_cpa + target_alto_m

    # Start positions
    os_start = (os_lat_deg, os_lon_deg, os_alt_m)
    os_cpa = meters_to_latlon(os_lat_deg, os_lon_deg, dx_os, dy_os)
    os_cpa = (*os_cpa, os_alt_cpa)

    tgt_cpa = os_cpa
    tgt_start = meters_to_latlon(os_lat_deg, os_lon_deg, dx_os - dx_tgt, dy_os - dy_tgt)
    tgt_start = (*tgt_start, tgt_start_alt)

    return {
    "os_start": os_start,
    "os_cpa": os_cpa,
    "tgt_start": tgt_start,
    "tgt_cpa": tgt_cpa
    }
