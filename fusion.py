"""
fusion.py

GNSS + AI/ML Dead Reckoning Fusion Engine

Modes:
    1. GNSS + INS Fusion
    2. GNSS LOST -> AI/ML Dead Reckoning
    3. GNSS RESTORED -> GNSS + INS Fusion

The ML model predicts step length.

The predicted step length + heading are converted into velocity
and used by the Kalman filter during GNSS outages.
"""

import os
from typing import Optional

import joblib
import numpy as np

import dead_reckoning
import ml_step_length


# ============================================================
# KALMAN FILTER
# ============================================================

class KalmanFilter:
    """
    Simple linear Kalman filter.

    State:
        [x, y, vx, vy]
    """

    def __init__(
        self,
        x0,
        P0=None,
        process_noise_std=0.5,
        gps_noise_std=3.0
    ):
        self.x = np.asarray(
            x0,
            dtype=float
        ).reshape(4)

        if P0 is None:
            self.P = np.eye(4) * 1.0
        else:
            self.P = np.array(
                P0,
                dtype=float
            )

        # Process noise
        self.base_q = process_noise_std ** 2

        # GPS measurement noise
        self.R = np.eye(2) * (
            gps_noise_std ** 2
        )

        # Measurement matrix
        self.H = np.zeros(
            (2, 4)
        )
        self.H[0, 0] = 1.0
        self.H[1, 1] = 1.0

    def predict(
        self,
        dt,
        control_velocity: Optional[np.ndarray] = None,
        Q_inflate=1.0
    ):
        """
        Predict the next state.

        control_velocity:
            ML estimated velocity [vx, vy]
        """

        dt = max(
            float(dt),
            1e-4
        )

        A = np.array(
            [
                [1, 0, dt, 0],
                [0, 1, 0, dt],
                [0, 0, 1, 0],
                [0, 0, 0, 1]
            ],
            dtype=float
        )

        # ----------------------------------------------------
        # Smooth ML velocity estimate
        # ----------------------------------------------------

        if control_velocity is not None:
            ml_velocity = np.asarray(
                control_velocity,
                dtype=float
            ).reshape(2)

            # Smooth sudden velocity changes
            velocity_blend = 0.65

            self.x[2:4] = (
                velocity_blend * self.x[2:4]
                + (1.0 - velocity_blend) * ml_velocity
            )

        # ----------------------------------------------------
        # State prediction
        # ----------------------------------------------------

        self.x = A.dot(
            self.x
        )

        # ----------------------------------------------------
        # Process noise
        # ----------------------------------------------------

        q = (
            self.base_q
            * float(Q_inflate)
        )

        Q = np.diag(
            [
                q * dt * dt,
                q * dt * dt,
                q * dt,
                q * dt
            ]
        )

        self.P = (
            A.dot(self.P)
            .dot(A.T)
            + Q
        )

    def update(
        self,
        z,
        R=None
    ):
        """
        Correct state using GNSS/GPS measurement.
        """

        if R is None:
            R = self.R

        z = np.asarray(
            z,
            dtype=float
        ).reshape(2)

        S = (
            self.H.dot(self.P)
            .dot(self.H.T)
            + R
        )

        K = (
            self.P
            .dot(self.H.T)
            .dot(np.linalg.inv(S))
        )

        innovation = (
            z
            - self.H.dot(self.x)
        )

        self.x = (
            self.x
            + K.dot(innovation)
        )

        I = np.eye(
            self.P.shape[0]
        )

        self.P = (
            I - K.dot(self.H)
        ).dot(self.P)

    def current_state(self):
        return self.x.copy()


# ============================================================
# MAIN FUSION FUNCTION
# ============================================================

