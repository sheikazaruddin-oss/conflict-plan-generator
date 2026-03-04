import json
import math
import os


# -------------------------------------------------
# Utility
# -------------------------------------------------
def load_json(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    with open(path, "r") as f:
        return json.load(f)


# -------------------------------------------------
# Main Validation
# -------------------------------------------------
def main():

    print("\nLoading files...\n")

    scenario = load_json("scenario_log.json")
    telemetry = load_json("telemetry_log.json")

    # -------------------------------------------------
    # Extract Theoretical Values
    # -------------------------------------------------
    theory_3d = scenario["cpa_metrics"]["3d_sep_ft"]
    theory_h  = scenario["cpa_metrics"]["horizontal_sep_ft"]
    theory_v  = scenario["cpa_metrics"]["vertical_sep_ft"]
    theory_tcpa = scenario["inputs"]["tcpa_sec"]

    print("Theoretical values loaded.")
    print(f"Theoretical 3D Separation : {theory_3d:.6f} ft")
    print(f"Theoretical TCPA          : {theory_tcpa:.6f} sec\n")

    # -------------------------------------------------
    # Extract Telemetry Frames
    # -------------------------------------------------
    frames = telemetry["frames"]

    if len(frames) == 0:
        raise ValueError("Telemetry frames are empty.")

    print(f"Telemetry frames loaded: {len(frames)} frames")

    # -------------------------------------------------
    # Filter Invalid Startup Frames
    # -------------------------------------------------
    valid_frames = []

    for frame in frames:

        sep = frame.get("separation_3d_ft", 0)
        own = frame.get("ownship", {})
        tgt = frame.get("target", {})

        # Skip if missing data
        if not own or not tgt:
            continue

        # Skip SITL initialization frames
        if (
            own.get("lat", 0) == 0 or
            tgt.get("lat", 0) == 0 or
            own.get("alt_ft", 0) == 0 or
            tgt.get("alt_ft", 0) == 0 or
            sep == 0
        ):
            continue

        valid_frames.append(frame)

    if len(valid_frames) == 0:
        raise ValueError("No valid telemetry frames found after filtering.")

    print(f"Valid frames used: {len(valid_frames)}\n")

    # -------------------------------------------------
    # Compute Actual Minimum Separation + RMSE
    # -------------------------------------------------
    start_time = valid_frames[0]["timestamp"]

    actual_min = float("inf")
    actual_min_time = None

    sum_sq_error = 0
    count = 0

    for frame in valid_frames:

        sep = frame["separation_3d_ft"]
        relative_time = frame["timestamp"] - start_time

        # Track actual minimum separation
        if sep < actual_min:
            actual_min = sep
            actual_min_time = relative_time

        # RMSE vs theoretical CPA separation
        error = sep - theory_3d
        sum_sq_error += error ** 2
        count += 1

    rmse = math.sqrt(sum_sq_error / count)

    # -------------------------------------------------
    # Compute Errors
    # -------------------------------------------------
    sep_error = abs(theory_3d - actual_min)

    if theory_3d != 0:
        sep_accuracy = 100 - (sep_error / theory_3d * 100)
    else:
        sep_accuracy = 0

    time_error = abs(theory_tcpa - actual_min_time)

    # -------------------------------------------------
    # Print Final Report
    # -------------------------------------------------
    print("=============== CPA VALIDATION REPORT ===============\n")

    print("--- Separation ---")
    print(f"Theoretical 3D Separation : {theory_3d:.6f} ft")
    print(f"Actual Minimum Separation : {actual_min:.6f} ft")
    print(f"Separation Error          : {sep_error:.6f} ft")

    print("--- Time ---")
    print(f"Theoretical TCPA (sec)    : {theory_tcpa:.6f}")
    print(f"Actual TCPA (sec)         : {actual_min_time:.6f}")
    print(f"TCPA Error (sec)          : {time_error:.6f}\n")

    print("=====================================================")


if __name__ == "__main__":
    main()