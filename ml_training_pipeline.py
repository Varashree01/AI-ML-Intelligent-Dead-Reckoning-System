"""First supervised ML correction baseline for smartphone dead reckoning.

Only smartphone channels are loaded as model features. Vehicle telemetry is
loaded separately and used to create offline reference targets and the single
pre-outage initial state; it is never included in X.
"""

import os
from math import cos, radians, sin

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib


TRAINING_CSV = os.path.join("data", "training_dataset.csv")
VEHICLE_CSV = os.path.join("IO-VNBD-GIT", "Synchronised V abd S datasets", "Uncategorised IOVNB Dataset", "V-Dataset", "V-S1.csv")
OUTPUT_DIR = "data"
MODEL_DIR = "models"
PLOT_DIR = "plots"
WINDOW_SECONDS = 2.0
OUTAGE_START = 60.0
OUTAGE_DURATION = 60.0
EARTH_RADIUS_M = 6378137.0

BASE_FEATURES = [
    "ACCEL_X", "ACCEL_Y", "ACCEL_Z", "GYRO_X", "GYRO_Y", "GYRO_Z",
    "GRAV_X", "GRAV_Y", "GRAV_Z", "MAG_X", "MAG_Y", "MAG_Z",
    "OR_AZ", "OR_P", "OR_R", "accel_mag", "gyro_mag", "time_delta",
]
TARGETS = ["target_dx", "target_dy"]


def numeric(frame, column):
    values = pd.to_numeric(frame[column], errors="coerce")
    values = values.interpolate().bfill().ffill()
    if values.isna().any():
        raise ValueError(f"Column {column} contains no numeric values")
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


def load_smartphone(path):
    required = ["time_s"] + BASE_FEATURES[:15]
    frame = pd.read_csv(path, encoding="cp1252", usecols=required)
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required smartphone columns: {missing}")
    data = {column: numeric(frame, column) for column in required}
    data["accel_mag"] = np.linalg.norm(np.column_stack([data[f"ACCEL_{axis}"] for axis in "XYZ"]), axis=1)
    data["gyro_mag"] = np.linalg.norm(np.column_stack([data[f"GYRO_{axis}"] for axis in "XYZ"]), axis=1)
    data["time_delta"] = np.r_[0.0, np.diff(data["time_s"])]
    time_s = data["time_s"] - data["time_s"][0]
    if np.any(np.diff(time_s) <= 0):
        raise ValueError("time_s must be strictly increasing")
    return data, time_s


def load_reference(path):
    frame = pd.read_csv(path, encoding="cp1252")
    time = numeric(frame, find_column(frame.columns, ["time since start of day", "time since start"])).copy()
    time -= time[0]
    order = np.argsort(time)
    latitude = numeric(frame, find_column(frame.columns, ["latitude"]))[order]
    longitude = numeric(frame, find_column(frame.columns, ["longitude"]))[order]
    heading = numeric(frame, find_column(frame.columns, ["heading"]))[order]
    speed = np.maximum(numeric(frame, find_column(frame.columns, ["indicated vehicle speed", "velocity", "speed"]))[order], 0) / 3.6
    reference_x, reference_y = latlon_to_enu(latitude, longitude, latitude[0], longitude[0])
    return {"time_s": time[order], "x": reference_x, "y": reference_y, "heading": heading, "speed": speed}


