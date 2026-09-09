import numpy as np
from pathlib import Path


# ============================================================
# File paths
# ============================================================

DATA_PATH = Path("data/simulated_run_filtered.npz")
OUTPUT_PATH = Path("data/heading_estimation_result.npz")


# ============================================================
# Utility
# ============================================================

def wrap_angle(angle):
    """
    Wrap an angle to the range [-pi, pi].
    """
    return (angle + np.pi) % (2.0 * np.pi) - np.pi


# ============================================================
# Magnetometer Heading
# ============================================================

def magnetometer_heading(mag):
    """
    Estimate heading from the magnetometer.

    Current simulator convention:
        heading = atan2(-My, Mx)

    Ground-truth heading is NOT used.
    """

    mx = mag[:, 0]
    my = mag[:, 1]

    heading = np.arctan2(-my, mx)

    # Remove discontinuities at +/-180 degrees.
    heading = np.unwrap(heading)

    return heading


# ============================================================
# Magnetometer Confidence
# ============================================================

def calculate_mag_confidence(mag):
    """
    Estimate magnetometer reliability from magnetic-field magnitude.

    Large deviations from the normal magnetic-field magnitude
    indicate possible magnetic disturbance.
    """

    magnitude = np.linalg.norm(mag, axis=1)

    # Robust reference value.
    reference = np.median(magnitude)

    # Relative deviation.
    deviation = (
        np.abs(magnitude - reference)
        / max(reference, 1e-6)
    )

    # Convert deviation into confidence.
    confidence = 1.0 - np.clip(
        deviation / 0.20,
        0.0,
        1.0
    )

    # Never completely trust a disturbed measurement.
    confidence = np.clip(
        confidence,
        0.05,
        1.0
    )

    return confidence


# ============================================================
# Gyroscope + Magnetometer Fusion
# ============================================================

def fuse_gyro_magnetometer(
    gyro_z,
    mag_heading,
    confidence,
    t
):
    """
    Fuse gyroscope and magnetometer using a small
    2-state Kalman filter.

    State:
        1. Heading
        2. Gyroscope bias

    Gyroscope:
        Provides short-term heading changes.

    Magnetometer:
        Corrects long-term drift.

    Ground truth is NOT used.
    """

    n = len(mag_heading)

    heading = np.zeros(n)
    gyro_bias = np.zeros(n)

    # --------------------------------------------------------
    # Initial state
    # --------------------------------------------------------

    # Start from magnetometer measurement.
    heading[0] = mag_heading[0]

    # No assumption about gyro bias.
    gyro_bias[0] = 0.0

    # --------------------------------------------------------
    # Initial covariance
    # --------------------------------------------------------

    P = np.array([
        [
            np.deg2rad(3.0) ** 2,
            0.0
        ],
        [
            0.0,
            np.deg2rad(0.5) ** 2
        ]
    ])

    # --------------------------------------------------------
    # Process noise
    # --------------------------------------------------------

    q_heading = np.deg2rad(0.15) ** 2
    q_bias = np.deg2rad(0.01) ** 2

    # --------------------------------------------------------
    # Magnetometer measurement noise
    # --------------------------------------------------------

    base_r = np.deg2rad(3.0) ** 2

    # ========================================================
    # Main filter loop
    # ========================================================

    for i in range(1, n):

        # ----------------------------------------------------
        # Time difference
        # ----------------------------------------------------

        dt = float(t[i] - t[i - 1])

        dt = max(dt, 1e-4)

        # ----------------------------------------------------
        # 1. Prediction using gyro
        # ----------------------------------------------------

        predicted_heading = (
            heading[i - 1]
            + (
                gyro_z[i - 1]
                - gyro_bias[i - 1]
            )
            * dt
        )

        predicted_bias = gyro_bias[i - 1]

        x_pred = np.array([
            predicted_heading,
            predicted_bias
        ])

        # ----------------------------------------------------
        # State transition matrix
        # ----------------------------------------------------

        F = np.array([
            [1.0, -dt],
            [0.0, 1.0]
        ])

        # ----------------------------------------------------
        # Process covariance
        # ----------------------------------------------------

        Q = np.array([
            [q_heading, 0.0],
            [0.0, q_bias]
        ])

        P = F @ P @ F.T + Q

        # ----------------------------------------------------
        # 2. Magnetometer correction
        # ----------------------------------------------------

        measurement = mag_heading[i]

        # Angular innovation.
        innovation = wrap_angle(
            measurement - predicted_heading
        )

        # ----------------------------------------------------
        # Adaptive measurement noise
        # ----------------------------------------------------

        conf = confidence[i]

        R = base_r / max(conf, 0.05)

        # Measurement matrix.
        H = np.array([
            [1.0, 0.0]
        ])

        # Innovation covariance.
        S = (
            H @ P @ H.T
            + R
        )

        # Kalman gain.
        K = (
            P @ H.T
            / S
        )

        # ----------------------------------------------------
        # State update
        # ----------------------------------------------------

        x_update = (
            x_pred
            + K.flatten() * innovation
        )

        # Normalize heading.
        x_update[0] = wrap_angle(
            x_update[0]
        )

        # Update covariance.
        P = (
            np.eye(2)
            - K @ H
        ) @ P

        # ----------------------------------------------------
        # Store
        # ----------------------------------------------------

        heading[i] = x_update[0]
        gyro_bias[i] = x_update[1]

    # Make heading continuous.
    heading = np.unwrap(heading)

    return heading, gyro_bias


