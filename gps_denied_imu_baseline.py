"""Scientifically constrained smartphone-IMU GPS-denied baseline.

Vehicle data is separated into two permitted roles:
* the last pre-outage sample initializes position, velocity, and heading;
* the complete vehicle trajectory is used only after propagation for scoring.

The 60-120 second propagation loop receives no vehicle or GPS values. The
orientation conversion uses the dataset's azimuth/pitch/roll values directly
with a Z-Y-X Euler convention. These values are not silently corrected; the
dataset's pitch is close to -80 degrees and its roll spans almost 360 degrees,
so orientation quality is reported as a limitation of this baseline.
"""

import argparse
import os
from math import cos, radians, sin

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial.transform import Rotation


EARTH_RADIUS_M = 6378137.0
OUTAGE_START = 60.0
OUTAGE_DURATION = 60.0
TRAINING_CSV = os.path.join("data", "training_dataset.csv")
VEHICLE_CSV = os.path.join(
    "IO-VNBD-GIT", "Synchronised V abd S datasets", "Uncategorised IOVNB Dataset",
    "V-Dataset", "V-S1.csv"
)
OUTPUT_CSV = os.path.join("data", "gps_denied_imu_baseline_results.csv")
PLOTS_DIR = os.path.join("data", "gps_denied_imu_plots")

SMARTPHONE_COLUMNS = [
    "time_s", "ACCEL_X", "ACCEL_Y", "ACCEL_Z", "GYRO_X", "GYRO_Y", "GYRO_Z",
    "GRAV_X", "GRAV_Y", "GRAV_Z", "OR_AZ", "OR_P", "OR_R",
]


def find_column(columns, keywords):
    for keyword in keywords:
        for column in columns:
            if keyword.lower() in str(column).lower():
                return column
    raise ValueError(f"Could not find a column matching {keywords}")


def to_numeric(frame, column):
    values = pd.to_numeric(frame[column], errors="coerce")
    if values.isna().any():
        values = values.interpolate().bfill().ffill()
    if values.isna().any():
        raise ValueError(f"Column {column} contains no usable numeric values")
    return values.to_numpy(dtype=float)


def latlon_to_enu(latitude, longitude, latitude0, longitude0):
    east = np.deg2rad(latitude * 0.0 + longitude - longitude0) * cos(radians(latitude0)) * EARTH_RADIUS_M
    north = np.deg2rad(latitude - latitude0) * EARTH_RADIUS_M
    return east, north


