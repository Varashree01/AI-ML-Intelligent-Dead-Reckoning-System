"""Causal hybrid physics plus ML velocity-residual dead reckoning."""

import os
from math import cos, radians, sin

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import joblib
import numpy as np
import pandas as pd

from scipy.spatial.transform import Rotation
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


# ============================================================
# PATHS AND CONFIGURATION
# ============================================================

DATA_DIR = "data"
MODEL_DIR = "models"
PLOT_DIR = "plots"

TRAINING_CSV = os.path.join(
    DATA_DIR,
    "training_dataset.csv"
)

VEHICLE_CSV = os.path.join(
    "IO-VNBD-GIT",
    "Synchronised V abd S datasets",
    "Uncategorised IOVNB Dataset",
    "V-Dataset",
    "V-S1.csv"
)

WINDOW_SIZE = 20

# GNSS outage interval used for evaluation
OUTAGE_START = 60.0
OUTAGE_END = 120.0

EARTH_RADIUS_M = 6378137.0


# Smartphone sensor channels
CHANNELS = [
    "ACCEL_X",
    "ACCEL_Y",
    "ACCEL_Z",
    "GYRO_X",
    "GYRO_Y",
    "GYRO_Z",
    "GRAV_X",
    "GRAV_Y",
    "GRAV_Z",
    "MAG_X",
    "MAG_Y",
    "MAG_Z",
    "OR_AZ",
    "OR_P",
    "OR_R",
    "accel_mag",
    "gyro_mag",
    "time_delta",
]


# ML targets
TARGETS = [
    "velocity_residual_x",
    "velocity_residual_y",
]


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def numeric(frame, column):
    """
    Convert a dataframe column to numeric values.

    Missing/non-numeric values are interpolated and then
    forward/backward filled.
    """

    values = (
        pd.to_numeric(frame[column], errors="coerce")
        .interpolate()
        .bfill()
        .ffill()
    )

    if values.isna().any():
        raise ValueError(
            f"No usable numeric values in column: {column}"
        )

    return values.to_numpy(dtype=float)


def find_column(columns, keywords):
    """
    Find the first column whose name contains one of the
    requested keywords.
    """

    for keyword in keywords:
        for column in columns:
            if keyword.lower() in str(column).lower():
                return column

    raise ValueError(
        f"Missing column matching {keywords}"
    )


def latlon_to_enu(
    latitude,
    longitude,
    latitude0,
    longitude0
):
    """
    Convert latitude/longitude to a local East-North coordinate
    system in metres.
    """

    east = (
        np.deg2rad(longitude - longitude0)
        * cos(radians(latitude0))
        * EARTH_RADIUS_M
    )

    north = (
        np.deg2rad(latitude - latitude0)
        * EARTH_RADIUS_M
    )

    return east, north


# ============================================================
# DATA LOADING
# ============================================================

