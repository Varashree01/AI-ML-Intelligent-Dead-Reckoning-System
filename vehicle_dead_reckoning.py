import os
import json
import numpy as np
import joblib


# ============================================================
# CONFIGURATION
# ============================================================

DATA_PATH = "data/simulated_run_filtered.npz"
MODEL_PATH = "models/vehicle_speed_model.joblib"
HEADING_PATH = "data/heading_estimation_result.npz"
METRICS_PATH = "models/vehicle_speed_metrics.json"

OUTPUT_PATH = "data/vehicle_dr_result.npz"

WINDOW_SEC = 0.20

# GNSS fusion parameters
GNSS_POSITION_GAIN = 0.70

# Maximum allowed speed for a ground vehicle in this demo
MAX_SPEED = 5.0


# ============================================================
# FEATURE EXTRACTION
# Same 13 features used by vehicle_speed_estimator.py
# ============================================================

def build_features(acc, gyro, t, window_sec=WINDOW_SEC):

    dt = float(np.median(np.diff(t)))
    window_samples = max(5, int(round(window_sec / dt)))

    half = window_samples // 2

    features = []
    feature_times = []

    for i in range(half, len(t) - half):

        a = acc[i - half:i + half + 1]
        g = gyro[i - half:i + half + 1]

        acc_mag = np.linalg.norm(a, axis=1)
        gyro_mag = np.linalg.norm(g, axis=1)

        # Remove slowly varying acceleration baseline
        acc_residual = acc_mag - np.median(acc_mag)

        row = [
            np.mean(acc_residual),
            np.std(acc_residual),
            np.sqrt(np.mean(acc_residual ** 2)),
            np.max(np.abs(acc_residual)),

            np.mean(gyro_mag),
            np.std(gyro_mag),
            np.sqrt(np.mean(gyro_mag ** 2)),

            np.mean(a[:, 0]),
            np.mean(a[:, 1]),
            np.mean(a[:, 2]),

            np.std(a[:, 0]),
            np.std(a[:, 1]),
            np.std(a[:, 2]),
        ]

        features.append(row)
        feature_times.append(t[i])

    return np.asarray(features), np.asarray(feature_times)


# ============================================================
# INTERPOLATE ML SPEED
# ============================================================

def interpolate_predictions(pred_times, predictions, t):

    return np.interp(
        t,
        pred_times,
        predictions,
        left=predictions[0],
        right=predictions[-1]
    )


# ============================================================
# GNSS + DR FUSION
# ============================================================