def make_imu_baseline(time_s, smartphone, reference, outage_start, outage_duration):
    """Create the uncorrected causal IMU trajectory used to define targets."""
    outage_end = outage_start + outage_duration
    outage = (time_s >= outage_start) & (time_s < outage_end)
    if not outage.any():
        raise ValueError("Configured outage has no samples")
    start = np.flatnonzero(outage)[0]
    end = np.flatnonzero(outage)[-1]
    before = reference["time_s"] < outage_start
    if not before.any():
        raise ValueError("Reference has no pre-outage samples")
    ref_index = np.flatnonzero(before)[-1]
    initial_speed = reference["speed"][ref_index]
    initial_heading = reference["heading"][ref_index]
    initial_x = np.interp(time_s[start], reference["time_s"][:ref_index + 1], reference["x"][:ref_index + 1])
    initial_y = np.interp(time_s[start], reference["time_s"][:ref_index + 1], reference["y"][:ref_index + 1])
    acceleration = np.column_stack([
        smartphone["ACCEL_X"] - smartphone["GRAV_X"],
        smartphone["ACCEL_Y"] - smartphone["GRAV_Y"],
        smartphone["ACCEL_Z"] - smartphone["GRAV_Z"],
    ])
    from scipy.spatial.transform import Rotation
    navigation_acceleration = Rotation.from_euler(
        "ZYX", np.column_stack([smartphone["OR_AZ"], smartphone["OR_P"], smartphone["OR_R"]]), degrees=True
    ).apply(acceleration)
    x = np.full(len(time_s), np.nan)
    y = np.full(len(time_s), np.nan)
    x[start], y[start] = initial_x, initial_y
    velocity = np.array([initial_speed * sin(radians(initial_heading)), initial_speed * cos(radians(initial_heading))])
    for index in range(start + 1, end + 1):
        dt = time_s[index] - time_s[index - 1]
        velocity += navigation_acceleration[index, :2] * dt
        x[index] = x[index - 1] + velocity[0] * dt
        y[index] = y[index - 1] + velocity[1] * dt
    return x, y, outage


def window_features(data, time_s, window_seconds):
    sample_interval = float(np.median(np.diff(time_s)))
    window_size = max(2, int(round(window_seconds / sample_interval)))
    feature_names = []
    for column in BASE_FEATURES:
        feature_names += [f"{column}_{stat}" for stat in ("mean", "std", "min", "max", "range", "rms", "first", "last", "delta")]
    feature_names += ["window_mean_time_delta", "window_accumulated_time"]
    rows = []
    for end in range(len(time_s)):
        start = max(0, end - window_size + 1)
        values = []
        for column in BASE_FEATURES:
            window = data[column][start:end + 1]
            values.extend([np.mean(window), np.std(window), np.min(window), np.max(window),
                           np.max(window) - np.min(window), np.sqrt(np.mean(window ** 2)),
                           window[0], window[-1], window[-1] - window[0]])
        deltas = data["time_delta"][start:end + 1]
        values.extend([np.mean(deltas), np.sum(deltas)])
        rows.append(values)
    return np.asarray(rows), feature_names, window_size


def save_plot(path, x, y, xlabel, ylabel, title):
    plt.figure(figsize=(7, 5))
    plt.scatter(x, y, s=3, alpha=0.25)
    low, high = min(np.min(x), np.min(y)), max(np.max(x), np.max(y))
    plt.plot([low, high], [low, high], "k--", linewidth=1)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


