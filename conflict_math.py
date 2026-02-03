import math

def meters_to_latlon(lat0_deg, lon0_deg, dx_m, dy_m):
    # Converts local (dx, dy) in meters to (lat, lon) around reference
    R = 6378137.0  # Earth radius in meters
    lat0_rad = math.radians(lat0_deg)

    dlat = dy_m / R
    dlon = dx_m / (R * math.cos(lat0_rad))

    lat = lat0_deg + math.degrees(dlat)
    lon = lon0_deg + math.degrees(dlon)
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
    target_alt0_m,
    cpa_side,
):
    course_rad = math.radians(os_course_deg % 360)

    # Ownship motion in local frame
    dx_os = os_speed_mps * tcpa_sec * math.sin(course_rad)
    dy_os = os_speed_mps * tcpa_sec * math.cos(course_rad)
    dz_os = os_vspeed_mps * tcpa_sec
    cpa_alt = os_alt_m + dz_os

    # CPA offset for target based on DH and CPA side
    if cpa_side.lower() == "right":
        dx_tgt = dx_os + cpa_horiz_m * math.cos(course_rad)
        dy_tgt = dy_os - cpa_horiz_m * math.sin(course_rad)
    else:
        dx_tgt = dx_os - cpa_horiz_m * math.cos(course_rad)
        dy_tgt = dy_os + cpa_horiz_m * math.sin(course_rad)

    # Compute lat/lon positions
    os_start = (os_lat_deg, os_lon_deg, os_alt_m)
    os_cpa = meters_to_latlon(os_lat_deg, os_lon_deg, dx_os, dy_os) + (cpa_alt,)

    tgt_start = (os_lat_deg, os_lon_deg, target_alt0_m)
    tgt_cpa = meters_to_latlon(os_lat_deg, os_lon_deg, dx_tgt, dy_tgt) + (target_alt0_m + conflict_dh_m,)

    return {
        "os_start": os_start,
        "os_cpa": os_cpa,
        "tgt_start": tgt_start,
        "tgt_cpa": tgt_cpa,
    }