def load_data():
    """
    Load smartphone IMU data and the corresponding vehicle
    reference data from the IO-VNBD dataset.
    """

    required = ["time_s"] + CHANNELS[:15]

    if not os.path.exists(TRAINING_CSV):
        raise FileNotFoundError(
            f"Smartphone training dataset not found:\n{TRAINING_CSV}"
        )

    if not os.path.exists(VEHICLE_CSV):
        raise FileNotFoundError(
            f"Vehicle dataset not found:\n{VEHICLE_CSV}"
        )

    # --------------------------------------------------------
    # Smartphone data
    # --------------------------------------------------------

    frame = pd.read_csv(
        TRAINING_CSV,
        encoding="cp1252",
        usecols=required
    )

    missing = [
        column
        for column in required
        if column not in frame.columns
    ]

    if missing:
        raise ValueError(
            f"Missing smartphone columns: {missing}"
        )

    phone = {
        column: numeric(frame, column)
        for column in required
    }

    # Acceleration magnitude
    phone["accel_mag"] = np.linalg.norm(
        np.column_stack(
            [
                phone["ACCEL_X"],
                phone["ACCEL_Y"],
                phone["ACCEL_Z"],
            ]
        ),
        axis=1
    )

    # Gyroscope magnitude
    phone["gyro_mag"] = np.linalg.norm(
        np.column_stack(
            [
                phone["GYRO_X"],
                phone["GYRO_Y"],
                phone["GYRO_Z"],
            ]
        ),
        axis=1
    )

    # Time difference
    phone["time_delta"] = np.r_[
        0.0,
        np.diff(phone["time_s"])
    ]

    # Normalize time to start from zero
    time_s = phone["time_s"] - phone["time_s"][0]

    if np.any(np.diff(time_s) <= 0):
        raise ValueError(
            "Smartphone time_s must be strictly increasing."
        )

    # --------------------------------------------------------
    # Vehicle reference data
    # --------------------------------------------------------

    vehicle_frame = pd.read_csv(
        VEHICLE_CSV,
        encoding="cp1252"
    )

    time_col = find_column(
        vehicle_frame.columns,
        [
            "time since start of day",
            "time since start"
        ]
    )

    lat_col = find_column(
        vehicle_frame.columns,
        ["latitude"]
    )

    lon_col = find_column(
        vehicle_frame.columns,
        ["longitude"]
    )

    heading_col = find_column(
        vehicle_frame.columns,
        ["heading"]
    )

    speed_col = find_column(
        vehicle_frame.columns,
        [
            "indicated vehicle speed",
            "velocity",
            "speed"
        ]
    )

    vehicle_time = numeric(
        vehicle_frame,
        time_col
    ).copy()

    vehicle_time -= vehicle_time[0]

    order = np.argsort(vehicle_time)

    latitude = numeric(
        vehicle_frame,
        lat_col
    )[order]

    longitude = numeric(
        vehicle_frame,
        lon_col
    )[order]

    heading = numeric(
        vehicle_frame,
        heading_col
    )[order]

    # Dataset speed assumed to be km/h.
    # Convert to m/s.
    speed = (
        np.maximum(
            numeric(vehicle_frame, speed_col)[order],
            0.0
        )
        / 3.6
    )

    reference_x, reference_y = latlon_to_enu(
        latitude,
        longitude,
        latitude[0],
        longitude[0]
    )

    reference = {
        "time_s": vehicle_time[order],
        "x": reference_x,
        "y": reference_y,
        "heading": heading,
        "speed": speed,
    }

    return phone, time_s, reference


# ============================================================
# PHYSICS BASELINE
# ============================================================

def make_physics(phone, time_s, reference):
    """
    Physics-only inertial navigation baseline.

    Smartphone acceleration is transformed into navigation
    coordinates and integrated to estimate velocity and position.
    """

    outage = (
        (time_s >= OUTAGE_START)
        & (time_s < OUTAGE_END)
    )

    outage_indices = np.flatnonzero(outage)

    if len(outage_indices) < WINDOW_SIZE:
        raise ValueError(
            "Outage contains fewer than WINDOW_SIZE samples."
        )

    start = outage_indices[0]
    end = outage_indices[-1]

    # --------------------------------------------------------
    # Initial state at GNSS outage boundary
    # --------------------------------------------------------

    pre = reference["time_s"] < OUTAGE_START

    if not np.any(pre):
        raise ValueError(
            "No reference samples available before GNSS outage."
        )

    reference_index = np.flatnonzero(pre)[-1]

    initial_speed = reference["speed"][reference_index]
    initial_heading = reference["heading"][reference_index]

    initial_x = np.interp(
        time_s[start],
        reference["time_s"][:reference_index + 1],
        reference["x"][:reference_index + 1]
    )

    initial_y = np.interp(
        time_s[start],
        reference["time_s"][:reference_index + 1],
        reference["y"][:reference_index + 1]
    )

    # --------------------------------------------------------
    # Remove gravity
    # --------------------------------------------------------

    body_acceleration = np.column_stack(
        [
            phone["ACCEL_X"] - phone["GRAV_X"],
            phone["ACCEL_Y"] - phone["GRAV_Y"],
            phone["ACCEL_Z"] - phone["GRAV_Z"],
        ]
    )

    # --------------------------------------------------------
    # Body -> navigation frame transformation
    # --------------------------------------------------------

    navigation_acceleration = Rotation.from_euler(
        "ZYX",
        np.column_stack(
            [
                phone["OR_AZ"],
                phone["OR_P"],
                phone["OR_R"],
            ]
        ),
        degrees=True
    ).apply(body_acceleration)

    # --------------------------------------------------------
    # Initialize arrays
    # --------------------------------------------------------

    x = np.full(
        len(time_s),
        np.nan
    )

    y = np.full(
        len(time_s),
        np.nan
    )

    velocity = np.full(
        (len(time_s), 2),
        np.nan
    )

    x[start] = initial_x
    y[start] = initial_y

    # Heading convention:
    # X = East
    # Y = North
    velocity[start] = [
        initial_speed * sin(radians(initial_heading)),
        initial_speed * cos(radians(initial_heading)),
    ]

    # --------------------------------------------------------
    # Integrate acceleration
    # --------------------------------------------------------

    for index in range(
        start + 1,
        end + 1
    ):

        dt = (
            time_s[index]
            - time_s[index - 1]
        )

        velocity[index] = (
            velocity[index - 1]
            + navigation_acceleration[index, :2] * dt
        )

        x[index] = (
            x[index - 1]
            + velocity[index, 0] * dt
        )

        y[index] = (
            y[index - 1]
            + velocity[index, 1] * dt
        )

    return (
        x,
        y,
        velocity,
        navigation_acceleration[:, :2],
        outage
    )


