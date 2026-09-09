"""Causal hybrid physics + ML residual dead-reckoning baseline."""

import os
from math import cos, radians, sin

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


DATA_DIR = "data"
TRAINING_CSV = os.path.join(DATA_DIR, "training_dataset.csv")
VEHICLE_CSV = os.path.join("IO-VNBD-GIT", "Synchronised V abd S datasets", "Uncategorised IOVNB Dataset", "V-Dataset", "V-S1.csv")
WINDOW_SIZE = 20
OUTAGE_START = 60.0
OUTAGE_END = 120.0
EARTH_RADIUS_M = 6378137.0
BASE_CHANNELS = [
    "ACCEL_X", "ACCEL_Y", "ACCEL_Z", "GYRO_X", "GYRO_Y", "GYRO_Z",
    "GRAV_X", "GRAV_Y", "GRAV_Z", "MAG_X", "MAG_Y", "MAG_Z",
    "OR_AZ", "OR_P", "OR_R", "accel_mag", "gyro_mag", "time_delta",
]


def numeric(frame, column):
    values = pd.to_numeric(frame[column], errors="coerce").interpolate().bfill().ffill()
    if values.isna().any():
        raise ValueError(f"No usable values in {column}")
    return values.to_numpy(dtype=float)


def find_column(columns, keywords):
    for keyword in keywords:
        for column in columns:
            if keyword.lower() in str(column).lower():
                return column
    raise ValueError(f"Missing column matching {keywords}")


def latlon_to_enu(latitude, longitude, latitude0, longitude0):
    east = np.deg2rad(longitude - longitude0) * cos(radians(latitude0)) * EARTH_RADIUS_M
    north = np.deg2rad(latitude - latitude0) * EARTH_RADIUS_M
    return east, north


def load_inputs():
    required = ["time_s"] + BASE_CHANNELS[:15]
    phone_frame = pd.read_csv(TRAINING_CSV, encoding="cp1252", usecols=required)
    missing = [column for column in required if column not in phone_frame.columns]
    if missing:
        raise ValueError(f"Missing smartphone columns: {missing}")
    phone = {column: numeric(phone_frame, column) for column in required}
    phone["accel_mag"] = np.linalg.norm(np.column_stack([phone[f"ACCEL_{axis}"] for axis in "XYZ"]), axis=1)
    phone["gyro_mag"] = np.linalg.norm(np.column_stack([phone[f"GYRO_{axis}"] for axis in "XYZ"]), axis=1)
    phone["time_delta"] = np.r_[0.0, np.diff(phone["time_s"])]
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
    reference = {"time_s": vehicle_time[order], "x": reference_x, "y": reference_y, "heading": heading, "speed": speed}
    return phone, time_s, reference


def physics_trajectory(phone, time_s, reference):
    """Propagate a causal IMU physics trajectory from the allowed initial state."""
    outage = (time_s >= OUTAGE_START) & (time_s < OUTAGE_END)
    indices = np.flatnonzero(outage)
    if len(indices) < WINDOW_SIZE:
        raise ValueError("Outage is shorter than WINDOW_SIZE")
    start, end = indices[0], indices[-1]
    before = reference["time_s"] < OUTAGE_START
    initial_reference_index = np.flatnonzero(before)[-1]
    initial_speed = reference["speed"][initial_reference_index]
    initial_heading = reference["heading"][initial_reference_index]
    initial_x = np.interp(time_s[start], reference["time_s"][:initial_reference_index + 1], reference["x"][:initial_reference_index + 1])
    initial_y = np.interp(time_s[start], reference["time_s"][:initial_reference_index + 1], reference["y"][:initial_reference_index + 1])
    from scipy.spatial.transform import Rotation
    body_acceleration = np.column_stack([
        phone["ACCEL_X"] - phone["GRAV_X"], phone["ACCEL_Y"] - phone["GRAV_Y"], phone["ACCEL_Z"] - phone["GRAV_Z"]])
    navigation_acceleration = Rotation.from_euler(
        "ZYX", np.column_stack([phone["OR_AZ"], phone["OR_P"], phone["OR_R"]]), degrees=True).apply(body_acceleration)
    x = np.full(len(time_s), np.nan)
    y = np.full(len(time_s), np.nan)
    velocity = np.zeros((len(time_s), 2))
    acceleration_xy = navigation_acceleration[:, :2]
    x[start], y[start] = initial_x, initial_y
    velocity[start] = [initial_speed * sin(radians(initial_heading)), initial_speed * cos(radians(initial_heading))]
    for index in range(start + 1, end + 1):
        dt = time_s[index] - time_s[index - 1]
        velocity[index] = velocity[index - 1] + acceleration_xy[index] * dt
        x[index] = x[index - 1] + velocity[index, 0] * dt
        y[index] = y[index - 1] + velocity[index, 1] * dt
    return x, y, velocity, acceleration_xy, outage


