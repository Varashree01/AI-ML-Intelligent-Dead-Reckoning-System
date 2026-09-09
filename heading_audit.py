"""Offline audit of smartphone heading sources; does not modify the EKF."""

import os
from math import cos, radians, sin

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial.transform import Rotation


DATA_DIR = "data"
PLOT_DIR = "plots"
TRAINING_CSV = os.path.join(DATA_DIR, "training_dataset.csv")
EKF_RESULTS = os.path.join(DATA_DIR, "ekf_dead_reckoning_results.csv")
ORIGINAL_S_CSV = os.path.join("IO-VNBD-GIT", "Synchronised V abd S datasets", "Uncategorised IOVNB Dataset", "S-Dataset", "S-S1.csv")
VEHICLE_CSV = os.path.join("IO-VNBD-GIT", "Synchronised V abd S datasets", "Uncategorised IOVNB Dataset", "V-Dataset", "V-S1.csv")
OUTAGE_START = 60.0
OUTAGE_END = 120.0


def numeric(frame, column):
    values = pd.to_numeric(frame[column], errors="coerce").interpolate().bfill().ffill()
    if values.isna().any():
        raise ValueError(f"No usable numeric values in {column}")
    return values.to_numpy(dtype=float)


def find_column(columns, keywords):
    for keyword in keywords:
        for column in columns:
            if keyword.lower() in str(column).lower():
                return column
    raise ValueError(f"Missing column matching {keywords}")


def wrap_degrees(values):
    return (np.asarray(values) + 180.0) % 360.0 - 180.0


def circular_mean_degrees(values):
    return float(np.degrees(np.angle(np.mean(np.exp(1j * np.deg2rad(values))))))


def circular_error(estimator, reference):
    return wrap_degrees(estimator - reference)


def load_phone():
    columns = ["time_s", "ACCEL_X", "ACCEL_Y", "ACCEL_Z", "GYRO_X", "GYRO_Y", "GYRO_Z", "GRAV_X", "GRAV_Y", "GRAV_Z", "MAG_X", "MAG_Y", "MAG_Z", "OR_AZ", "OR_P", "OR_R"]
    frame = pd.read_csv(TRAINING_CSV, encoding="cp1252", usecols=columns)
    phone = {column: numeric(frame, column) for column in columns}
    time_s = phone["time_s"] - phone["time_s"][0]
    if np.any(np.diff(time_s) <= 0):
        raise ValueError("Smartphone timestamps are not strictly increasing")
    return phone, time_s


def load_vehicle():
    frame = pd.read_csv(VEHICLE_CSV, encoding="cp1252")
    time = numeric(frame, find_column(frame.columns, ["time since start of day", "time since start"])).copy()
    time -= time[0]
    order = np.argsort(time)
    return {
        "time_s": time[order],
        "heading": numeric(frame, find_column(frame.columns, ["heading"]))[order],
    }


def load_original_column_audit():
    frame = pd.read_csv(ORIGINAL_S_CSV, encoding="cp1252", nrows=1)
    requested = {
        "ORIENTATION (Azimuth)": ["orientation (azimuth)"],
        "ORIENTATION (Pitch)": ["orientation (pitch)"],
        "ORIENTATION (Roll)": ["orientation (roll"],
        "GYROSCOPE X": ["gyroscope x"], "GYROSCOPE Y": ["gyroscope y"], "GYROSCOPE Z": ["gyroscope z"],
        "MAGNETIC FIELD X": ["magnetic field x"], "MAGNETIC FIELD Y": ["magnetic field y"], "MAGNETIC FIELD Z": ["magnetic field z"],
    }
    return {name: find_column(frame.columns, patterns) for name, patterns in requested.items()}


def calibrate_to_vehicle(source, vehicle_heading, pre_mask):
    offset = circular_mean_degrees(vehicle_heading[pre_mask] - source[pre_mask])
    return (source + offset) % 360.0, offset


def gyro_heading(phone, time_s, bias):
    yaw = np.empty(len(time_s))
    yaw[0] = phone["OR_AZ"][0]
    yaw[1:] = yaw[0] + np.cumsum((phone["GYRO_Z"][1:] - bias) * np.diff(time_s) * 180.0 / np.pi)
    return np.mod(yaw, 360.0)


def magnetometer_heading(phone):
    magnetic = np.column_stack([phone[f"MAG_{axis}"] for axis in "XYZ"])
    rotations = Rotation.from_euler("ZYX", np.column_stack([phone["OR_AZ"], phone["OR_P"], phone["OR_R"]]), degrees=True)
    navigation_magnetic = rotations.apply(magnetic)
    return np.mod(np.degrees(np.arctan2(navigation_magnetic[:, 0], navigation_magnetic[:, 1])), 360.0), magnetic, navigation_magnetic


