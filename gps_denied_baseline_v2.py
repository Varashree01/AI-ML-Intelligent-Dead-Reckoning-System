"""GPS-denied dead-reckoning baseline, version 2.

The default estimator propagates vehicle speed along phone heading calibrated
from the five seconds before the outage. GPS is used only as the reference and
to initialize the estimate at the outage boundary.
"""

import argparse
import os
from math import cos, radians, sin

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


EARTH_RADIUS_M = 6378137.0
DEFAULT_S_PATH = os.path.join("IO-VNBD-GIT", "Synchronised V abd S datasets", "Uncategorised IOVNB Dataset", "S-Dataset", "S-S1.csv")
DEFAULT_V_PATH = os.path.join("IO-VNBD-GIT", "Synchronised V abd S datasets", "Uncategorised IOVNB Dataset", "V-Dataset", "V-S1.csv")


def find_column(columns, keywords, required=True):
    lowered = [str(column).lower() for column in columns]
    for keyword in keywords:
        for index, column in enumerate(lowered):
            if keyword.lower() in column:
                return columns[index]
    if required:
        raise ValueError(f"Could not find a column matching {keywords}")
    return None


def relative_time(values, unit):
    values = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float)
    if values.size < 2 or np.any(~np.isfinite(values)):
        raise ValueError("timestamps must contain at least two finite values")
    elapsed = values - values[0]
    if unit == "ms" or (unit == "auto" and np.nanmedian(np.diff(values)) > 10):
        elapsed /= 1000.0
    if np.any(np.diff(elapsed) <= 0):
        raise ValueError("timestamps must be strictly increasing")
    return elapsed


def latlon_to_enu(latitude, longitude, latitude0, longitude0):
    latitude = np.asarray(latitude, dtype=float)
    longitude = np.asarray(longitude, dtype=float)
    east = np.deg2rad(longitude - longitude0) * cos(radians(latitude0)) * EARTH_RADIUS_M
    north = np.deg2rad(latitude - latitude0) * EARTH_RADIUS_M
    return east, north


def circular_median_degrees(values):
    values = np.asarray(values, dtype=float)
    return np.degrees(np.angle(np.median(np.exp(1j * np.deg2rad(values)))))


def interpolate_heading(source_time, source_heading, target_time):
    heading = pd.to_numeric(source_heading, errors="coerce").interpolate().bfill().ffill().to_numpy(dtype=float)
    heading = np.unwrap(np.deg2rad(heading))
    return np.rad2deg(np.interp(target_time, source_time, heading))


