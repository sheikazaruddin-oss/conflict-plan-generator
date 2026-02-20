# validation_logger.py

import json
import datetime
import uuid

from units import m_to_ft, mps_to_kt


def sec_to_mmss(seconds: int) -> str:
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes:02d}:{secs:02d}"


def save_validation_log(filename, inputs_dict, points_dict, tcpa_sec):
    """
    Save aviation-friendly validation log.
    All outputs converted to:
        - feet
        - knots
        - ft/min
        - TCPA in mm:ss
    """

    # ==============================
    # TIME METADATA
    # ==============================

    now_utc = datetime.datetime.utcnow()
    predicted_cpa_utc = now_utc + datetime.timedelta(seconds=tcpa_sec)

    # ==============================
    # CONVERT CPA METRICS TO FEET
    # ==============================

    cpa_sep_horiz_ft = round(m_to_ft(points_dict.get("cpa_sep_horiz_m")), 2)
    cpa_sep_vert_ft = round(m_to_ft(points_dict.get("cpa_sep_vert_m")), 2)
    cpa_sep_3d_ft = round(m_to_ft(points_dict.get("cpa_sep_3d_m")), 2)

    # ==============================
    # OWNERSHIP INITIAL STATE (AVIATION UNITS)
    # ==============================

    os_start = points_dict.get("os_start")
    tgt_start = points_dict.get("tgt_start")

    os_speed_kt = round(mps_to_kt(points_dict.get("os_speed_mps")), 2)
    tgt_speed_kt = round(mps_to_kt(points_dict.get("tgt_speed_mps")), 2)

    os_vertical_speed_fpm = inputs_dict.get("os_vspeed_fpm", 0.0)

    # ==============================
    # BUILD LOG STRUCTURE
    # ==============================

    log_data = {

        "metadata": {
            "scenario_id": str(uuid.uuid4()),
            "generated_utc": now_utc.isoformat() + "Z",
            "predicted_cpa_utc": predicted_cpa_utc.isoformat() + "Z",
            "tcpa_mmss": sec_to_mmss(tcpa_sec)
        },

        # Raw user inputs (aviation units already)
        "inputs": inputs_dict,

        # CPA separation metrics (AVIATION UNITS)
        "cpa_metrics": {
            "horizontal_sep_ft": cpa_sep_horiz_ft,
            "vertical_sep_ft": cpa_sep_vert_ft,
            "3d_sep_ft": cpa_sep_3d_ft
        },

        # Computed initial aircraft states
        "computed_initial_state": {

            "ownship": {
                "lat_deg": os_start[0],
                "lon_deg": os_start[1],
                "alt_ft": round(m_to_ft(os_start[2]), 2),
                "course_deg": points_dict.get("os_course_deg"),
                "speed_kt": os_speed_kt,
                "vertical_speed_fpm": os_vertical_speed_fpm
            },

            "target": {
                "lat_deg": tgt_start[0],
                "lon_deg": tgt_start[1],
                "alt_ft": round(m_to_ft(tgt_start[2]), 2),
                "course_deg": points_dict.get("tgt_course_deg"),
                "speed_kt": tgt_speed_kt,
                "vertical_speed_fpm": 0.0
            }
        }
    }

    # ==============================
    # WRITE FILE
    # ==============================

    with open(filename, "w") as f:
        json.dump(log_data, f, indent=4)

    return filename