# ============================================================
# FEATURE ENGINEERING
# ============================================================

def names():
    """
    Generate feature names for each sensor channel.
    """

    output = []

    statistics = (
        "mean",
        "std",
        "min",
        "max",
        "range",
        "rms",
        "first",
        "last",
        "delta",
    )

    for channel in CHANNELS:
        output.extend(
            [
                f"{channel}_{stat}"
                for stat in statistics
            ]
        )

    output.extend(
        [
            "window_duration",
            "current_time_s",
            "physics_velocity_x",
            "physics_velocity_y",
            "previous_physics_velocity_x",
            "previous_physics_velocity_y",
            "physics_acceleration_x",
            "physics_acceleration_y",
            "previous_yaw_estimate",
        ]
    )

    return output


def window_row(
    phone,
    time_s,
    velocity,
    acceleration,
    start,
    end
):
    """
    Create causal features from the current and previous
    smartphone sensor samples.
    """

    values = []

    for channel in CHANNELS:

        window = phone[channel][
            start:end + 1
        ]

        values.extend(
            [
                np.mean(window),
                np.std(window),
                np.min(window),
                np.max(window),
                np.ptp(window),
                np.sqrt(
                    np.mean(window ** 2)
                ),
                window[0],
                window[-1],
                window[-1] - window[0],
            ]
        )

    previous_velocity = velocity[end - 1]
    current_velocity = velocity[end]

    current_acceleration = acceleration[end]

    previous_yaw = (
        np.degrees(
            np.arctan2(
                previous_velocity[0],
                previous_velocity[1]
            )
        )
        % 360.0
    )

    window_duration = np.sum(
        phone["time_delta"][
            start:end + 1
        ]
    )

    return values + [
        window_duration,
        time_s[end],

        current_velocity[0],
        current_velocity[1],

        previous_velocity[0],
        previous_velocity[1],

        current_acceleration[0],
        current_acceleration[1],

        previous_yaw,
    ]


# ============================================================
# DATASET SPLITTING
# ============================================================

def make_split(
    phone,
    time_s,
    velocity,
    acceleration,
    reference_x,
    reference_y,
    reference_vx,
    reference_vy,
    physics_x,
    physics_y,
    start,
    end
):
    """
    Create a train/validation/test dataframe.

    The feature window only uses current/past samples.
    """

    rows = []

    for index in range(
        start + 1,
        end + 1
    ):

        window_start = max(
            start,
            index - WINDOW_SIZE + 1
        )

        physics_vx = velocity[index, 0]
        physics_vy = velocity[index, 1]

        rows.append(
            window_row(
                phone,
                time_s,
                velocity,
                acceleration,
                window_start,
                index
            )
            + [
                reference_vx[index] - physics_vx,
                reference_vy[index] - physics_vy,

                physics_vx,
                physics_vy,

                reference_vx[index],
                reference_vy[index],

                physics_x[index]
                - physics_x[index - 1],

                physics_y[index]
                - physics_y[index - 1],

                time_s[index],
            ]
        )

    columns = (
        names()
        + TARGETS
        + [
            "physics_vx",
            "physics_vy",
            "reference_vx",
            "reference_vy",
            "physics_delta_x",
            "physics_delta_y",
            "time_s",
        ]
    )

    return pd.DataFrame(
        rows,
        columns=columns
    )