def run_baseline(s_path, v_path, outage_start, outage_duration, mode="velocity",
                 heading_source="vehicle",
                 output_csv="data/gps_denied_baseline_v2_results.csv",
                 output_dir="data/gps_denied_plots_v2"):
    phone = pd.read_csv(s_path, encoding="cp1252")
    vehicle = pd.read_csv(v_path, encoding="cp1252")
    phone_time = relative_time(phone[find_column(phone.columns, ["time since start"])], "ms")
    vehicle_time = relative_time(vehicle[find_column(vehicle.columns, ["time since start of day", "time since start"])], "s")

    phone_lat_col = find_column(phone.columns, ["gps latitude", "latitude"])
    phone_lon_col = find_column(phone.columns, ["gps longitude", "longitude"])
    vehicle_lat_col = find_column(vehicle.columns, ["latitude"])
    vehicle_lon_col = find_column(vehicle.columns, ["longitude"])
    phone_lat = pd.to_numeric(phone[phone_lat_col], errors="coerce").interpolate().bfill().ffill().to_numpy()
    phone_lon = pd.to_numeric(phone[phone_lon_col], errors="coerce").interpolate().bfill().ffill().to_numpy()
    vehicle_lat = pd.to_numeric(vehicle[vehicle_lat_col], errors="coerce").interpolate().bfill().ffill().to_numpy()
    vehicle_lon = pd.to_numeric(vehicle[vehicle_lon_col], errors="coerce").interpolate().bfill().ffill().to_numpy()
    reference_x, reference_y = latlon_to_enu(
        np.interp(phone_time, vehicle_time, vehicle_lat),
        np.interp(phone_time, vehicle_time, vehicle_lon), vehicle_lat[0], vehicle_lon[0])

    phone_yaw_col = find_column(phone.columns, ["orientation (azimuth)", "gps orientation"])
    vehicle_heading_col = find_column(vehicle.columns, ["heading"], required=False)
    phone_yaw = interpolate_heading(phone_time, phone[phone_yaw_col], phone_time)
    vehicle_heading = interpolate_heading(
        vehicle_time,
        vehicle[vehicle_heading_col] if vehicle_heading_col else np.zeros(len(vehicle)),
        phone_time)
    outage_end = outage_start + outage_duration
    outage_mask = (phone_time >= outage_start) & (phone_time < outage_end)
    if not np.any(outage_mask):
        raise ValueError("The requested outage contains no phone samples")
    start_index = np.flatnonzero(outage_mask)[0]
    end_index = np.flatnonzero(outage_mask)[-1]
    pre_mask = (phone_time >= max(0.0, outage_start - 5.0)) & (phone_time < outage_start)
    if not np.any(pre_mask):
        raise ValueError("No samples available before the outage for heading calibration")
    yaw_offset = circular_median_degrees(vehicle_heading[pre_mask] - phone_yaw[pre_mask])
    if heading_source == "vehicle":
        heading = vehicle_heading % 360.0
    else:
        heading = (phone_yaw + yaw_offset) % 360.0

    speed_col = find_column(vehicle.columns, ["indicated vehicle speed", "velocity", "speed"])
    speed = pd.to_numeric(vehicle[speed_col], errors="coerce").interpolate().bfill().ffill().to_numpy()
    speed_mps = np.maximum(np.interp(phone_time, vehicle_time, speed), 0.0) / 3.6
    estimate_x = reference_x.copy()
    estimate_y = reference_y.copy()
    estimate_x[start_index:end_index + 1] = reference_x[start_index]
    estimate_y[start_index:end_index + 1] = reference_y[start_index]

    if mode == "acceleration":
        ax = pd.to_numeric(phone[find_column(phone.columns, ["accelerometer x", "accel x"])], errors="coerce").interpolate().bfill().ffill().to_numpy()
        ay = pd.to_numeric(phone[find_column(phone.columns, ["accelerometer y", "accel y"])], errors="coerce").interpolate().bfill().ffill().to_numpy()
        gravity_cols = [find_column(phone.columns, [f"gravity {axis}"], required=False) for axis in "xy"]
        if all(gravity_cols):
            ax -= pd.to_numeric(phone[gravity_cols[0]], errors="coerce").to_numpy()
            ay -= pd.to_numeric(phone[gravity_cols[1]], errors="coerce").to_numpy()
        velocity = np.zeros((len(phone_time), 2))
        for index in range(start_index + 1, end_index + 1):
            dt = phone_time[index] - phone_time[index - 1]
            yaw = radians(heading[index])
            world_acceleration = np.array([ax[index] * sin(yaw) + ay[index] * cos(yaw), ax[index] * cos(yaw) - ay[index] * sin(yaw)])
            velocity[index] = velocity[index - 1] + world_acceleration * dt
            estimate_x[index] = estimate_x[index - 1] + velocity[index, 0] * dt
            estimate_y[index] = estimate_y[index - 1] + velocity[index, 1] * dt
    else:
        for index in range(start_index + 1, end_index + 1):
            dt = phone_time[index] - phone_time[index - 1]
            compass_heading = radians(heading[index])
            estimate_x[index] = estimate_x[index - 1] + speed_mps[index] * sin(compass_heading) * dt
            estimate_y[index] = estimate_y[index - 1] + speed_mps[index] * cos(compass_heading) * dt

    error = np.hypot(estimate_x - reference_x, estimate_y - reference_y)
    outage_error = error[outage_mask]
    output = pd.DataFrame({"time_s": phone_time, "gps_x": reference_x, "gps_y": reference_y,
                           "dr_x": estimate_x, "dr_y": estimate_y, "gps_available": ~outage_mask,
                           "estimated_heading_deg": heading, "speed_mps": speed_mps,
                           "position_error_m": error})
    os.makedirs(os.path.dirname(output_csv) or ".", exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    output.to_csv(output_csv, index=False)

    plt.figure(figsize=(9, 6))
    plt.plot(reference_x, reference_y, label="GPS reference", linewidth=2)
    plt.plot(estimate_x, estimate_y, label=f"DR v2 ({mode})")
    plt.axis("equal")
    plt.xlabel("East (m)")
    plt.ylabel("North (m)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "trajectory.png"), dpi=150)
    plt.close()
    plt.figure(figsize=(9, 4))
    plt.plot(phone_time, error)
    plt.axvspan(outage_start, outage_end, color="orange", alpha=0.2)
    plt.xlabel("Time (s)")
    plt.ylabel("Position error (m)")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "error.png"), dpi=150)
    plt.close()
    return {"rmse_m": float(np.sqrt(np.mean(outage_error ** 2))),
            "mean_error_m": float(np.mean(outage_error)),
            "max_error_m": float(np.max(outage_error)),
            "final_error_m": float(error[end_index]),
            "yaw_offset_deg": float(yaw_offset), "output_csv": output_csv}


def main():
    parser = argparse.ArgumentParser(description="Run the v2 GPS-denied dead-reckoning baseline")
    parser.add_argument("--s-path", default=DEFAULT_S_PATH)
    parser.add_argument("--v-path", default=DEFAULT_V_PATH)
    parser.add_argument("--outage-start", type=float, default=60.0)
    parser.add_argument("--outage-duration", type=float, default=60.0)
    parser.add_argument("--mode", choices=("velocity", "acceleration"), default="velocity")
    parser.add_argument("--heading-source", choices=("vehicle", "phone"), default="vehicle")
    parser.add_argument("--output-csv", default="data/gps_denied_baseline_v2_results.csv")
    parser.add_argument("--output-dir", default="data/gps_denied_plots_v2")
    args = parser.parse_args()
    metrics = run_baseline(**vars(args))
    print("GPS-DENIED BASELINE V2")
    for name, value in metrics.items():
        print(f"{name}: {value}")


if __name__ == "__main__":
    main()