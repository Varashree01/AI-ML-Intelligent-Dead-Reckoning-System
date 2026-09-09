import os
import json

import numpy as np
import joblib

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error


INPUT_PATH = os.path.join(
    "data",
    "simulated_run_filtered.npz"
)

MODEL_PATH = "models/vehicle_speed_model.joblib"
METRICS_PATH = "models/vehicle_speed_metrics.json"


def build_features(acc, gyro, dt):
    """
    Convert IMU signals into short-window features.

    Features are calculated without using ground-truth speed.
    """

    acc = np.asarray(acc, dtype=float)
    gyro = np.asarray(gyro, dtype=float)

    n = len(acc)

    acc_mag = np.linalg.norm(acc, axis=1)
    gyro_mag = np.linalg.norm(gyro, axis=1)

    # Remove approximate gravity magnitude.
    # This is only a feature-engineering step.
    acc_dynamic = acc_mag - np.median(acc_mag)

    window = max(
        int(round(0.20 / max(dt, 1e-4))),
        3
    )

    features = []

    for i in range(n):

        start = max(
            0,
            i - window + 1
        )

        a = acc_dynamic[start:i + 1]
        g = gyro_mag[start:i + 1]

        ax = acc[start:i + 1, 0]
        ay = acc[start:i + 1, 1]
        az = acc[start:i + 1, 2]

        row = [

            # Acceleration features
            np.mean(a),
            np.std(a),
            np.sqrt(np.mean(a ** 2)),
            np.max(np.abs(a)),

            # Gyroscope features
            np.mean(g),
            np.std(g),
            np.sqrt(np.mean(g ** 2)),

            # Individual acceleration axes
            np.mean(ax),
            np.mean(ay),
            np.mean(az),

            np.std(ax),
            np.std(ay),
            np.std(az),
        ]

        features.append(row)

    return np.asarray(features)


def main():

    if not os.path.exists(INPUT_PATH):
        raise FileNotFoundError(
            f"Filtered dataset not found: {INPUT_PATH}\n"
            "Run imu_disturbance_filter.py first."
        )

    data = dict(
        np.load(
            INPUT_PATH,
            allow_pickle=True
        )
    )

    required = [
        "acc_filtered",
        "gyro_filtered",
        "dt",
        "vehicle_speed"
    ]

    missing = [
        key
        for key in required
        if key not in data
    ]

    if missing:
        raise KeyError(
            f"Missing dataset keys: {missing}"
        )

    acc = np.asarray(
        data["acc_filtered"],
        dtype=float
    )

    gyro = np.asarray(
        data["gyro_filtered"],
        dtype=float
    )

    dt = float(data["dt"])

    speed = np.asarray(
        data["vehicle_speed"],
        dtype=float
    )

    print("==============================================")
    print(" Vehicle Speed Estimation")
    print("==============================================")

    print("Building IMU features...")

    X = build_features(
        acc,
        gyro,
        dt
    )

    y = speed

    print(f"Samples: {len(X)}")
    print(f"Features per sample: {X.shape[1]}")

    # ---------------------------------------------------------
    # Time-based train/test split
    # ---------------------------------------------------------
    # No random shuffle because sensor data is time-series data.

    split = int(
        0.80 * len(X)
    )

    X_train = X[:split]
    y_train = y[:split]

    X_test = X[split:]
    y_test = y[split:]

    print(
        f"Training samples: {len(X_train)}"
    )

    print(
        f"Testing samples : {len(X_test)}"
    )

    # ---------------------------------------------------------
    # Train model
    # ---------------------------------------------------------

    print()
    print("Training Random Forest speed estimator...")

    model = RandomForestRegressor(
        n_estimators=150,
        max_depth=18,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1
    )

    model.fit(
        X_train,
        y_train
    )

    # ---------------------------------------------------------
    # Evaluate on HELD-OUT test set
    # ---------------------------------------------------------

    predicted_speed = model.predict(
        X_test
    )

    mae = mean_absolute_error(
        y_test,
        predicted_speed
    )

    rmse = np.sqrt(
        mean_squared_error(
            y_test,
            predicted_speed
        )
    )

    print()
    print("Vehicle Speed Estimation Results")
    print("---------------------------------")

    print(
        f"MAE  : {mae:.3f} m/s"
    )

    print(
        f"RMSE : {rmse:.3f} m/s"
    )

    # ---------------------------------------------------------
    # Save model
    # ---------------------------------------------------------

    os.makedirs(
        "models",
        exist_ok=True
    )

    joblib.dump(
        model,
        MODEL_PATH
    )

    print()
    print(
        f"Model saved: {MODEL_PATH}"
    )

    # ---------------------------------------------------------
    # Save VALIDATED held-out metrics
    # ---------------------------------------------------------

    metrics = {
        "model": "RandomForestRegressor",
        "evaluation": "held_out_test_set",
        "train_fraction": 0.80,
        "test_fraction": 0.20,
        "mae_mps": float(mae),
        "rmse_mps": float(rmse),
        "training_samples": int(len(X_train)),
        "testing_samples": int(len(X_test)),
        "features_per_sample": int(X.shape[1]),
        "ground_truth_used_for_training_target": True,
        "ground_truth_used_for_inference_features": False
    }

    with open(
        METRICS_PATH,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            metrics,
            f,
            indent=2
        )

    print(
        f"Metrics saved: {METRICS_PATH}"
    )

    # ---------------------------------------------------------
    # Sample predictions
    # ---------------------------------------------------------

    print()
    print("Sample predictions:")
    print(
        "Actual speed -> Predicted speed"
    )

    for actual, pred in zip(
        y_test[:10],
        predicted_speed[:10]
    ):

        print(
            f"{actual:.2f} m/s -> "
            f"{pred:.2f} m/s"
        )

    print()

    print(
        "Ground-truth speed was used only "
        "as the training/evaluation target."
    )

    print(
        "Inference features do not contain "
        "vehicle_speed."
    )

    print()
    print("==============================================")
    print(" Held-out metrics saved successfully")
    print("==============================================")


if __name__ == "__main__":
    main()