# ============================================================
# Main
# ============================================================

def main():

    print()
    print("==============================================")
    print(" Corrected Heading Estimation")
    print("==============================================")
    print()

    # --------------------------------------------------------
    # Check dataset
    # --------------------------------------------------------

    if not DATA_PATH.exists():

        raise FileNotFoundError(
            f"Dataset not found: {DATA_PATH}"
        )

    # --------------------------------------------------------
    # Load data
    # --------------------------------------------------------

    data = np.load(DATA_PATH)

    t = data["t"]
    mag = data["mag"]
    gyro = data["gyro"]

    print(f"Samples : {len(t)}")
    print(f"Duration: {t[-1]:.2f} seconds")
    print()

    # --------------------------------------------------------
    # 1. Magnetometer heading
    # --------------------------------------------------------

    mag_heading = magnetometer_heading(
        mag
    )

    initial_mag_heading = np.rad2deg(
        mag_heading[0]
    )

    print(
        "Initial magnetometer heading: "
        f"{initial_mag_heading:.2f} deg"
    )

    # --------------------------------------------------------
    # 2. Magnetometer confidence
    # --------------------------------------------------------

    confidence = calculate_mag_confidence(
        mag
    )

    print(
        "Mean magnetometer confidence: "
        f"{np.mean(confidence):.3f}"
    )

    # --------------------------------------------------------
    # 3. Gyro + magnetometer fusion
    # --------------------------------------------------------

    gyro_z = gyro[:, 2]

    fused_heading, gyro_bias = (
        fuse_gyro_magnetometer(
            gyro_z,
            mag_heading,
            confidence,
            t
        )
    )

    # --------------------------------------------------------
    # Heading information
    # --------------------------------------------------------

    initial_fused_heading = np.rad2deg(
        fused_heading[0]
    )

    final_fused_heading = np.rad2deg(
        fused_heading[-1]
    )

    total_heading_change = np.rad2deg(
        wrap_angle(
            fused_heading[-1]
            - fused_heading[0]
        )
    )

    final_gyro_bias = np.rad2deg(
        gyro_bias[-1]
    )

    print()
    print("----------------------------------------------")
    print(" Heading Results")
    print("----------------------------------------------")

    print(
        "Initial fused heading: "
        f"{initial_fused_heading:.2f} deg"
    )

    print(
        "Final fused heading: "
        f"{final_fused_heading:.2f} deg"
    )

    print(
        "Total fused heading change: "
        f"{total_heading_change:.2f} deg"
    )

    print(
        "Final estimated gyro bias: "
        f"{final_gyro_bias:.4f} deg/s"
    )

    # --------------------------------------------------------
    # 4. Save results
    # --------------------------------------------------------

    np.savez(
        OUTPUT_PATH,

        t=t,

        # Raw magnetometer heading
        mag_heading=mag_heading,

        # Fused heading
        fused_heading=fused_heading,

        # Magnetometer confidence
        magnetometer_confidence=confidence,

        # Estimated gyro bias
        gyro_bias=gyro_bias
    )

    # --------------------------------------------------------
    # Done
    # --------------------------------------------------------

    print()
    print("----------------------------------------------")
    print(" Output")
    print("----------------------------------------------")

    print(
        f"Saved: {OUTPUT_PATH}"
    )

    print()
    print(
        "Ground truth heading was NOT used."
    )

    print()
    print("Heading estimation completed successfully.")
    print()


# ============================================================
# Program Entry Point
# ============================================================

if __name__ == "__main__":
    main()