def main():
    smartphone, time_s = load_smartphone(TRAINING_CSV)
    reference = load_reference(VEHICLE_CSV)
    baseline_x, baseline_y, outage = make_imu_baseline(time_s, smartphone, reference, OUTAGE_START, OUTAGE_DURATION)
    reference_x = np.interp(time_s, reference["time_s"], reference["x"])
    reference_y = np.interp(time_s, reference["time_s"], reference["y"])
    valid = np.isfinite(baseline_x) & np.isfinite(baseline_y)
    X, feature_names, window_size = window_features(smartphone, time_s, WINDOW_SECONDS)
    frame = pd.DataFrame(X, columns=feature_names)
    frame["target_dx"] = reference_x - baseline_x
    frame["target_dy"] = reference_y - baseline_y
    frame["time_s"] = time_s
    frame = frame.loc[valid].reset_index(drop=True)

    n = len(frame)
    train_end, validation_end = int(n * 0.70), int(n * 0.85)
    train = frame.iloc[:train_end]
    validation = frame.iloc[train_end:validation_end]
    test = frame.iloc[validation_end:]
    X_train, X_validation, X_test = [part[feature_names] for part in (train, validation, test)]
    y_train = train[TARGETS]
    y_validation = validation[TARGETS]
    y_test = test[TARGETS]

    models = {}
    predictions = {}
    metrics = []
    for target in TARGETS:
        model_name = "model_dx" if target == "target_dx" else "model_dy"
        model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1, min_samples_leaf=2)
        model.fit(X_train, y_train[target])
        pred = model.predict(X_test)
        models[model_name] = model
        predictions[target] = pred
        metrics.append({"target": target, "MAE_m": mean_absolute_error(y_test[target], pred),
                        "RMSE_m": np.sqrt(mean_squared_error(y_test[target], pred)),
                        "R2": r2_score(y_test[target], pred)})

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(MODEL_DIR, exist_ok=True)
    os.makedirs(PLOT_DIR, exist_ok=True)
    frame.to_csv(os.path.join(OUTPUT_DIR, "ml_training_dataset.csv"), index=False)
    train.to_csv(os.path.join(OUTPUT_DIR, "ml_train.csv"), index=False)
    validation.to_csv(os.path.join(OUTPUT_DIR, "ml_validation.csv"), index=False)
    test.to_csv(os.path.join(OUTPUT_DIR, "ml_test.csv"), index=False)
    joblib.dump({"model": models["model_dx"], "features": feature_names, "target": "target_dx"}, os.path.join(MODEL_DIR, "dr_error_model_dx.pkl"))
    joblib.dump({"model": models["model_dy"], "features": feature_names, "target": "target_dy"}, os.path.join(MODEL_DIR, "dr_error_model_dy.pkl"))
    pd.DataFrame(metrics).to_csv(os.path.join(OUTPUT_DIR, "ml_baseline_metrics.csv"), index=False)
    save_plot(os.path.join(PLOT_DIR, "ml_actual_vs_predicted_dx.png"), y_test["target_dx"], predictions["target_dx"], "Actual target_dx (m)", "Predicted target_dx (m)", "ML correction: dx")
    save_plot(os.path.join(PLOT_DIR, "ml_actual_vs_predicted_dy.png"), y_test["target_dy"], predictions["target_dy"], "Actual target_dy (m)", "Predicted target_dy (m)", "ML correction: dy")
    residuals = np.r_[y_test["target_dx"].to_numpy() - predictions["target_dx"], y_test["target_dy"].to_numpy() - predictions["target_dy"]]
    plt.figure(figsize=(7, 4))
    plt.hist(residuals, bins=80)
    plt.xlabel("Prediction residual (m)")
    plt.ylabel("Count")
    plt.title("ML correction residual distribution")
    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "ml_error_distribution.png"), dpi=150)
    plt.close()

    print(f"total samples: {n}")
    print(f"window samples: {window_size} ({WINDOW_SECONDS:.1f} seconds)")
    print(f"number of features: {len(feature_names)}")
    print(f"target columns: {TARGETS}")
    print(f"training samples: {len(train)}")
    print(f"validation samples: {len(validation)}")
    print(f"test samples: {len(test)}")
    print("target statistics:")
    print(frame[TARGETS].describe().loc[["mean", "std", "min", "max"]].to_string())
    print("missing values:")
    print(int(frame[feature_names + TARGETS].isna().sum().sum()))
    print(f"time ranges: train={train.time_s.iloc[0]:.3f}..{train.time_s.iloc[-1]:.3f}, validation={validation.time_s.iloc[0]:.3f}..{validation.time_s.iloc[-1]:.3f}, test={test.time_s.iloc[0]:.3f}..{test.time_s.iloc[-1]:.3f}")
    print(pd.DataFrame(metrics).to_string(index=False))
    print("PREDICTION FEATURES:")
    print(", ".join(feature_names))
    print("TRAINING TARGETS:")
    print("target_dx\ntarget_dy")
    print("EVALUATION-ONLY DATA:")
    print("vehicle latitude, vehicle longitude, vehicle speed, vehicle heading, reference_x, reference_y")
    print("INFORMATION-LEAKAGE AUDIT: vehicle/reference fields are used only for initial-state construction and offline target generation; they are excluded from X.")
    print("This is the first ML correction baseline, not a final navigation model.")


if __name__ == "__main__":
    main()