# ============================================================
# MODEL SELECTION
# ============================================================

def choose_model(
    X_train,
    y_train,
    X_validation,
    y_validation
):
    """
    Select the Random Forest configuration using only the
    validation set.
    """

    best = None
    best_score = float("inf")

    configurations = [
        (50, 1),
        (100, 1),
        (100, 2),
    ]

    for trees, leaf in configurations:

        model = RandomForestRegressor(
            n_estimators=trees,
            min_samples_leaf=leaf,
            random_state=42,
            n_jobs=-1
        )

        model.fit(
            X_train,
            y_train
        )

        prediction = model.predict(
            X_validation
        )

        score = np.sqrt(
            mean_squared_error(
                y_validation,
                prediction
            )
        )

        if score < best_score:
            best = model
            best_score = score

    return best, best_score


# ============================================================
# TRAJECTORY METRICS
# ============================================================

def trajectory_metrics(
    x,
    y,
    ref_x,
    ref_y,
    time_s
):
    """
    Calculate position error metrics.
    """

    error = np.hypot(
        x - ref_x,
        y - ref_y
    )

    duration = (
        time_s[-1]
        - time_s[0]
    )

    if duration <= 0:
        drift_rate = float("nan")
    else:
        drift_rate = (
            error[-1]
            / duration
        )

    return {
        "position_mae_m": float(
            np.mean(error)
        ),
        "position_rmse_m": float(
            np.sqrt(
                np.mean(error ** 2)
            )
        ),
        "final_position_error_m": float(
            error[-1]
        ),
        "maximum_position_error_m": float(
            np.max(error)
        ),
        "drift_rate_mps": float(
            drift_rate
        ),
    }


# ============================================================
# PREVIOUS HYBRID MODEL
# ============================================================

def load_previous_hybrid(
    initial_x,
    initial_y
):
    """
    Load the older position-residual hybrid model if available.

    This is only used for comparison.
    """

    try:

        previous_test = pd.read_csv(
            os.path.join(
                DATA_DIR,
                "hybrid_residual_test.csv"
            )
        )

        dx_obj = joblib.load(
            os.path.join(
                MODEL_DIR,
                "hybrid_residual_dx.pkl"
            )
        )

        dy_obj = joblib.load(
            os.path.join(
                MODEL_DIR,
                "hybrid_residual_dy.pkl"
            )
        )

        dx = dx_obj["model"].predict(
            previous_test[
                dx_obj["features"]
            ]
        )

        dy = dy_obj["model"].predict(
            previous_test[
                dy_obj["features"]
            ]
        )

        x = [float(initial_x)]
        y = [float(initial_y)]

        for row, add_x, add_y in zip(
            previous_test.itertuples(
                index=False
            ),
            dx,
            dy
        ):

            x.append(
                x[-1]
                + row.physics_delta_x
                + add_x
            )

            y.append(
                y[-1]
                + row.physics_delta_y
                + add_y
            )

        return (
            np.asarray(x[1:]),
            np.asarray(y[1:])
        )

    except (
        FileNotFoundError,
        KeyError,
        ValueError
    ) as error:

        print(
            "Previous hybrid comparison unavailable:",
            error
        )

        return None


# ============================================================
# MAIN PIPELINE
# ============================================================