def heading_metrics(estimate, reference, outage):
    error = circular_error(estimate[outage], reference[outage])
    return {"mean_abs_error_deg": float(np.mean(np.abs(error))), "rmse_deg": float(np.sqrt(np.mean(error ** 2))), "final_error_deg": float(abs(error[-1])), "max_abs_error_deg": float(np.max(np.abs(error)))}


def main():
    os.makedirs(PLOT_DIR, exist_ok=True)
    phone, time_s = load_phone()
    vehicle = load_vehicle()
    vehicle_heading = np.mod(np.interp(time_s, vehicle["time_s"], np.unwrap(np.deg2rad(vehicle["heading"])) * 180.0 / np.pi), 360.0)
    outage = (time_s >= OUTAGE_START) & (time_s < OUTAGE_END)
    pre = time_s < OUTAGE_START
    recovery = time_s >= OUTAGE_END
    if not outage.any():
        raise ValueError("Configured outage has no smartphone samples")

    raw_azimuth, azimuth_offset = calibrate_to_vehicle(phone["OR_AZ"], vehicle_heading, pre)
    early_bias_mask = time_s < min(5.0, OUTAGE_START)
    gyro_bias = float(np.median(phone["GYRO_Z"][early_bias_mask]))
    gyro_raw = gyro_heading(phone, time_s, 0.0)
    gyro_corrected = gyro_heading(phone, time_s, gyro_bias)
    gyro_raw, gyro_offset = calibrate_to_vehicle(gyro_raw, vehicle_heading, pre)
    gyro_corrected, gyro_corrected_offset = calibrate_to_vehicle(gyro_corrected, vehicle_heading, pre)
    magnetometer_raw, magnetic_body, magnetic_navigation = magnetometer_heading(phone)
    magnetometer, magnetometer_offset = calibrate_to_vehicle(magnetometer_raw, vehicle_heading, pre)

    ekf_frame = pd.read_csv(EKF_RESULTS)
    ekf_yaw = np.mod(np.rad2deg(np.unwrap(ekf_frame["ekf_yaw"].to_numpy(dtype=float))), 360.0)
    ekf_yaw, ekf_offset = calibrate_to_vehicle(ekf_yaw, vehicle_heading, pre)
    estimators = {"raw smartphone azimuth": raw_azimuth, "gyro integrated yaw": gyro_raw, "bias-corrected gyro yaw": gyro_corrected, "magnetometer heading": magnetometer, "existing EKF yaw": ekf_yaw}
    metrics = {name: heading_metrics(values, vehicle_heading, outage) for name, values in estimators.items()}

    magnetic_magnitude = np.linalg.norm(magnetic_body, axis=1)
    magnitude_median = np.median(magnetic_magnitude)
    magnitude_mad = np.median(np.abs(magnetic_magnitude - magnitude_median))
    magnetic_disturbance = np.abs(magnetic_magnitude - magnitude_median) > max(5.0 * magnitude_mad, 1.0)
    hard_iron = np.mean(magnetic_body, axis=0)
    gyro_accumulation_raw = np.rad2deg(np.cumsum(phone["GYRO_Z"] * np.r_[0.0, np.diff(time_s)]))
    gyro_accumulation_corrected = np.rad2deg(np.cumsum((phone["GYRO_Z"] - gyro_bias) * np.r_[0.0, np.diff(time_s)]))

    plt.figure(figsize=(10, 5)); plt.plot(time_s, raw_azimuth); plt.axvspan(OUTAGE_START, OUTAGE_END, color="orange", alpha=0.2); plt.ylabel("Heading (deg)"); plt.xlabel("Time (s)"); plt.tight_layout(); plt.savefig(os.path.join(PLOT_DIR, "heading_audit_raw_azimuth.png"), dpi=150); plt.close()
    plt.figure(figsize=(10, 5)); plt.plot(time_s, gyro_raw); plt.axvspan(OUTAGE_START, OUTAGE_END, color="orange", alpha=0.2); plt.ylabel("Heading (deg)"); plt.xlabel("Time (s)"); plt.tight_layout(); plt.savefig(os.path.join(PLOT_DIR, "heading_audit_gyro_yaw.png"), dpi=150); plt.close()
    plt.figure(figsize=(10, 5)); plt.plot(time_s, gyro_corrected); plt.axvspan(OUTAGE_START, OUTAGE_END, color="orange", alpha=0.2); plt.ylabel("Heading (deg)"); plt.xlabel("Time (s)"); plt.tight_layout(); plt.savefig(os.path.join(PLOT_DIR, "heading_audit_bias_corrected_yaw.png"), dpi=150); plt.close()
    plt.figure(figsize=(10, 5)); plt.plot(time_s, magnetometer, label="tilt-compensated magnetometer"); plt.plot(time_s, vehicle_heading, label="vehicle evaluation reference", alpha=0.7); plt.axvspan(OUTAGE_START, OUTAGE_END, color="orange", alpha=0.2); plt.legend(); plt.ylabel("Heading (deg)"); plt.xlabel("Time (s)"); plt.tight_layout(); plt.savefig(os.path.join(PLOT_DIR, "heading_audit_magnetometer.png"), dpi=150); plt.close()
    plt.figure(figsize=(11, 6));
    for name, values in estimators.items(): plt.plot(time_s, values, label=name)
    plt.plot(time_s, vehicle_heading, "k--", label="vehicle evaluation only")
    plt.axvspan(0, OUTAGE_START, color="green", alpha=0.08, label="GPS available / calibration")
    plt.axvspan(OUTAGE_START, OUTAGE_END, color="orange", alpha=0.15, label="GPS denied")
    plt.axvspan(OUTAGE_END, time_s[-1], color="blue", alpha=0.06, label="GPS recovery")
    plt.ylabel("Heading (deg)"); plt.xlabel("Time (s)"); plt.legend(fontsize=8); plt.tight_layout(); plt.savefig(os.path.join(PLOT_DIR, "heading_audit_comparison.png"), dpi=150); plt.close()
    plt.figure(figsize=(10, 5)); plt.plot(time_s, gyro_accumulation_raw, label="raw integrated gyro Z"); plt.plot(time_s, gyro_accumulation_corrected, label="early-window bias corrected"); plt.axvspan(OUTAGE_START, OUTAGE_END, color="orange", alpha=0.2); plt.legend(); plt.ylabel("Accumulated yaw (deg)"); plt.xlabel("Time (s)"); plt.tight_layout(); plt.savefig(os.path.join(PLOT_DIR, "heading_audit_gyro_bias.png"), dpi=150); plt.close()

    best_name = min(metrics, key=lambda name: metrics[name]["rmse_deg"])
    print("SMARTPHONE ORIGINAL-COLUMN MAPPING:")
    for source, column in load_original_column_audit().items(): print(f"- {source}: {column}")
    print("ANGLE CONVENTIONS:")
    print("- Smartphone azimuth and vehicle heading are degree-valued compass bearings: 0 degrees is north, increasing clockwise toward east.")
    print("- ENU is x=East, y=North; compass bearing maps East=sin(theta), North=cos(theta).")
    print("- Gyro Z is consumed as rad/s and integrated into a compass-angle estimate with positive sign; outputs are converted to degrees and wrapped to 0..360.")
    print("- Magnetometer uses recorded ZYX azimuth/pitch/roll for tilt compensation; no outage-derived correction is applied.")
    print("PREDICTION INPUTS:")
    print("- Smartphone azimuth/orientation, accelerometer/gravity, gyroscope, and magnetometer candidates; existing EKF yaw is read only for comparison.")
    print("EVALUATION-ONLY DATA:")
    print("- Vehicle heading, used for pre-outage fixed-offset calibration and outage scoring; it is not used in any candidate propagation.")
    print("GYRO Z BIAS ANALYSIS:")
    print(f"- Estimate from median first 5 seconds only: {gyro_bias:.9f} rad/s ({np.degrees(gyro_bias):.6f} deg/s)")
    print(f"- Raw accumulated yaw at 60 s: {gyro_accumulation_raw[np.flatnonzero(time_s >= OUTAGE_START)[0]]:.6f} deg")
    print(f"- Bias-corrected accumulated yaw at 60 s: {gyro_accumulation_corrected[np.flatnonzero(time_s >= OUTAGE_START)[0]]:.6f} deg")
    print("MAGNETOMETER ANALYSIS:")
    print(f"- Magnitude median={magnitude_median:.6f}, MAD={magnitude_mad:.6f}, disturbed samples={int(magnetic_disturbance.sum())}/{len(magnetic_disturbance)}")
    print(f"- Body-axis mean (hard-iron indication): [{hard_iron[0]:.6f}, {hard_iron[1]:.6f}, {hard_iron[2]:.6f}] uT")
    print("- Tilt compensation is computationally possible because azimuth/pitch/roll are present, but the recorded pitch/roll ranges may make the result unreliable.")
    print("HEADING METRICS DURING GPS OUTAGE:")
    print(pd.DataFrame(metrics).T.to_string())
    print(f"BEST HEADING SOURCE: {best_name}")
    print(f"CURRENT EKF YAW SHOULD BE CHANGED: {'YES' if metrics['existing EKF yaw']['rmse_deg'] > metrics[best_name]['rmse_deg'] else 'NO based on RMSE alone'}")
    print("RECOMMENDED EKF MODIFICATION: use a smartphone-only gyro/attitude yaw prediction, estimate gyro bias from a documented pre-outage calibration window, and add magnetometer yaw updates only after disturbance/quality gating; retain vehicle heading solely for offline evaluation.")


if __name__ == "__main__":
    main()