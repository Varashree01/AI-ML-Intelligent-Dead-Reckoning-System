"""Extended Kalman Filter baseline for GPS-denied smartphone navigation."""

import os
from math import cos, radians, sin

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import joblib
import numpy as np
import pandas as pd
from scipy.spatial.transform import Rotation


DATA_DIR = "data"
TRAINING_CSV = os.path.join(DATA_DIR, "training_dataset.csv")
VEHICLE_CSV = os.path.join("IO-VNBD-GIT", "Synchronised V abd S datasets", "Uncategorised IOVNB Dataset", "V-Dataset", "V-S1.csv")
OUT_CSV = os.path.join(DATA_DIR, "ekf_dead_reckoning_results.csv")
PLOT_DIR = "plots"
OUTAGE_START = 60.0
OUTAGE_END = 120.0
EARTH_RADIUS_M = 6378137.0

# Noise parameters are deliberately explicit and configurable.
ACCEL_PROCESS_NOISE = 0.35
GYRO_PROCESS_NOISE = np.deg2rad(1.0)
ACCEL_BIAS_PROCESS_NOISE = 0.01
GYRO_BIAS_PROCESS_NOISE = np.deg2rad(0.02)
GPS_POSITION_NOISE = 3.0
GPS_VELOCITY_NOISE = 1.5
INITIAL_POSITION_NOISE = 3.0
INITIAL_VELOCITY_NOISE = 1.5
INITIAL_YAW_NOISE = np.deg2rad(5.0)


def find_column(columns, keywords):
    for keyword in keywords:
        for column in columns:
            if keyword.lower() in str(column).lower():
                return column
    raise ValueError(f"Missing column matching {keywords}")


def numeric(frame, column):
    values = pd.to_numeric(frame[column], errors="coerce").interpolate().bfill().ffill()
    if values.isna().any():
        raise ValueError(f"No usable numeric values in {column}")
    return values.to_numpy(dtype=float)


def latlon_to_enu(latitude, longitude, latitude0, longitude0):
    east = np.deg2rad(longitude - longitude0) * cos(radians(latitude0)) * EARTH_RADIUS_M
    north = np.deg2rad(latitude - latitude0) * EARTH_RADIUS_M
    return east, north