def main():

    print("=" * 70)
    print("HYBRID PHYSICS + ML VELOCITY RESIDUAL PIPELINE")
    print("=" * 70)

    # --------------------------------------------------------
    # Load data
    # --------------------------------------------------------

    print("\nLoading smartphone and vehicle data...")

    phone, time_s, reference = load_data()

    print(
        f"Smartphone samples: {len(time_s)}"
    )

    print(
        f"Time range: {time_s[0]:.2f}s - {time_s[-1]:.2f}s"
    )

    # --------------------------------------------------------
    # Physics baseline
    # --------------------------------------------------------

    print("\nRunning physics baseline...")

    (
        physics_x,
        physics_y,
        velocity,
        acceleration,
        outage
    ) = make_physics(
        phone,
        time_s,
        reference
    )

    # --------------------------------------------------------
    # Reference interpolation
    # --------------------------------------------------------

    reference_x = np.interp(
        time_s,
        reference["time_s"],
        reference["x"]
    )

    reference_y = np.interp(
        time_s,
        reference["time_s"],
        reference["y"]
    )

    reference_heading = np.deg2rad(
        np.interp(
            time_s,
            reference["time_s"],
            reference["heading"]
        )
    )

    reference_speed = np.interp(
        time_s,
        reference["time_s"],
        reference["speed"]
    )

    reference_vx = (
        reference_speed
        * np.sin(reference_heading)
    )

    reference_vy = (
        reference_speed
        * np.cos(reference_heading)
    )

    # --------------------------------------------------------
    # Outage split
    # --------------------------------------------------------

    indices = np.flatnonzero(outage)

    start = indices[0]
    end = indices[-1]

    train_end = (
        start
        + int(len(indices) * 0.70)
    )

    validation_end = (
        start
        + int(len(indices) * 0.85)
    )

    print(
        f"\nGNSS outage: "
        f"{time_s[start]:.2f}s - "
        f"{time_s[end]:.2f}s"
    )

    print(
        f"Train boundary: {time_s[train_end]:.2f}s"
    )

    print(
        f"Validation boundary: "
        f"{time_s[validation_end]:.2f}s"
    )

    # --------------------------------------------------------
    # Create datasets
    # --------------------------------------------------------

    print("\nCreating causal ML datasets...")

    splits = {

        "train": make_split(
            phone,
            time_s,
            velocity,
            acceleration,
            reference_x,
            reference_y,
            reference_vx,
            reference_vy,
            physics_x,
            physics_y,
            start,
            train_end - 1
        ),

        "validation": make_split(
            phone,
            time_s,
            velocity,
            acceleration,
            reference_x,
            reference_y,
            reference_vx,
            reference_vy,
            physics_x,
            physics_y,
            train_end,
            validation_end - 1
        ),

        "test": make_split(
            phone,
            time_s,
            velocity,
            acceleration,
            reference_x,
            reference_y,
            reference_vx,
            reference_vy,
            physics_x,
            physics_y,
            validation_end,
            end
        ),
    }

    print(
        f"Training samples: {len(splits['train'])}"
    )

    print(
        f"Validation samples: {len(splits['validation'])}"
    )

    print(
        f"Test samples: {len(splits['test'])}"
    )

    # --------------------------------------------------------
    # Train ML models
    # --------------------------------------------------------

    feature_list = names()

    models = {}
    predictions = {}
    metric_rows = []

    print("\nTraining velocity-residual models...")

    for target, key in zip(
        TARGETS,
        [
            "velocity_residual_model_x",
            "velocity_residual_model_y",
        ]
    ):

        model, validation_rmse = choose_model(
            splits["train"][feature_list],
            splits["train"][target],
            splits["validation"][feature_list],
            splits["validation"][target]
        )

        models[key] = model

        predictions[target] = model.predict(
            splits["test"][feature_list]
        )

        test_target = splits["test"][target]

        metric_rows.extend(
            [
                {
                    "group": "velocity_residual",
                    "metric": target + "_MAE",
                    "value": mean_absolute_error(
                        test_target,
                        predictions[target]
                    ),
                },

                {
                    "group": "velocity_residual",
                    "metric": target + "_RMSE",
                    "value": np.sqrt(
                        mean_squared_error(
                            test_target,
                            predictions[target]
                        )
                    ),
                },

                {
                    "group": "velocity_residual",
                    "metric": target + "_R2",
                    "value": r2_score(
                        test_target,
                        predictions[target]
                    ),
                },
            ]
        )

        print(
            f"Selected {key}: "
            f"validation RMSE="
            f"{validation_rmse:.6f}"
        )

    # --------------------------------------------------------
    # Test trajectory
    # --------------------------------------------------------

    test = splits["test"]

    test_times = test[
        "time_s"
    ].to_numpy()

    physics_test_x = physics_x[
        validation_end + 1:end + 1
    ]

    physics_test_y = physics_y[
        validation_end + 1:end + 1
    ]

    ref_test_x = reference_x[
        validation_end + 1:end + 1
    ]

    ref_test_y = reference_y[
        validation_end + 1:end + 1
    ]

    # --------------------------------------------------------
    # Hybrid velocity integration
    # --------------------------------------------------------

    hybrid_x = []
    hybrid_y = []

    current_x = physics_x[
        validation_end
    ]

    current_y = physics_y[
        validation_end
    ]

    previous_time = time_s[
        validation_end
    ]

    for row, dx, dy in zip(
        test.itertuples(index=False),
        predictions[TARGETS[0]],
        predictions[TARGETS[1]]
    ):

        dt = (
            row.time_s
            - previous_time
        )

        dt = max(
            float(dt),
            1e-6
        )

        current_x += (
            row.physics_delta_x
            + dx * dt
        )

        current_y += (
            row.physics_delta_y
            + dy * dt
        )

        hybrid_x.append(current_x)
        hybrid_y.append(current_y)

        previous_time = row.time_s

    hybrid_x = np.asarray(
        hybrid_x,
        dtype=float
    )

    hybrid_y = np.asarray(
        hybrid_y,
        dtype=float
    )

    # --------------------------------------------------------
    # Metrics
    # --------------------------------------------------------

    physics_metrics = trajectory_metrics(
        physics_test_x,
        physics_test_y,
        ref_test_x,
        ref_test_y,
        test_times
    )

    hybrid_metrics = trajectory_metrics(
        hybrid_x,
        hybrid_y,
        ref_test_x,
        ref_test_y,
        test_times
    )

    previous = load_previous_hybrid(
        physics_x[validation_end],
        physics_y[validation_end]
    )

    if previous is not None:

        previous_metrics = trajectory_metrics(
            previous[0],
            previous[1],
            ref_test_x,
            ref_test_y,
            test_times
        )

    else:

        previous_metrics = {
            key: float("nan")
            for key in physics_metrics
        }

    # --------------------------------------------------------
    # Comparison metrics
    # --------------------------------------------------------

    for group, values in [
        (
            "physics_only",
            physics_metrics
        ),
        (
            "hybrid_velocity",
            hybrid_metrics
        ),
        (
            "hybrid_position_previous",
            previous_metrics
        ),
    ]:

        for key, value in values.items():

            metric_rows.append(
                {
                    "group": group,
                    "metric": key,
                    "value": value,
                }
            )

    physics_rmse = physics_metrics[
        "position_rmse_m"
    ]

    hybrid_rmse = hybrid_metrics[
        "position_rmse_m"
    ]

    if physics_rmse > 0:

        rmse_improvement = (
            100
            * (physics_rmse - hybrid_rmse)
            / physics_rmse
        )

    else:

        rmse_improvement = float("nan")

    previous_rmse = previous_metrics[
        "position_rmse_m"
    ]

    if np.isfinite(previous_rmse) and previous_rmse > 0:

        previous_improvement = (
            100
            * (previous_rmse - hybrid_rmse)
            / previous_rmse
        )

    else:

        previous_improvement = float("nan")

    metric_rows.extend(
        [
            {
                "group": "comparison",
                "metric":
                    "rmse_improvement_over_physics_percent",
                "value": rmse_improvement,
            },

            {
                "group": "comparison",
                "metric":
                    "rmse_improvement_over_previous_percent",
                "value": previous_improvement,
            },
        ]
    )

    # --------------------------------------------------------
    # Save outputs
    # --------------------------------------------------------

    os.makedirs(
        MODEL_DIR,
        exist_ok=True
    )

    os.makedirs(
        DATA_DIR,
        exist_ok=True
    )

    os.makedirs(
        PLOT_DIR,
        exist_ok=True
    )

    for name, frame in splits.items():

        frame.to_csv(
            os.path.join(
                DATA_DIR,
                f"hybrid_velocity_{name}.csv"
            ),
            index=False
        )

    joblib.dump(
        {
            "model":
                models["velocity_residual_model_x"],
            "features":
                feature_list,
            "target":
                TARGETS[0],
        },
        os.path.join(
            MODEL_DIR,
            "hybrid_velocity_residual_x.pkl"
        )
    )

    joblib.dump(
        {
            "model":
                models["velocity_residual_model_y"],
            "features":
                feature_list,
            "target":
                TARGETS[1],
        },
        os.path.join(
            MODEL_DIR,
            "hybrid_velocity_residual_y.pkl"
        )
    )

    pd.DataFrame(
        metric_rows
    ).to_csv(
        os.path.join(
            DATA_DIR,
            "hybrid_velocity_metrics.csv"
        ),
        index=False
    )

    # --------------------------------------------------------
    # Plot 1: trajectory comparison
    # --------------------------------------------------------

    plt.figure(
        figsize=(9, 5)
    )

    plt.plot(
        test_times,
        ref_test_x,
        label="reference x"
    )

    plt.plot(
        test_times,
        physics_test_x,
        label="physics x"
    )

    plt.plot(
        test_times,
        hybrid_x,
        label="hybrid velocity x"
    )

    plt.xlabel("Time (s)")
    plt.ylabel("X Position (m)")
    plt.title(
        "Physics vs Hybrid Velocity Residual"
    )

    plt.legend()
    plt.tight_layout()

    plt.savefig(
        os.path.join(
            PLOT_DIR,
            "hybrid_velocity_trajectory_comparison.png"
        ),
        dpi=150
    )

    plt.close()

    # --------------------------------------------------------
    # Plot 2: error comparison
    # --------------------------------------------------------

    plt.figure(
        figsize=(9, 5)
    )

    plt.plot(
        test_times,
        np.hypot(
            physics_test_x - ref_test_x,
            physics_test_y - ref_test_y
        ),
        label="physics-only"
    )

    plt.plot(
        test_times,
        np.hypot(
            hybrid_x - ref_test_x,
            hybrid_y - ref_test_y
        ),
        label="hybrid velocity"
    )

    plt.xlabel("Time (s)")
    plt.ylabel("Position Error (m)")
    plt.title(
        "Position Error Comparison"
    )

    plt.legend()
    plt.tight_layout()

    plt.savefig(
        os.path.join(
            PLOT_DIR,
            "hybrid_velocity_error_comparison.png"
        ),
        dpi=150
    )

    plt.close()

    # --------------------------------------------------------
    # Plot 3: X velocity residual
    # --------------------------------------------------------

    plt.figure(
        figsize=(9, 5)
    )

    plt.plot(
        test_times,
        test[TARGETS[0]],
        label="actual"
    )

    plt.plot(
        test_times,
        predictions[TARGETS[0]],
        label="predicted"
    )

    plt.xlabel("Time (s)")
    plt.ylabel("Velocity Residual X (m/s)")
    plt.title(
        "X Velocity Residual Prediction"
    )

    plt.legend()
    plt.tight_layout()

    plt.savefig(
        os.path.join(
            PLOT_DIR,
            "hybrid_velocity_residual_x.png"
        ),
        dpi=150
    )

    plt.close()

    # --------------------------------------------------------
    # Plot 4: Y velocity residual
    # --------------------------------------------------------

    plt.figure(
        figsize=(9, 5)
    )

    plt.plot(
        test_times,
        test[TARGETS[1]],
        label="actual"
    )

    plt.plot(
        test_times,
        predictions[TARGETS[1]],
        label="predicted"
    )

    plt.xlabel("Time (s)")
    plt.ylabel("Velocity Residual Y (m/s)")
    plt.title(
        "Y Velocity Residual Prediction"
    )

    plt.legend()
    plt.tight_layout()

    plt.savefig(
        os.path.join(
            PLOT_DIR,
            "hybrid_velocity_residual_y.png"
        ),
        dpi=150
    )

    plt.close()

    # --------------------------------------------------------
    # Plot 5: model comparison
    # --------------------------------------------------------

    plt.figure(
        figsize=(8, 5)
    )

    plt.bar(
        [
            "Physics only",
            "Previous hybrid",
            "Velocity hybrid",
        ],
        [
            physics_metrics[
                "position_rmse_m"
            ],
            previous_metrics[
                "position_rmse_m"
            ],
            hybrid_metrics[
                "position_rmse_m"
            ],
        ]
    )

    plt.ylabel(
        "Test Position RMSE (m)"
    )

    plt.title(
        "Hybrid Model Comparison"
    )

    plt.tight_layout()

    plt.savefig(
        os.path.join(
            PLOT_DIR,
            "hybrid_model_comparison.png"
        ),
        dpi=150
    )

    plt.close()

    # --------------------------------------------------------
    # Numerical sanity checks
    # --------------------------------------------------------

    corrected_velocity = np.column_stack(
        [
            test["physics_vx"].to_numpy()
            + predictions[TARGETS[0]],

            test["physics_vy"].to_numpy()
            + predictions[TARGETS[1]],
        ]
    )

    if len(test_times) > 1:

        corrected_acceleration = (
            np.diff(
                corrected_velocity,
                axis=0
            )
            / np.diff(
                test_times
            )[:, None]
        )

        acceleration_magnitude = np.linalg.norm(
            corrected_acceleration,
            axis=1
        )

        max_corrected_acceleration = (
            float(
                np.max(
                    acceleration_magnitude
                )
            )
        )

    else:

        max_corrected_acceleration = 0.0

    max_corrected_velocity = float(
        np.max(
            np.linalg.norm(
                corrected_velocity,
                axis=1
            )
        )
    )

    max_residual = float(
        np.max(
            np.hypot(
                predictions[TARGETS[0]],
                predictions[TARGETS[1]]
            )
        )
    )

    dt_test = np.diff(
        np.r_[
            time_s[validation_end],
            test_times
        ]
    )

    max_increment = float(
        np.max(
            np.hypot(
                test["physics_delta_x"].to_numpy()
                + predictions[TARGETS[0]]
                * dt_test,

                test["physics_delta_y"].to_numpy()
                + predictions[TARGETS[1]]
                * dt_test
            )
        )
    )

    finite = (
        np.isfinite(hybrid_x).all()
        and np.isfinite(hybrid_y).all()
        and np.isfinite(corrected_velocity).all()
    )

    # --------------------------------------------------------
    # Final report
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)

    print("\nPHYSICS ONLY")
    print(physics_metrics)

    print("\nPREVIOUS HYBRID POSITION RESIDUAL")
    print(previous_metrics)

    print("\nCURRENT HYBRID VELOCITY RESIDUAL")
    print(hybrid_metrics)

    print(
        f"\nRMSE improvement over physics (%): "
        f"{rmse_improvement:.6f}"
    )

    if np.isfinite(previous_improvement):

        print(
            f"RMSE improvement over previous hybrid (%): "
            f"{previous_improvement:.6f}"
        )

    print(
        f"\nMaximum corrected velocity: "
        f"{max_corrected_velocity:.6f} m/s"
    )

    print(
        f"Maximum corrected acceleration: "
        f"{max_corrected_acceleration:.6f} m/s^2"
    )

    print(
        f"Maximum velocity residual: "
        f"{max_residual:.6f} m/s"
    )

    print(
        f"Maximum position increment: "
        f"{max_increment:.6f} m"
    )

    print(
        f"NaN/Inf values: "
        f"{'FAIL' if not finite else 'PASS'}"
    )

    if finite:

        print(
            "Numerical explosion: PASS "
            "(all calculated values are finite)"
        )

    else:

        print(
            "Numerical explosion: FAIL"
        )

    print("\nMODEL INPUT FEATURES:")
    print(
        ", ".join(feature_list)
    )

    print("\nTRAINING TARGETS:")
    print(
        "velocity_residual_x"
    )
    print(
        "velocity_residual_y"
    )

    print(
        "\nREFERENCE / EVALUATION VARIABLES:"
    )

    print(
        "vehicle latitude, vehicle longitude, "
        "vehicle speed, vehicle heading, "
        "reference_x, reference_y, "
        "reference_vx, reference_vy"
    )

    print(
        "\nAUDIT:"
    )

    print(
        "Feature windows use only current and past "
        "smartphone sensor samples."
    )

    print(
        "Reference vehicle measurements are used "
        "for training targets and evaluation."
    )

    print(
        "No future IMU samples are used."
    )

    print(
        "No future reference samples are used "
        "as model input features."
    )

    print(
        "No test-set tuning is performed."
    )

    print(
        "Train, validation and test periods are "
        "kept sequential."
    )

    if (
        previous is not None
        and hybrid_metrics["position_rmse_m"]
        < previous_metrics["position_rmse_m"]
    ):

        print(
            "\nVELOCITY-RESIDUAL RESULT: "
            "BETTER THAN PREVIOUS HYBRID"
        )

    else:

        print(
            "\nVELOCITY-RESIDUAL RESULT: "
            "NOT BETTER THAN PREVIOUS HYBRID"
        )

    print("\n" + "=" * 70)
    print("Pipeline completed successfully.")
    print("=" * 70)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()