def run_vehicle_dead_reckoning():

    print("=" * 65)
    print(" Vehicle AI-ML Dead Reckoning V2")
    print("=" * 65)

    # --------------------------------------------------------
    # File checks
    # --------------------------------------------------------

    for path in [
        DATA_PATH,
        MODEL_PATH,
        HEADING_PATH,
        METRICS_PATH
    ]:

        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Required file not found: {path}"
            )

    # --------------------------------------------------------
    # Load dataset
    # --------------------------------------------------------

    print("\nLoading filtered IMU dataset...")

    data = np.load(DATA_PATH)

    t = data["t"]

    gps_pos = data["gps_pos"]
    gps_available = data["gps_available"].astype(bool)

    acc = data["acc_filtered"]
    gyro = data["gyro_filtered"]

    # Ground truth is ONLY used for evaluation
    gt_pos = data["gt_pos"]
    gt_velocity = data["gt_velocity"]

    tunnel_start = float(data["tunnel_start"])
    tunnel_duration = float(data["tunnel_duration"])
    tunnel_end = tunnel_start + tunnel_duration

    print(f"Samples       : {len(t)}")
    print(f"Duration      : {t[-1]:.2f} s")
    print(
        f"GNSS blackout : "
        f"{tunnel_start:.2f} - {tunnel_end:.2f} s"
    )

    # --------------------------------------------------------
    # Load heading
    # --------------------------------------------------------

    print("\nLoading heading estimation result...")

    heading_data = np.load(HEADING_PATH)

    heading = heading_data["fused_heading"]

    if len(heading) != len(t):

        if "t" not in heading_data:
            raise ValueError(
                "Heading length does not match dataset."
            )

        heading = np.interp(
            t,
            heading_data["t"],
            heading
        )

    # Ensure continuous heading
    heading = np.unwrap(heading)

    # --------------------------------------------------------
    # Load ML model
    # --------------------------------------------------------

    print("\nLoading vehicle speed ML model...")

    model = joblib.load(MODEL_PATH)

    # --------------------------------------------------------
    # Build ML features
    # --------------------------------------------------------

    print("\nBuilding IMU features...")

    X, feature_times = build_features(
        acc,
        gyro,
        t
    )

    print(f"Feature samples : {len(X)}")
    print(f"Features/sample : {X.shape[1]}")

    # --------------------------------------------------------
    # Predict vehicle speed
    # --------------------------------------------------------

    print("\nPredicting vehicle speed using AI/ML...")

    predicted_speed_window = model.predict(X)

    predicted_speed_window = np.maximum(
        predicted_speed_window,
        0.0
    )

    predicted_speed_window = np.minimum(
        predicted_speed_window,
        MAX_SPEED
    )

    predicted_speed = interpolate_predictions(
        feature_times,
        predicted_speed_window,
        t
    )

    print(
        f"Predicted speed range : "
        f"{predicted_speed.min():.2f} - "
        f"{predicted_speed.max():.2f} m/s"
    )

    # --------------------------------------------------------
    # Initialize position
    # --------------------------------------------------------

    gps_indices = np.where(gps_available)[0]

    if len(gps_indices) == 0:
        raise RuntimeError(
            "No GNSS measurements found."
        )

    first_gps_index = int(gps_indices[0])

    estimated_pos = np.zeros_like(
        gt_pos,
        dtype=float
    )

    # Start from first available GNSS position
    estimated_pos[0] = gps_pos[first_gps_index]

    # --------------------------------------------------------
    # Variables for diagnostics
    # --------------------------------------------------------

    dr_prediction = np.zeros_like(
        gt_pos,
        dtype=float
    )

    gnss_correction = np.zeros_like(
        gt_pos,
        dtype=float
    )

    navigation_mode = np.zeros(
        len(t),
        dtype=np.int8
    )

    # --------------------------------------------------------
    # Main fusion loop
    # --------------------------------------------------------

    print("\nStarting seamless navigation...")

    last_gps_position = estimated_pos[0]

    for i in range(1, len(t)):

        dt = float(t[i] - t[i - 1])

        if dt <= 0:
            dt = float(np.median(np.diff(t)))

        # ====================================================
        # AI/ML VEHICLE VELOCITY
        # ====================================================

        speed = predicted_speed[i]

        vx = speed * np.cos(heading[i])
        vy = speed * np.sin(heading[i])

        velocity = np.array([
            vx,
            vy
        ])

        # ====================================================
        # DEAD RECKONING PREDICTION
        # ====================================================

        predicted_position = (
            estimated_pos[i - 1]
            + velocity * dt
        )

        dr_prediction[i] = predicted_position

        # ====================================================
        # GNSS AVAILABLE
        # ====================================================

        if gps_available[i]:

            navigation_mode[i] = 1

            measurement = gps_pos[i]

            # Difference between DR and GNSS
            correction = measurement - predicted_position

            gnss_correction[i] = correction

            # Smooth GNSS correction
            estimated_pos[i] = (
                predicted_position
                + GNSS_POSITION_GAIN * correction
            )

            last_gps_position = measurement

        # ====================================================
        # GNSS BLACKOUT
        # ====================================================

        else:

            navigation_mode[i] = 2

            # NO GNSS correction here.
            #
            # Position comes only from:
            # AI/ML speed + heading + IMU
            #
            estimated_pos[i] = predicted_position

    # --------------------------------------------------------
    # Position error
    # --------------------------------------------------------

    position_error = np.linalg.norm(
        estimated_pos - gt_pos,
        axis=1
    )

    # --------------------------------------------------------
    # Blackout mask
    # --------------------------------------------------------

    blackout_mask = (
        (t >= tunnel_start)
        &
        (t < tunnel_end)
    )

    blackout_errors = position_error[
        blackout_mask
    ]

    # --------------------------------------------------------
    # Overall metrics
    # --------------------------------------------------------

    mean_error = float(
        np.mean(position_error)
    )

    rmse_error = float(
        np.sqrt(
            np.mean(position_error ** 2)
        )
    )

    max_error = float(
        np.max(position_error)
    )

    # --------------------------------------------------------
    # Blackout metrics
    # --------------------------------------------------------

    blackout_mean = float(
        np.mean(blackout_errors)
    )

    blackout_rmse = float(
        np.sqrt(
            np.mean(blackout_errors ** 2)
        )
    )

    blackout_max = float(
        np.max(blackout_errors)
    )

    # --------------------------------------------------------
    # Blackout travelled distance
    # --------------------------------------------------------

    blackout_gt = gt_pos[
        blackout_mask
    ]

    if len(blackout_gt) > 1:

        blackout_distance = float(
            np.sum(
                np.linalg.norm(
                    np.diff(
                        blackout_gt,
                        axis=0
                    ),
                    axis=1
                )
            )
        )

    else:

        blackout_distance = 0.0

    # --------------------------------------------------------
    # Drift percentage
    # --------------------------------------------------------

    blackout_drift_percentage = (
        blackout_max
        / blackout_distance
        * 100.0
        if blackout_distance > 0
        else 0.0
    )

    # --------------------------------------------------------
    # Additional drift-from-blackout-start metric
    #
    # This separates accumulated blackout drift from the
    # absolute position error already present at blackout start.
    # --------------------------------------------------------

    blackout_indices = np.where(
        blackout_mask
    )[0]

    blackout_start_error = 0.0
    blackout_end_error = 0.0
    accumulated_blackout_drift = 0.0

    if len(blackout_indices) > 0:

        start_idx = blackout_indices[0]
        end_idx = blackout_indices[-1]

        blackout_start_error = float(
            position_error[start_idx]
        )

        blackout_end_error = float(
            position_error[end_idx]
        )

        accumulated_blackout_drift = (
            blackout_end_error
            - blackout_start_error
        )

    # --------------------------------------------------------
    # Speed evaluation
    # --------------------------------------------------------
    # IMPORTANT:
    # Use the validated held-out metrics generated by
    # vehicle_speed_estimator.py.
    #
    # These metrics come from the 80/20 time-based test split.
    # They are NOT calculated on the same samples used for
    # training the Random Forest model.

    with open(
        METRICS_PATH,
        "r",
        encoding="utf-8"
    ) as f:

        speed_metrics = json.load(f)

    speed_mae = float(
        speed_metrics["mae_mps"]
    )

    speed_rmse = float(
        speed_metrics["rmse_mps"]
    )

    print()
    print("Validated Vehicle Speed Metrics")
    print("---------------------------------")
    print(
        f"Source     : {METRICS_PATH}"
    )
    print(
        f"Evaluation : {speed_metrics['evaluation']}"
    )
    print(
        f"MAE        : {speed_mae:.3f} m/s"
    )
    print(
        f"RMSE       : {speed_rmse:.3f} m/s"
    )

    # --------------------------------------------------------
    # Heading statistics
    # --------------------------------------------------------

    heading_deg = np.rad2deg(
        heading
    )

    # --------------------------------------------------------
    # Results
    # --------------------------------------------------------

    print("\n")
    print("=" * 65)
    print(" Vehicle Dead Reckoning V2 Results")
    print("=" * 65)

    print(
        f"Mean position error     : "
        f"{mean_error:.3f} m"
    )

    print(
        f"RMSE position error     : "
        f"{rmse_error:.3f} m"
    )

    print(
        f"Maximum position error  : "
        f"{max_error:.3f} m"
    )

    print("\nAI/ML Vehicle Speed Estimation")
    print("-" * 45)

    print(
        f"Speed MAE               : "
        f"{speed_mae:.3f} m/s"
    )

    print(
        f"Speed RMSE              : "
        f"{speed_rmse:.3f} m/s"
    )

    print("\nGNSS Blackout Performance")
    print("-" * 45)

    print(
        f"Blackout duration       : "
        f"{tunnel_duration:.2f} s"
    )

    print(
        f"Travelled distance      : "
        f"{blackout_distance:.2f} m"
    )

    print(
        f"Mean blackout error     : "
        f"{blackout_mean:.3f} m"
    )

    print(
        f"RMSE blackout error     : "
        f"{blackout_rmse:.3f} m"
    )

    print(
        f"Maximum blackout error  : "
        f"{blackout_max:.3f} m"
    )

    print(
        f"Blackout drift          : "
        f"{blackout_drift_percentage:.2f}%"
    )

    print(
        f"Error at blackout start : "
        f"{blackout_start_error:.3f} m"
    )

    print(
        f"Error at blackout end   : "
        f"{blackout_end_error:.3f} m"
    )

    print(
        f"Accumulated blackout drift : "
        f"{accumulated_blackout_drift:.3f} m"
    )

    # --------------------------------------------------------
    # Navigation mode summary
    # --------------------------------------------------------

    print("\nNavigation Modes")
    print("-" * 45)

    print(
        "✓ GNSS + AI/ML INS"
    )

    print(
        "✓ GNSS-denied AI/ML Dead Reckoning"
    )

    print(
        "✓ GNSS recovery"
    )

    # --------------------------------------------------------
    # Save complete result
    # --------------------------------------------------------

    np.savez(
        OUTPUT_PATH,

        t=t,

        estimated_pos=estimated_pos,

        dr_prediction=dr_prediction,

        gnss_correction=gnss_correction,

        predicted_speed=predicted_speed,

        heading=heading,

        heading_deg=heading_deg,

        gps_pos=gps_pos,

        gps_available=gps_available,

        navigation_mode=navigation_mode,

        position_error=position_error,

        blackout_mask=blackout_mask,

        gt_pos=gt_pos,

        gt_velocity=gt_velocity,

        speed_mae=speed_mae,

        speed_rmse=speed_rmse,

        mean_position_error=mean_error,

        rmse_position_error=rmse_error,

        max_position_error=max_error,

        blackout_mean_error=blackout_mean,

        blackout_rmse_error=blackout_rmse,

        blackout_max_error=blackout_max,

        blackout_distance=blackout_distance,

        blackout_drift_percentage=blackout_drift_percentage,

        blackout_start_error=blackout_start_error,

        blackout_end_error=blackout_end_error,

        accumulated_blackout_drift=accumulated_blackout_drift,

        tunnel_start=tunnel_start,

        tunnel_duration=tunnel_duration
    )

    print("\nSaved:")
    print(OUTPUT_PATH)

    print("\nGround-truth usage:")
    print("✓ gt_pos      → evaluation only")
    print("✓ gt_velocity → evaluation only")
    print("✓ gt_heading  → NOT used")

    print("\n" + "=" * 65)
    print(" Vehicle Dead Reckoning V2 completed successfully")
    print("=" * 65)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    run_vehicle_dead_reckoning()