def run_fusion(
    npz_path,
    model_path="step_length_model.joblib",
    process_noise_std=0.5,
    gps_noise_std=3.0
):
    """
    Run complete GNSS + AI/ML Dead Reckoning fusion.

    Returns:
        fused positions
        naive GPS positions
        DR positions
        errors
        operating modes
    """

    # ========================================================
    # 1. LOAD DATASET
    # ========================================================

    print("\nLoading dataset...")

    data = np.load(
        npz_path
    )

    t = data["t"]
    gt_pos = data["gt_pos"]
    acc = data["acc"]
    gyro = data["gyro"]

    gps_pos = data.get(
        "gps_pos"
    )

    gps_available = data.get(
        "gps_available"
    )

    if gps_pos is None:
        raise ValueError(
            "gps_pos is missing from dataset"
        )

    if gps_available is None:
        raise ValueError(
            "gps_available is missing from dataset"
        )

    gps_pos = np.asarray(
        gps_pos,
        dtype=float
    )

    gps_available = np.asarray(
        gps_available
    ).astype(bool)

    # ========================================================
    # 2. LOAD ML MODEL
    # ========================================================

    print(
        "Loading ML model..."
    )

    if not os.path.exists(
        model_path
    ):
        print(
            "ML model not found."
        )
        print(
            "Training ML model..."
        )

        ml_step_length.train_and_save_model(
            npz_path,
            model_path
        )

    model_obj = joblib.load(
        model_path
    )

    if isinstance(
        model_obj,
        dict
    ):
        model = model_obj.get(
            "model",
            model_obj
        )
        meta = model_obj.get(
            "meta",
            {}
        )
    else:
        model = model_obj
        meta = {}

    # ========================================================
    # 3. SAMPLING FREQUENCY
    # ========================================================

    if t.size >= 2:
        dt_med = float(
            np.median(
                np.diff(t)
            )
        )

        if dt_med > 0:
            fs = 1.0 / dt_med
        else:
            fs = None
    else:
        fs = None

    # ========================================================
    # 4. DETECT STEPS
    # ========================================================

    step_indices, mag, thresh = (
        dead_reckoning.detect_steps(
            acc,
            fs=fs
        )
    )

    print(
        f"Fusion: detected "
        f"{len(step_indices)} steps"
    )

    # ========================================================
    # 5. HEADING ESTIMATION
    # ========================================================

    gyro_z = gyro[:, 2]
    mag_heading = None

    # Simulation heading support
    #
    # NOTE:
    # For the final real-world system this should be replaced
    # with actual magnetometer / IMU heading estimation.

    if "gt_heading" in data:
        rng = np.random.default_rng(
            123
        )

        noise_std = np.deg2rad(
            3.0
        )

        mag_heading = (
            data["gt_heading"]
            + rng.normal(
                0.0,
                noise_std,
                size=data["gt_heading"].shape
            )
        )

    heading = (
        dead_reckoning.estimate_heading(
            gyro_z,
            t=t,
            alpha=0.98,
            mag_heading=mag_heading
        )
    )

    # ========================================================
    # 6. ML FEATURES
    # ========================================================

    features, _ = (
        ml_step_length.extract_features_for_steps(
            acc,
            t,
            step_indices
        )
    )

    if features.shape[0] == 0:
        raise ValueError(
            "No valid ML features found."
        )

    if "median_dt_impute" in meta:
        median_dt = float(
            meta["median_dt_impute"]
        )
    else:
        median_dt = float(
            np.nanmedian(
                features[:, 1]
            )
        )

    features[:, 1] = np.where(
        np.isnan(
            features[:, 1]
        ),
        median_dt,
        features[:, 1]
    )

    # ========================================================
    # 7. ML STEP LENGTH PREDICTION
    # ========================================================

    step_lengths_pred = (
        model.predict(
            features
        )
    )

    step_lengths_pred = np.asarray(
        step_lengths_pred,
        dtype=float
    )

    # Prevent invalid values
    step_lengths_pred = np.maximum(
        step_lengths_pred,
        0.05
    )

    # ========================================================
    # 8. VARIABLE STEP DEAD RECKONING
    # ========================================================

    initial_pos = gt_pos[0]

    dr_var_positions = (
        ml_step_length.reconstruct_path_variable(
            initial_pos,
            step_indices,
            heading,
            step_lengths_pred
        )
    )

    # ========================================================
    # 9. FIXED STEP DEAD RECKONING
    # ========================================================

    dr_fixed = (
        dead_reckoning.reconstruct_position(
            initial_pos,
            step_indices,
            heading,
            step_length=0.7
        )
    )

    dr_fixed_positions = dr_fixed[0]

    # ========================================================
    # 10. NAIVE GPS FREEZE BASELINE
    # ========================================================

    naive_positions = np.zeros_like(
        gps_pos
    )

    last_gps = gps_pos[0]

    for i in range(
        gps_pos.shape[0]
    ):
        if gps_available[i]:
            last_gps = gps_pos[i]

        naive_positions[i] = (
            last_gps
        )

    # ========================================================
    # 11. INITIAL KALMAN STATE
    # ========================================================

    N = t.size

    fused_positions = np.zeros(
        (N, 2),
        dtype=float
    )

    if gps_available[0]:
        x0 = np.array(
            [
                gps_pos[0, 0],
                gps_pos[0, 1],
                0.0,
                0.0
            ]
        )
    else:
        x0 = np.array(
            [
                gt_pos[0, 0],
                gt_pos[0, 1],
                0.0,
                0.0
            ]
        )

    kf = KalmanFilter(
        x0,
        process_noise_std=process_noise_std,
        gps_noise_std=gps_noise_std
    )

    # ========================================================
    # 12. STEP LENGTH LOOKUP
    # ========================================================

    step_len_by_idx = {
        int(idx): float(length)
        for idx, length in zip(
            step_indices,
            step_lengths_pred
        )
    }

    # ========================================================
    # 13. STEP DURATION LOOKUP
    # ========================================================

    step_dt_by_idx = {}
    prev_idx = 0

    for idx in step_indices:
        idx = int(idx)

        if idx > prev_idx:
            step_dt = float(
                t[idx] - t[prev_idx]
            )
        else:
            if len(t) >= 2:
                step_dt = float(
                    np.median(
                        np.diff(t)
                    )
                )
            else:
                step_dt = 0.01

        step_dt_by_idx[idx] = max(
            step_dt,
            1e-3
        )

        prev_idx = idx

    # ========================================================
    # 14. CREATE EXPLICIT NAVIGATION MODES
    # ========================================================

    modes = np.empty(
        N,
        dtype=object
    )

    # ========================================================
    # 15. RUN SEAMLESS GNSS / DR FUSION
    # ========================================================

    print(
        "\nStarting seamless navigation..."
    )

    previous_mode = None
    last_t = t[0]

    last_ml_velocity = np.array(
        [0.0, 0.0]
    )

    for i in range(N):

        # ----------------------------------------------------
        # Calculate dt
        # ----------------------------------------------------

        if i > 0:
            dt = float(
                t[i] - last_t
            )
        else:
            if len(t) >= 2:
                dt = float(
                    np.median(
                        np.diff(t)
                    )
                )
            else:
                dt = 0.01

        dt = max(
            dt,
            1e-4
        )

        # ----------------------------------------------------
        # DETERMINE NAVIGATION MODE
        # ----------------------------------------------------

        if gps_available[i]:
            mode = (
                "GNSS + INS Fusion"
            )
        else:
            mode = (
                "GNSS LOST - "
                "AI/ML Dead Reckoning"
            )

        modes[i] = mode

        # ----------------------------------------------------
        # PRINT MODE TRANSITION
        # ----------------------------------------------------

        if mode != previous_mode:
            print(
                f"\nTime {t[i]:.2f}s : "
                f"{mode}"
            )
            previous_mode = mode

        # ----------------------------------------------------
        # ML VELOCITY UPDATE
        # ----------------------------------------------------

        if i in step_len_by_idx:
            L = step_len_by_idx[i]

            theta = float(
                heading[i]
            )

            step_dt = (
                step_dt_by_idx[i]
            )

            last_ml_velocity = np.array(
                [
                    L * np.cos(theta),
                    L * np.sin(theta)
                ],
                dtype=float
            ) / max(
                step_dt,
                1e-3
            )

        # ----------------------------------------------------
        # GNSS AVAILABLE / LOST
        # ----------------------------------------------------

        if gps_available[i]:
            Q_inflate = 1.0
        else:
            Q_inflate = 2.0

        # ----------------------------------------------------
        # PREDICTION
        # ----------------------------------------------------

        kf.predict(
            dt,
            control_velocity=last_ml_velocity,
            Q_inflate=Q_inflate
        )

        # ----------------------------------------------------
        # GNSS CORRECTION
        # ----------------------------------------------------

        if gps_available[i]:
            kf.update(
                gps_pos[i]
            )

        # ----------------------------------------------------
        # SAVE POSITION
        # ----------------------------------------------------

        fused_positions[i] = (
            kf.current_state()[:2]
        )

        last_t = t[i]

    # ========================================================
    # 16. REPORT MODE TRANSITIONS
    # ========================================================

    print(
        "\nNavigation mode switching completed."
    )

    unique_modes = []

    for mode in modes:
        if mode not in unique_modes:
            unique_modes.append(
                mode
            )

    print(
        "\nModes used:"
    )

    for mode in unique_modes:
        print(
            "  ✓",
            mode
        )

    # ========================================================
    # 17. ERROR FUNCTION
    # ========================================================

    def compute_errors(
        pred_ts,
        ref_ts
    ):
        d = np.linalg.norm(
            pred_ts - ref_ts,
            axis=1
        )

        return (
            float(
                np.mean(d)
            ),
            float(
                np.max(d)
            )
        )

    # ========================================================
    # 18. GROUND TRUTH AT STEPS
    # ========================================================

    gt_at_steps = np.vstack(
        [
            gt_pos[0]
        ]
        +
        [
            gt_pos[int(idx)]
            for idx in step_indices
        ]
    )

    # ========================================================
    # 19. DR VARIABLE ERROR
    # ========================================================

    dr_var_mean, dr_var_max = (
        compute_errors(
            dr_var_positions,
            gt_at_steps
        )
    )

    # ========================================================
    # 20. DR FIXED ERROR
    # ========================================================

    dr_fixed_mean, dr_fixed_max = (
        compute_errors(
            dr_fixed_positions,
            gt_at_steps
        )
    )

    # ========================================================
    # 21. NAIVE GPS ERROR
    # ========================================================

    naive_mean, naive_max = (
        compute_errors(
            naive_positions,
            gt_pos
        )
    )

    # ========================================================
    # 22. FUSED ERROR
    # ========================================================

    fused_mean, fused_max = (
        compute_errors(
            fused_positions,
            gt_pos
        )
    )

    # ========================================================
    # 23. GNSS BLACKOUT ERROR
    # ========================================================

    blackout_mask = (
        ~gps_available
    )

    if np.any(
        blackout_mask
    ):
        blackout_error = np.linalg.norm(
            fused_positions[blackout_mask]
            - gt_pos[blackout_mask],
            axis=1
        )

        blackout_mean = float(
            np.mean(
                blackout_error
            )
        )

        blackout_max = float(
            np.max(
                blackout_error
            )
        )

    else:
        blackout_mean = float(
            "nan"
        )

        blackout_max = float(
            "nan"
        )

    # ========================================================
    # 24. PRINT IMPORTANT PERFORMANCE
    # ========================================================

    print(
        "\nGNSS Blackout Performance:"
    )

    print(
        f"Mean blackout error : "
        f"{blackout_mean:.3f} m"
    )

    print(
        f"Max blackout error  : "
        f"{blackout_max:.3f} m"
    )

    # ========================================================
    # 25. RESULTS
    # ========================================================

    results = {
        "fused_positions":
            fused_positions,

        "naive_positions":
            naive_positions,

        "dr_var_positions":
            dr_var_positions,

        "dr_fixed_positions":
            dr_fixed_positions,

        "gt_pos":
            gt_pos,

        "step_indices":
            step_indices,

        "step_lengths_pred":
            step_lengths_pred,

        "modes":
            modes,

        "blackout_mean_error":
            blackout_mean,

        "blackout_max_error":
            blackout_max,

        "errors": {
            "dr_var": (
                dr_var_mean,
                dr_var_max
            ),

            "dr_fixed": (
                dr_fixed_mean,
                dr_fixed_max
            ),

            "naive": (
                naive_mean,
                naive_max
            ),

            "fused": (
                fused_mean,
                fused_max
            )
        }
    }

    return results


# ============================================================
# COMMAND LINE ENTRY
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Run AI/ML GNSS + Dead Reckoning Fusion"
        )
    )

    parser.add_argument(
        "npz",
        help=(
            "Path to .npz dataset"
        )
    )

    parser.add_argument(
        "--model",
        default="step_length_model.joblib",
        help=(
            "Path to trained ML model"
        )
    )

    args = parser.parse_args()

    result = run_fusion(
        args.npz,
        model_path=args.model
    )

    print(
        "\nFusion errors:"
    )

    print(
        result["errors"]
    )