def reference_at_phone_rate(time_s, reference):
    return (np.interp(time_s, reference["time_s"], reference["x"]),
            np.interp(time_s, reference["time_s"], reference["y"]))


def make_window_row(phone, time_s, velocity, acceleration_xy, start, end):
    values = []
    for channel in BASE_CHANNELS:
        window = phone[channel][start:end + 1]
        values.extend([np.mean(window), np.std(window), np.min(window), np.max(window),
                       np.ptp(window), np.sqrt(np.mean(window ** 2)), window[0], window[-1], window[-1] - window[0]])
    values.extend([np.sum(phone["time_delta"][start:end + 1]), time_s[end],
                   velocity[end - 1, 0], velocity[end - 1, 1],
                   acceleration_xy[end - 1, 0], acceleration_xy[end - 1, 1]])
    return values


def feature_names():
    names = []
    for channel in BASE_CHANNELS:
        names.extend([f"{channel}_{stat}" for stat in ("mean", "std", "min", "max", "range", "rms", "first", "last", "delta")])
    return names + ["window_duration", "current_time_s", "previous_velocity_x", "previous_velocity_y", "previous_acceleration_x", "previous_acceleration_y"]


def create_split(phone, time_s, velocity, acceleration_xy, physics_x, physics_y, reference_x, reference_y, start, end):
    rows = []
    for index in range(start + 1, end + 1):
        window_start = max(start, index - WINDOW_SIZE + 1)
        physics_dx = physics_x[index] - physics_x[index - 1]
        physics_dy = physics_y[index] - physics_y[index - 1]
        reference_dx = reference_x[index] - reference_x[index - 1]
        reference_dy = reference_y[index] - reference_y[index - 1]
        rows.append(make_window_row(phone, time_s, velocity, acceleration_xy, window_start, index) + [
            reference_dx - physics_dx, reference_dy - physics_dy, time_s[index],
            physics_dx, physics_dy, reference_dx, reference_dy])
    columns = feature_names() + ["residual_dx", "residual_dy", "time_s", "physics_delta_x", "physics_delta_y", "reference_delta_x", "reference_delta_y"]
    return pd.DataFrame(rows, columns=columns)


def fit_best_model(X_train, y_train, X_validation, y_validation):
    candidates = [(50, 1), (100, 1), (100, 2)]
    best_model, best_score = None, float("inf")
    for trees, leaf in candidates:
        model = RandomForestRegressor(n_estimators=trees, min_samples_leaf=leaf, random_state=42, n_jobs=-1)
        model.fit(X_train, y_train)
        score = mean_squared_error(y_validation, model.predict(X_validation)) ** 0.5
        if score < best_score:
            best_model, best_score = model, score
    return best_model, best_score


def trajectory_metrics(x, y, reference_x, reference_y, times):
    error = np.hypot(x - reference_x, y - reference_y)
    return {"position_mae_m": float(np.mean(error)), "position_rmse_m": float(np.sqrt(np.mean(error ** 2))),
            "final_position_error_m": float(error[-1]), "maximum_position_error_m": float(np.max(error)),
            "drift_rate_mps": float(error[-1] / (times[-1] - times[0]))}


