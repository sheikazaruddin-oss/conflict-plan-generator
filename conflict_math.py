import math

def knots_to_mps(knots):
    return knots * 0.514444

def calculate_cpa_geometry(
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
    relative_heading_deg
):
    # Convert input angles to radians
    os_heading_rad = math.radians(os_course)
    tgt_heading_rad = math.radians((os_course + relative_heading_deg) % 360)

    # Speeds in m/s
    os_speed_mps = knots_to_mps(os_speed)
    tgt_speed_mps = knots_to_mps(tgt_rel_speed)

    # Total distance each travels before CPA
    os_h_dist = os_speed_mps * tcpa
    tgt_h_dist = tgt_speed_mps * tcpa

    # Vertical positions
    os_final_alt = os_alt + os_vspeed * tcpa
    tgt_alt = os_final_alt + tgt_alt_offset

    # OS Waypoints (start and CPA)
    os_x1, os_y1 = 0, 0
    os_x2 = os_h_dist * math.cos(os_heading_rad)
    os_y2 = os_h_dist * math.sin(os_heading_rad)

    # Target position: start from CPA point, backtrack by horizontal distance
    tgt_cpa_x = os_x2 + cpa_distance * math.cos(tgt_heading_rad)
    tgt_cpa_y = os_y2 + cpa_distance * math.sin(tgt_heading_rad)

    tgt_x1 = tgt_cpa_x - tgt_h_dist * math.cos(tgt_heading_rad)
    tgt_y1 = tgt_cpa_y - tgt_h_dist * math.sin(tgt_heading_rad)
    tgt_x2 = tgt_cpa_x
    tgt_y2 = tgt_cpa_y

    # Convert XY to lat/lon (very rough, assumes flat Earth)
    def meters_to_latlon(x, y, lat0, lon0):
        dlat = y / 111320
        dlon = x / (40075000 * math.cos(math.radians(lat0)) / 360)
        return lat0 + dlat, lon0 + dlon

    os_wp1 = (os_lat, os_lon, os_alt)
    os_wp2 = (*meters_to_latlon(os_x2, os_y2, os_lat, os_lon), os_final_alt)

    tgt_wp1 = (*meters_to_latlon(tgt_x1, tgt_y1, os_lat, os_lon), tgt_alt)
    tgt_wp2 = (*meters_to_latlon(tgt_x2, tgt_y2, os_lat, os_lon), tgt_alt)

    return os_wp1, os_wp2, tgt_wp1, tgt_wp2