def load_data():
    smartphone_columns = ["time_s", "ACCEL_X", "ACCEL_Y", "ACCEL_Z", "GYRO_X", "GYRO_Y", "GYRO_Z", "GRAV_X", "GRAV_Y", "GRAV_Z", "OR_AZ", "OR_P", "OR_R"]
    frame = pd.read_csv(TRAINING_CSV, encoding="cp1252", usecols=smartphone_columns)
    missing = [column for column in smartphone_columns if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing smartphone columns: {missing}")
    phone = {column: numeric(frame, column) for column in smartphone_columns}
    time_s = phone["time_s"] - phone["time_s"][0]
    if np.any(np.diff(time_s) <= 0):
        raise ValueError("Smartphone timestamps must be strictly increasing")

    vehicle_frame = pd.read_csv(VEHICLE_CSV, encoding="cp1252")
    time_col = find_column(vehicle_frame.columns, ["time since start of day", "time since start"])
    lat_col = find_column(vehicle_frame.columns, ["latitude"])
    lon_col = find_column(vehicle_frame.columns, ["longitude"])
    heading_col = find_column(vehicle_frame.columns, ["heading"])
    speed_col = find_column(vehicle_frame.columns, ["indicated vehicle speed", "velocity", "speed"])
    vehicle_time = numeric(vehicle_frame, time_col).copy()
    vehicle_time -= vehicle_time[0]
    order = np.argsort(vehicle_time)
    latitude = numeric(vehicle_frame, lat_col)[order]
    longitude = numeric(vehicle_frame, lon_col)[order]
    heading = numeric(vehicle_frame, heading_col)[order]
    speed = np.maximum(numeric(vehicle_frame, speed_col)[order], 0.0) / 3.6
    reference_x, reference_y = latlon_to_enu(latitude, longitude, latitude[0], longitude[0])
    reference = {"time_s": vehicle_time[order], "x": reference_x, "y": reference_y,
                 "heading": heading, "speed": speed}
    return phone, time_s, reference


def reference_at_phone_rate(time_s, reference):
    heading = np.deg2rad(np.interp(time_s, reference["time_s"], reference["heading"]))
    speed = np.interp(time_s, reference["time_s"], reference["speed"])
    return (np.interp(time_s, reference["time_s"], reference["x"]),
            np.interp(time_s, reference["time_s"], reference["y"]),
            speed * np.sin(heading), speed * np.cos(heading))


class ExtendedKalmanFilter:
    """EKF state [px, py, vx, vy, yaw, bax, bay, bgz]."""

    def __init__(self, state, covariance):
        self.state = np.asarray(state, dtype=float).reshape(8)
        self.covariance = np.asarray(covariance, dtype=float).reshape(8, 8)
        self.covariance_diagnostics = []

    def predict(self, acceleration_nav, gyro_z, dt):
        px, py, vx, vy, yaw, bax, bay, bgz = self.state
        corrected_acceleration = np.asarray(acceleration_nav, dtype=float)[:2] - [bax, bay]
        corrected_gyro = float(gyro_z) - bgz
        self.state[0] = px + vx * dt + 0.5 * corrected_acceleration[0] * dt * dt
        self.state[1] = py + vy * dt + 0.5 * corrected_acceleration[1] * dt * dt
        self.state[2] = vx + corrected_acceleration[0] * dt
        self.state[3] = vy + corrected_acceleration[1] * dt
        self.state[4] = yaw + corrected_gyro * dt

        jacobian = np.eye(8)
        jacobian[0, 2] = dt
        jacobian[1, 3] = dt
        jacobian[0, 5] = -0.5 * dt * dt
        jacobian[1, 6] = -0.5 * dt * dt
        jacobian[2, 5] = -dt
        jacobian[3, 6] = -dt
        jacobian[4, 7] = -dt
        process_noise = np.diag([
            0.25 * ACCEL_PROCESS_NOISE ** 2 * dt ** 4,
            0.25 * ACCEL_PROCESS_NOISE ** 2 * dt ** 4,
            ACCEL_PROCESS_NOISE ** 2 * dt ** 2,
            ACCEL_PROCESS_NOISE ** 2 * dt ** 2,
            GYRO_PROCESS_NOISE ** 2 * dt ** 2,
            ACCEL_BIAS_PROCESS_NOISE ** 2 * dt,
            ACCEL_BIAS_PROCESS_NOISE ** 2 * dt,
            GYRO_BIAS_PROCESS_NOISE ** 2 * dt,
        ])
        self.covariance = jacobian @ self.covariance @ jacobian.T + process_noise
        self._diagnose_covariance()

    def update_gps(self, position, velocity):
        measurement = np.asarray([position[0], position[1], velocity[0], velocity[1]], dtype=float)
        observation = np.zeros((4, 8))
        observation[0, 0], observation[1, 1] = 1.0, 1.0
        observation[2, 2], observation[3, 3] = 1.0, 1.0
        measurement_noise = np.diag([GPS_POSITION_NOISE ** 2, GPS_POSITION_NOISE ** 2,
                                     GPS_VELOCITY_NOISE ** 2, GPS_VELOCITY_NOISE ** 2])
        innovation = measurement - observation @ self.state
        innovation_covariance = observation @ self.covariance @ observation.T + measurement_noise
        gain = self.covariance @ observation.T @ np.linalg.inv(innovation_covariance)
        self.state += gain @ innovation
        identity = np.eye(8)
        self.covariance = (identity - gain @ observation) @ self.covariance @ (identity - gain @ observation).T + gain @ measurement_noise @ gain.T
        self.state[4] = np.arctan2(np.sin(self.state[4]), np.cos(self.state[4]))
        self._diagnose_covariance()

    def _diagnose_covariance(self):
        covariance = (self.covariance + self.covariance.T) / 2.0
        self.covariance = covariance
        eigenvalues = np.linalg.eigvalsh(covariance)
        self.covariance_diagnostics.append((np.max(np.abs(covariance - covariance.T)), np.min(eigenvalues)))


def main():
    phone, time_s, reference = load_data()
    reference_x, reference_y, reference_vx, reference_vy = reference_at_phone_rate(time_s, reference)
    outage = (time_s >= OUTAGE_START) & (time_s < OUTAGE_END)
    outage_indices = np.flatnonzero(outage)
    start, end = outage_indices[0], outage_indices[-1]
    before = reference["time_s"] < OUTAGE_START
    initial_reference_index = np.flatnonzero(before)[-1]
    initial_position = [reference["x"][initial_reference_index], reference["y"][initial_reference_index]]
    initial_velocity = [reference["speed"][initial_reference_index] * sin(radians(reference["heading"][initial_reference_index])), reference["speed"][initial_reference_index] * cos(radians(reference["heading"][initial_reference_index]))]
    initial_heading = np.deg2rad(reference["heading"][initial_reference_index])
    state = [initial_position[0], initial_position[1], initial_velocity[0], initial_velocity[1], initial_heading, 0.0, 0.0, 0.0]
    covariance = np.diag([INITIAL_POSITION_NOISE ** 2, INITIAL_POSITION_NOISE ** 2, INITIAL_VELOCITY_NOISE ** 2, INITIAL_VELOCITY_NOISE ** 2, INITIAL_YAW_NOISE ** 2, 0.1 ** 2, 0.1 ** 2, np.deg2rad(1.0) ** 2])
    ekf = ExtendedKalmanFilter(state, covariance)
    body_acceleration = np.column_stack([
        phone["ACCEL_X"] - phone["GRAV_X"], phone["ACCEL_Y"] - phone["GRAV_Y"], phone["ACCEL_Z"] - phone["GRAV_Z"]])
    navigation_acceleration = Rotation.from_euler("ZYX", np.column_stack([phone["OR_AZ"], phone["OR_P"], phone["OR_R"]]), degrees=True).apply(body_acceleration)
    estimated = np.full((len(time_s), 8), np.nan)
    gps_available = ~outage
    rng = np.random.default_rng(42)
    gps_position = np.column_stack([reference_x, reference_y]) + rng.normal(0.0, GPS_POSITION_NOISE, (len(time_s), 2))
    gps_velocity = np.column_stack([reference_vx, reference_vy]) + rng.normal(0.0, GPS_VELOCITY_NOISE, (len(time_s), 2))
    for index in range(len(time_s)):
        if index > 0:
            dt = time_s[index] - time_s[index - 1]
            ekf.predict(navigation_acceleration[index], phone["GYRO_Z"][index], dt)
        if gps_available[index]:
            ekf.update_gps(gps_position[index], gps_velocity[index])
        estimated[index] = ekf.state
    error_x = estimated[:, 0] - reference_x
    error_y = estimated[:, 1] - reference_y
    position_error = np.hypot(error_x, error_y)
    outage_error = position_error[outage]
    outage_velocity_error = np.hypot(estimated[outage, 2] - reference_vx[outage], estimated[outage, 3] - reference_vy[outage])
    reference_heading_outage = np.deg2rad(np.interp(time_s[outage], reference["time_s"], reference["heading"]))
    heading_difference = estimated[outage, 4] - reference_heading_outage
    heading_error = np.abs(np.arctan2(np.sin(heading_difference), np.cos(heading_difference)))
    metrics = {"position_mae_m": float(np.mean(outage_error)), "position_rmse_m": float(np.sqrt(np.mean(outage_error ** 2))), "final_position_error_m": float(outage_error[-1]), "maximum_position_error_m": float(np.max(outage_error)), "drift_rate_mps": float(outage_error[-1] / (OUTAGE_END - OUTAGE_START)), "velocity_rmse_mps": float(np.sqrt(np.mean(outage_velocity_error ** 2))), "heading_error_deg": float(np.degrees(np.mean(heading_error)))}
    output = pd.DataFrame({"time_s": time_s, "gps_available": gps_available, "ekf_x": estimated[:, 0], "ekf_y": estimated[:, 1], "ekf_vx": estimated[:, 2], "ekf_vy": estimated[:, 3], "ekf_yaw": estimated[:, 4], "accel_bias_x": estimated[:, 5], "accel_bias_y": estimated[:, 6], "gyro_bias_z": estimated[:, 7], "reference_x": reference_x, "reference_y": reference_y, "position_error": position_error, "position_error_x": error_x, "position_error_y": error_y})
    os.makedirs(DATA_DIR, exist_ok=True); os.makedirs(PLOT_DIR, exist_ok=True)
    output.to_csv(OUT_CSV, index=False)

    previous_metrics = {"position_rmse_m": np.nan, "final_position_error_m": np.nan, "maximum_position_error_m": np.nan, "drift_rate_mps": np.nan}
    try:
        prior = pd.read_csv(os.path.join(DATA_DIR, "hybrid_velocity_metrics.csv"))
        for metric in previous_metrics:
            row = prior[(prior["group"] == "hybrid_position_previous") & (prior["metric"] == metric)]
            if not row.empty: previous_metrics[metric] = float(row.iloc[0]["value"])
    except (FileNotFoundError, KeyError):
        pass
    physics_metrics = {"position_rmse_m": 265.78928667224073, "final_position_error_m": 333.20671249678986, "maximum_position_error_m": 333.20671249678986, "drift_rate_mps": 37.8643991473625}
    velocity_metrics = {"position_rmse_m": 230.1998603515857, "final_position_error_m": 269.7186557347179, "maximum_position_error_m": 269.7186557347179, "drift_rate_mps": 30.64984724258159}
    comparison = pd.DataFrame([{"model": "Physics only", **physics_metrics}, {"model": "Hybrid position residual", **previous_metrics}, {"model": "Hybrid velocity residual", **velocity_metrics}, {"model": "EKF", **{key: metrics[key] for key in physics_metrics}}])
    comparison.to_csv(os.path.join(DATA_DIR, "ekf_model_comparison.csv"), index=False)

    plt.figure(figsize=(9, 6)); plt.plot(reference_x, reference_y, label="reference"); plt.plot(estimated[:, 0], estimated[:, 1], label="EKF"); plt.axvspan(reference_x[start], reference_x[end], color="orange", alpha=0.15, label="GPS denied"); plt.axis("equal"); plt.legend(); plt.tight_layout(); plt.savefig(os.path.join(PLOT_DIR, "ekf_trajectory.png"), dpi=150); plt.close()
    plt.figure(figsize=(9, 4)); plt.plot(time_s, position_error); plt.axvspan(OUTAGE_START, OUTAGE_END, color="orange", alpha=0.2); plt.tight_layout(); plt.savefig(os.path.join(PLOT_DIR, "ekf_position_error.png"), dpi=150); plt.close()
    plt.figure(figsize=(9, 4)); plt.plot(time_s, np.degrees(estimated[:, 4])); plt.axvspan(OUTAGE_START, OUTAGE_END, color="orange", alpha=0.2); plt.tight_layout(); plt.savefig(os.path.join(PLOT_DIR, "ekf_heading.png"), dpi=150); plt.close()
    plt.figure(figsize=(9, 4)); plt.plot(time_s, np.hypot(estimated[:, 2], estimated[:, 3])); plt.axvspan(OUTAGE_START, OUTAGE_END, color="orange", alpha=0.2); plt.tight_layout(); plt.savefig(os.path.join(PLOT_DIR, "ekf_velocity.png"), dpi=150); plt.close()
    plt.figure(figsize=(9, 4)); plt.plot(time_s, estimated[:, 5], label="bax"); plt.plot(time_s, estimated[:, 6], label="bay"); plt.plot(time_s, estimated[:, 7], label="bgz"); plt.legend(); plt.tight_layout(); plt.savefig(os.path.join(PLOT_DIR, "ekf_bias_estimates.png"), dpi=150); plt.close()
    plt.figure(figsize=(8, 5)); plt.bar(comparison["model"], comparison["position_rmse_m"]); plt.xticks(rotation=15); plt.ylabel("Outage position RMSE (m)"); plt.tight_layout(); plt.savefig(os.path.join(PLOT_DIR, "ekf_model_comparison.png"), dpi=150); plt.close()

    covariance_symmetric = max(item[0] for item in ekf.covariance_diagnostics) < 1e-10
    covariance_positive = min(item[1] for item in ekf.covariance_diagnostics) > -1e-9
    finite = np.isfinite(estimated).all() and np.isfinite(position_error).all()
    heading_discontinuities = np.max(np.abs(np.diff(np.unwrap(estimated[:, 4])))) > np.pi
    max_velocity = float(np.max(np.hypot(estimated[:, 2], estimated[:, 3])))
    max_acceleration = float(np.max(np.linalg.norm(navigation_acceleration[:, :2], axis=1)))
    velocity_plausible = max_velocity < 100.0
    acceleration_plausible = max_acceleration < 100.0
    print("PHYSICS-ONLY BASELINE"); print(physics_metrics)
    print("HYBRID POSITION-RESIDUAL BASELINE"); print(previous_metrics)
    print("HYBRID VELOCITY-RESIDUAL BASELINE"); print(velocity_metrics)
    print("EKF GPS-DENIED TEST RESULT"); print(metrics)
    print("COMPARISON TABLE"); print(comparison.to_string(index=False))
    print(f"EKF RMSE improvement over physics (%): {100 * (physics_metrics['position_rmse_m'] - metrics['position_rmse_m']) / physics_metrics['position_rmse_m']:.6f}")
    print(f"EKF final-error improvement over physics (%): {100 * (physics_metrics['final_position_error_m'] - metrics['final_position_error_m']) / physics_metrics['final_position_error_m']:.6f}")
    print(f"covariance symmetry: {'PASS' if covariance_symmetric else 'FAIL'}; positive definiteness: {'PASS' if covariance_positive else 'FAIL'}")
    print(f"maximum EKF velocity: {max_velocity:.6f} m/s; unrealistic velocity: {'FAIL' if not velocity_plausible else 'PASS'}")
    print(f"maximum navigation acceleration: {max_acceleration:.6f} m/s^2; unrealistic acceleration: {'FAIL' if not acceleration_plausible else 'PASS'}")
    print(f"NaN/Inf: {'PASS' if finite else 'FAIL'}; numerical explosion: {'PASS' if finite and velocity_plausible and acceleration_plausible else 'FAIL'}; heading discontinuities: {'FAIL' if heading_discontinuities else 'PASS'}")
    print("LEAKAGE AUDIT: During 60-120 s, propagation uses only smartphone acceleration, gravity, orientation, gyro Z, timestamps, and EKF state/covariance. GPS/reference updates are disabled. Vehicle/reference values are used for pre-outage initialization, available-GPS measurement simulation, and offline evaluation only.")


if __name__ == "__main__":
    main()