def main():
    phone, time_s, reference = load_inputs()
    physics_x, physics_y, velocity, acceleration_xy, outage = physics_trajectory(phone, time_s, reference)
    reference_x, reference_y = reference_at_phone_rate(time_s, reference)
    outage_indices = np.flatnonzero(outage)
    start, end = outage_indices[0], outage_indices[-1]
    n = len(outage_indices)
    train_end = start + int(n * 0.70)
    validation_end = start + int(n * 0.85)
    split_frames = {
        "train": create_split(phone, time_s, velocity, acceleration_xy, physics_x, physics_y, reference_x, reference_y, start, train_end - 1),
        "validation": create_split(phone, time_s, velocity, acceleration_xy, physics_x, physics_y, reference_x, reference_y, train_end, validation_end - 1),
        "test": create_split(phone, time_s, velocity, acceleration_xy, physics_x, physics_y, reference_x, reference_y, validation_end, end),
    }
    names = feature_names()
    models = {}
    residual_predictions = {}
    metric_rows = []
    for target, model_key in [("residual_dx", "residual_model_dx"), ("residual_dy", "residual_model_dy")]:
        model, validation_rmse = fit_best_model(split_frames["train"][names], split_frames["train"][target], split_frames["validation"][names], split_frames["validation"][target])
        models[model_key] = model
        residual_predictions[target] = model.predict(split_frames["test"][names])
        metric_rows.append({"metric_group": "residual", "metric": target + "_MAE", "value": mean_absolute_error(split_frames["test"][target], residual_predictions[target])})
        metric_rows.append({"metric_group": "residual", "metric": target + "_RMSE", "value": mean_squared_error(split_frames["test"][target], residual_predictions[target]) ** 0.5})
        metric_rows.append({"metric_group": "residual", "metric": target + "_R2", "value": r2_score(split_frames["test"][target], residual_predictions[target])})
        print(f"selected {model_key}: validation RMSE={validation_rmse:.6f}")

    test = split_frames["test"]
    hybrid_x = np.zeros(len(test))
    hybrid_y = np.zeros(len(test))
    corrected_velocities = np.zeros((len(test), 2))
    current_x, current_y = physics_x[validation_end], physics_y[validation_end]
    previous_time = time_s[validation_end]
    for index, row in enumerate(test.itertuples(index=False)):
        corrected_delta = np.array([
            row.physics_delta_x + residual_predictions["residual_dx"][index],
            row.physics_delta_y + residual_predictions["residual_dy"][index],
        ])
        dt = row.time_s - previous_time
        corrected_velocities[index] = corrected_delta / dt
        current_x += corrected_delta[0]
        current_y += corrected_delta[1]
        hybrid_x[index], hybrid_y[index] = current_x, current_y
        previous_time = row.time_s
    physics_test_x = physics_x[validation_end + 1:end + 1]
    physics_test_y = physics_y[validation_end + 1:end + 1]
    reference_test_x = reference_x[validation_end + 1:end + 1]
    reference_test_y = reference_y[validation_end + 1:end + 1]
    test_times = time_s[validation_end + 1:end + 1]
    physics_metrics = trajectory_metrics(physics_test_x, physics_test_y, reference_test_x, reference_test_y, test_times)
    hybrid_metrics = trajectory_metrics(hybrid_x, hybrid_y, reference_test_x, reference_test_y, test_times)
    metric_rows += [{"metric_group": "physics_only", "metric": key, "value": value} for key, value in physics_metrics.items()]
    metric_rows += [{"metric_group": "hybrid_ml", "metric": key, "value": value} for key, value in hybrid_metrics.items()]
    rmse_improvement = 100 * (physics_metrics["position_rmse_m"] - hybrid_metrics["position_rmse_m"]) / physics_metrics["position_rmse_m"]
    final_improvement = 100 * (physics_metrics["final_position_error_m"] - hybrid_metrics["final_position_error_m"]) / physics_metrics["final_position_error_m"]
    metric_rows += [{"metric_group": "comparison", "metric": "RMSE_improvement_percent", "value": rmse_improvement}, {"metric_group": "comparison", "metric": "final_error_improvement_percent", "value": final_improvement}]

    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs("models", exist_ok=True)
    os.makedirs("plots", exist_ok=True)
    for name, frame in split_frames.items():
        frame.to_csv(os.path.join(DATA_DIR, f"hybrid_residual_{name}.csv"), index=False)
    joblib.dump({"model": models["residual_model_dx"], "features": names}, "models/hybrid_residual_dx.pkl")
    joblib.dump({"model": models["residual_model_dy"], "features": names}, "models/hybrid_residual_dy.pkl")
    pd.DataFrame(metric_rows).to_csv(os.path.join(DATA_DIR, "hybrid_residual_metrics.csv"), index=False)

    plt.figure(figsize=(9, 5)); plt.plot(test_times, reference_test_x, label="reference x"); plt.plot(test_times, physics_test_x, label="physics x"); plt.legend(); plt.tight_layout(); plt.savefig("plots/hybrid_physics_vs_reference.png", dpi=150); plt.close()
    plt.figure(figsize=(9, 5)); plt.plot(test_times, reference_test_x, label="reference x"); plt.plot(test_times, hybrid_x, label="hybrid x"); plt.legend(); plt.tight_layout(); plt.savefig("plots/hybrid_ml_vs_reference.png", dpi=150); plt.close()
    plt.figure(figsize=(9, 5)); plt.plot(test_times, np.hypot(physics_test_x - reference_test_x, physics_test_y - reference_test_y), label="physics-only"); plt.plot(test_times, np.hypot(hybrid_x - reference_test_x, hybrid_y - reference_test_y), label="hybrid ML"); plt.legend(); plt.tight_layout(); plt.savefig("plots/hybrid_error_comparison.png", dpi=150); plt.close()
    plt.figure(figsize=(9, 5)); plt.plot(test_times, test["residual_dx"], label="actual"); plt.plot(test_times, residual_predictions["residual_dx"], label="predicted"); plt.legend(); plt.tight_layout(); plt.savefig("plots/hybrid_residual_dx.png", dpi=150); plt.close()
    plt.figure(figsize=(9, 5)); plt.plot(test_times, test["residual_dy"], label="actual"); plt.plot(test_times, residual_predictions["residual_dy"], label="predicted"); plt.legend(); plt.tight_layout(); plt.savefig("plots/hybrid_residual_dy.png", dpi=150); plt.close()
    plt.figure(figsize=(7, 5)); plt.bar(["physics-only", "hybrid ML"], [physics_metrics["position_rmse_m"], hybrid_metrics["position_rmse_m"]]); plt.ylabel("Test position RMSE (m)"); plt.tight_layout(); plt.savefig("plots/hybrid_rmse_comparison.png", dpi=150); plt.close()

    max_velocity = float(np.linalg.norm(corrected_velocities, axis=1).max())
    corrected_acceleration = np.diff(corrected_velocities, axis=0) / np.diff(test_times)[:, None]
    max_acceleration = float(np.linalg.norm(corrected_acceleration, axis=1).max()) if len(corrected_acceleration) else 0.0
    max_residual = max(np.hypot(test["residual_dx"], test["residual_dy"]).max(), np.hypot(residual_predictions["residual_dx"], residual_predictions["residual_dy"]).max())
    print("PHYSICS-ONLY TEST RESULT"); print(physics_metrics)
    print("HYBRID ML TEST RESULT"); print(hybrid_metrics)
    print(f"RMSE improvement (%): {rmse_improvement:.6f}"); print(f"FINAL ERROR improvement (%): {final_improvement:.6f}")
    print(f"maximum corrected velocity: {max_velocity:.6f} m/s"); print(f"maximum corrected acceleration: {max_acceleration:.6f} m/s^2"); print(f"maximum residual magnitude: {max_residual:.6f} m")
    print("MODEL INPUTS:"); print(", ".join(names))
    print("TARGETS:\nresidual_dx\nresidual_dy")
    print("REFERENCE/EVALUATION-ONLY DATA:"); print("vehicle latitude, vehicle longitude, pre-outage vehicle speed and heading, reference_x, reference_y")
    print("AUDIT: No future samples, future reference, vehicle speed/heading features, GPS coordinate features, test tuning, or cross-boundary windows were used.")
    print("HYBRID STATUS:", "IMPROVED" if rmse_improvement > 0 else "DID NOT IMPROVE")


if __name__ == "__main__":
    main()