def load_smartphone_data(path):
    frame = pd.read_csv(path, encoding="cp1252", usecols=SMARTPHONE_COLUMNS)
    missing = [column for column in SMARTPHONE_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required smartphone columns: {missing}")
    arrays = {column: to_numeric(frame, column) for column in SMARTPHONE_COLUMNS}
    time_s = arrays["time_s"] - arrays["time_s"][0]
    if np.any(np.diff(time_s) <= 0):
        raise ValueError("training_dataset.csv time_s must be strictly increasing")
    return arrays, time_s


def load_vehicle_evaluation(path):
    frame = pd.read_csv(path, encoding="cp1252")
    time_col = find_column(frame.columns, ["time since start of day", "time since start"])
    lat_col = find_column(frame.columns, ["latitude"])
    lon_col = find_column(frame.columns, ["longitude"])
    heading_col = find_column(frame.columns, ["heading"])
    speed_col = find_column(frame.columns, ["indicated vehicle speed", "velocity", "speed"])
    time_s = to_numeric(frame, time_col).copy()
    time_s -= time_s[0]
    order = np.argsort(time_s)
    return {
        "time_s": time_s[order],
        "latitude": to_numeric(frame, lat_col)[order],
        "longitude": to_numeric(frame, lon_col)[order],
        "heading": to_numeric(frame, heading_col)[order],
        "speed_mps": np.maximum(to_numeric(frame, speed_col)[order], 0.0) / 3.6,
    }


def pre_outage_initial_state(vehicle, outage_start):
    """Read only vehicle samples strictly before the outage boundary."""
    allowed = vehicle["time_s"] < outage_start
    if not np.any(allowed):
        raise ValueError("Vehicle data has no samples before the outage")
    index = np.flatnonzero(allowed)[-1]
    return index, vehicle["speed_mps"][index], vehicle["heading"][index]


def orientation_to_navigation(acceleration, azimuth, pitch, roll):
    """Apply the recorded Z-Y-X device orientation without data-driven tuning."""
    rotations = Rotation.from_euler("ZYX", np.column_stack((azimuth, pitch, roll)), degrees=True)
    return rotations.apply(acceleration)


def run_baseline(training_csv=TRAINING_CSV, vehicle_csv=VEHICLE_CSV,
                 outage_start=OUTAGE_START, outage_duration=OUTAGE_DURATION,
                 output_csv=OUTPUT_CSV, plots_dir=PLOTS_DIR):
    smartphone, time_s = load_smartphone_data(training_csv)
    vehicle = load_vehicle_evaluation(vehicle_csv)
    outage_end = outage_start + outage_duration
    outage_mask = (time_s >= outage_start) & (time_s < outage_end)
    if not np.any(outage_mask):
        raise ValueError("The requested outage contains no smartphone samples")

    start_index = np.flatnonzero(outage_mask)[0]
    end_index = np.flatnonzero(outage_mask)[-1]
    initial_vehicle_index, initial_speed, initial_heading = pre_outage_initial_state(vehicle, outage_start)

    reference_lat = np.interp(time_s, vehicle["time_s"], vehicle["latitude"])
    reference_lon = np.interp(time_s, vehicle["time_s"], vehicle["longitude"])
    reference_x, reference_y = latlon_to_enu(
        reference_lat, reference_lon, vehicle["latitude"][0], vehicle["longitude"][0])
    initial_x = np.interp(time_s[start_index], vehicle["time_s"][:initial_vehicle_index + 1], vehicle["latitude"][:initial_vehicle_index + 1])
    initial_y = np.interp(time_s[start_index], vehicle["time_s"][:initial_vehicle_index + 1], vehicle["longitude"][:initial_vehicle_index + 1])
    initial_x, initial_y = latlon_to_enu(initial_x, initial_y, vehicle["latitude"][0], vehicle["longitude"][0])
    initial_x, initial_y = float(initial_x), float(initial_y)

    azimuth = smartphone["OR_AZ"]
    pitch = smartphone["OR_P"]
    roll = smartphone["OR_R"]
    linear_acceleration = np.column_stack((
        smartphone["ACCEL_X"] - smartphone["GRAV_X"],
        smartphone["ACCEL_Y"] - smartphone["GRAV_Y"],
        smartphone["ACCEL_Z"] - smartphone["GRAV_Z"],
    ))
    navigation_acceleration = orientation_to_navigation(linear_acceleration, azimuth, pitch, roll)

    estimated_x = np.full(len(time_s), np.nan)
    estimated_y = np.full(len(time_s), np.nan)
    estimated_speed = np.full(len(time_s), np.nan)
    estimated_heading = np.full(len(time_s), np.nan)
    estimated_x[start_index] = initial_x
    estimated_y[start_index] = initial_y
    estimated_speed[start_index] = initial_speed
    estimated_heading[start_index] = initial_heading
    velocity = np.array([initial_speed * sin(radians(initial_heading)), initial_speed * cos(radians(initial_heading))])

    # GPS/vehicle values are intentionally absent from this outage propagation loop.
    for index in range(start_index + 1, end_index + 1):
        dt = time_s[index] - time_s[index - 1]
        velocity += navigation_acceleration[index, :2] * dt
        estimated_x[index] = estimated_x[index - 1] + velocity[0] * dt
        estimated_y[index] = estimated_y[index - 1] + velocity[1] * dt
        estimated_speed[index] = np.linalg.norm(velocity)
        estimated_heading[index] = np.degrees(np.arctan2(velocity[0], velocity[1])) % 360.0

    position_error = np.hypot(estimated_x - reference_x, estimated_y - reference_y)
    outage_error = position_error[outage_mask]
    metrics = {
        "rmse_m": float(np.sqrt(np.mean(outage_error ** 2))),
        "mean_error_m": float(np.mean(outage_error)),
        "max_error_m": float(np.max(outage_error)),
        "final_error_m": float(position_error[end_index]),
        "drift_rate_mps": float(position_error[end_index] / outage_duration),
    }

    output = pd.DataFrame({
        "time_s": time_s, "reference_x": reference_x, "reference_y": reference_y,
        "dr_x": estimated_x, "dr_y": estimated_y, "position_error_m": position_error,
        "estimated_heading_deg": estimated_heading, "estimated_speed_mps": estimated_speed,
        "outage": outage_mask,
    })
    os.makedirs(os.path.dirname(output_csv) or ".", exist_ok=True)
    os.makedirs(plots_dir, exist_ok=True)
    output.to_csv(output_csv, index=False)

    plt.figure(figsize=(9, 6))
    plt.plot(reference_x, reference_y, label="Evaluation reference")
    plt.plot(estimated_x, estimated_y, label="Smartphone IMU DR")
    plt.axis("equal")
    plt.xlabel("East (m)")
    plt.ylabel("North (m)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "gps_denied_imu_trajectory.png"), dpi=150)
    plt.close()

    plot_specs = [
        ("gps_denied_imu_error.png", position_error, "Position error (m)"),
        ("gps_denied_imu_heading.png", estimated_heading, "Estimated heading (degrees)"),
        ("gps_denied_imu_speed.png", estimated_speed, "Estimated speed (m/s)"),
    ]
    for filename, values, ylabel in plot_specs:
        plt.figure(figsize=(9, 4))
        plt.plot(time_s, values)
        plt.axvspan(outage_start, outage_end, color="orange", alpha=0.2)
        plt.xlabel("Time (s)")
        plt.ylabel(ylabel)
        plt.tight_layout()
        plt.savefig(os.path.join(plots_dir, filename), dpi=150)
        plt.close()

    orientation_note = (
        f"pitch range={pitch.min():.2f}..{pitch.max():.2f} deg, "
        f"roll range={roll.min():.2f}..{roll.max():.2f} deg"
    )
    print("PREDICTION INPUTS DURING GPS OUTAGE:")
    print("- smartphone accelerometer")
    print("- smartphone gyroscope (recorded; not directly integrated in this baseline)")
    print("- smartphone gravity/orientation")
    print("- propagated velocity and position state")
    print("FORBIDDEN DURING GPS OUTAGE:")
    print("- GPS position")
    print("- GPS speed")
    print("- vehicle speed")
    print("- vehicle heading")
    print("- vehicle telemetry")
    print("EVALUATION ONLY:")
    print("- reference GPS/vehicle trajectory")
    print(f"ORIENTATION DATASET NOTE: {orientation_note}; values were not corrected.")
    print(f"INITIAL STATE: pre-outage vehicle sample index {initial_vehicle_index}, used only at initialization")
    print("GPS-DENIED IMU BASELINE RESULTS")
    for name, value in metrics.items():
        print(f"{name}: {value:.6f}")
    print(f"results_csv: {output_csv}")
    return metrics


def main():
    parser = argparse.ArgumentParser(description="Run smartphone-IMU-only GPS-denied dead reckoning")
    parser.add_argument("--training-csv", default=TRAINING_CSV)
    parser.add_argument("--vehicle-csv", default=VEHICLE_CSV)
    parser.add_argument("--outage-start", type=float, default=OUTAGE_START)
    parser.add_argument("--outage-duration", type=float, default=OUTAGE_DURATION)
    parser.add_argument("--output-csv", default=OUTPUT_CSV)
    parser.add_argument("--plots-dir", default=PLOTS_DIR)
    args = parser.parse_args()
    run_baseline(**vars(args))


if __name__ == "__main__":
    main()