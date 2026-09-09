import numpy as np
from pathlib import Path


# ============================================================
# File Paths
# ============================================================

DATA_PATH = Path("data/simulated_run_filtered.npz")
HEADING_PATH = Path("data/heading_estimation_result.npz")


# ============================================================
# Utility Function
# ============================================================

def wrap_angle(angle):
    """
    Wrap angle to the range [-pi, pi].
    """
    return (angle + np.pi) % (2.0 * np.pi) - np.pi


# ============================================================
# Calculate Heading Errors
# ============================================================

def calculate_errors(estimated, ground_truth):
    """
    Calculate heading error metrics.

    Returns:
        error_deg
        MAE
        RMSE
        Maximum error
    """

    error = wrap_angle(
        estimated - ground_truth
    )

    error_deg = np.rad2deg(error)

    mae = np.mean(
        np.abs(error_deg)
    )

    rmse = np.sqrt(
        np.mean(error_deg ** 2)
    )

    maximum = np.max(
        np.abs(error_deg)
    )

    return (
        error_deg,
        mae,
        rmse,
        maximum
    )


# ============================================================
# Evaluate Heading
# ============================================================

def evaluate_section(
    name,
    estimated,
    ground_truth
):
    """
    Evaluate one heading estimate.
    """

    (
        error,
        mae,
        rmse,
        maximum
    ) = calculate_errors(
        estimated,
        ground_truth
    )

    print()
    print(name)
    print("-" * len(name))

    print(
        f"Mean absolute heading error : "
        f"{mae:.3f} deg"
    )

    print(
        f"RMSE heading error           : "
        f"{rmse:.3f} deg"
    )

    print(
        f"Maximum heading error        : "
        f"{maximum:.3f} deg"
    )

    return error


# ============================================================
# Main
# ============================================================

def main():

    print()
    print("==============================================")
    print(" Heading Estimation Evaluation")
    print("==============================================")
    print()

    # --------------------------------------------------------
    # Check files
    # --------------------------------------------------------

    if not DATA_PATH.exists():

        raise FileNotFoundError(
            f"Dataset not found: {DATA_PATH}"
        )

    if not HEADING_PATH.exists():

        raise FileNotFoundError(
            f"Heading result not found: {HEADING_PATH}"
        )

    # --------------------------------------------------------
    # Load data
    # --------------------------------------------------------

    data = np.load(
        DATA_PATH
    )

    heading_data = np.load(
        HEADING_PATH
    )

    t = data["t"]

    ground_truth = data["gt_heading"]

    # New heading estimator outputs
    mag_heading = heading_data[
        "mag_heading"
    ]

    fused_heading = heading_data[
        "fused_heading"
    ]

    # --------------------------------------------------------
    # 1. Magnetometer Heading
    # --------------------------------------------------------

    evaluate_section(
        "1. Magnetometer Heading",
        mag_heading,
        ground_truth
    )

    # --------------------------------------------------------
    # 2. Gyroscope + Magnetometer
    # --------------------------------------------------------

    fused_error = evaluate_section(
        "2. Gyroscope + Magnetometer Fusion",
        fused_heading,
        ground_truth
    )

    # --------------------------------------------------------
    # 3. Initial Heading
    # --------------------------------------------------------

    print()
    print("3. Initial Heading")
    print("------------------")

    gt_initial = np.rad2deg(
        ground_truth[0]
    )

    mag_initial = np.rad2deg(
        mag_heading[0]
    )

    fused_initial = np.rad2deg(
        fused_heading[0]
    )

    initial_mag_error = np.rad2deg(
        wrap_angle(
            mag_heading[0]
            - ground_truth[0]
        )
    )

    initial_fused_error = np.rad2deg(
        wrap_angle(
            fused_heading[0]
            - ground_truth[0]
        )
    )

    print(
        f"Ground-truth initial : "
        f"{gt_initial:.3f} deg"
    )

    print(
        f"Magnetometer initial : "
        f"{mag_initial:.3f} deg"
    )

    print(
        f"Fused initial        : "
        f"{fused_initial:.3f} deg"
    )

    print(
        f"Magnetometer initial error : "
        f"{initial_mag_error:.3f} deg"
    )

    print(
        f"Fused initial error        : "
        f"{initial_fused_error:.3f} deg"
    )

    # --------------------------------------------------------
    # 4. Total Heading Change
    # --------------------------------------------------------

    gt_change = np.rad2deg(
        wrap_angle(
            ground_truth[-1]
            - ground_truth[0]
        )
    )

    mag_change = np.rad2deg(
        wrap_angle(
            mag_heading[-1]
            - mag_heading[0]
        )
    )

    fused_change = np.rad2deg(
        wrap_angle(
            fused_heading[-1]
            - fused_heading[0]
        )
    )

    print()
    print("4. Total Heading Change")
    print("-----------------------")

    print(
        f"Ground truth : "
        f"{gt_change:.3f} deg"
    )

    print(
        f"Magnetometer : "
        f"{mag_change:.3f} deg"
    )

    print(
        f"Fused        : "
        f"{fused_change:.3f} deg"
    )

    # --------------------------------------------------------
    # 5. GNSS Blackout
    # --------------------------------------------------------

    blackout_start = 25.0
    blackout_end = 35.0

    blackout_mask = (
        (t >= blackout_start)
        &
        (t <= blackout_end)
    )

    print()
    print("5. GNSS Blackout Heading Performance")
    print("-------------------------------------")

    if np.any(blackout_mask):

        blackout_gt = ground_truth[
            blackout_mask
        ]

        blackout_mag = mag_heading[
            blackout_mask
        ]

        blackout_fused = fused_heading[
            blackout_mask
        ]

        # ----------------------------------------------------
        # Magnetometer blackout metrics
        # ----------------------------------------------------

        (
            _,
            mag_blackout_mae,
            mag_blackout_rmse,
            mag_blackout_max
        ) = calculate_errors(
            blackout_mag,
            blackout_gt
        )

        # ----------------------------------------------------
        # Fused blackout metrics
        # ----------------------------------------------------

        (
            _,
            fused_blackout_mae,
            fused_blackout_rmse,
            fused_blackout_max
        ) = calculate_errors(
            blackout_fused,
            blackout_gt
        )

        print()
        print("Magnetometer:")
        print(
            f"  Mean absolute error : "
            f"{mag_blackout_mae:.3f} deg"
        )

        print(
            f"  RMSE                : "
            f"{mag_blackout_rmse:.3f} deg"
        )

        print(
            f"  Maximum error       : "
            f"{mag_blackout_max:.3f} deg"
        )

        print()
        print("Gyroscope + Magnetometer:")
        print(
            f"  Mean absolute error : "
            f"{fused_blackout_mae:.3f} deg"
        )

        print(
            f"  RMSE                : "
            f"{fused_blackout_rmse:.3f} deg"
        )

        print(
            f"  Maximum error       : "
            f"{fused_blackout_max:.3f} deg"
        )

    else:

        print(
            "No GNSS blackout interval found."
        )

    # --------------------------------------------------------
    # 6. Final Summary
    # --------------------------------------------------------

    (
        _,
        mag_mae,
        mag_rmse,
        mag_max
    ) = calculate_errors(
        mag_heading,
        ground_truth
    )

    (
        _,
        fused_mae,
        fused_rmse,
        fused_max
    ) = calculate_errors(
        fused_heading,
        ground_truth
    )

    print()
    print("==============================================")
    print(" Summary")
    print("==============================================")

    print()
    print("Magnetometer Heading:")
    print(
        f"  MAE  : {mag_mae:.3f} deg"
    )
    print(
        f"  RMSE : {mag_rmse:.3f} deg"
    )
    print(
        f"  Max  : {mag_max:.3f} deg"
    )

    print()
    print("Gyroscope + Magnetometer Fusion:")
    print(
        f"  MAE  : {fused_mae:.3f} deg"
    )
    print(
        f"  RMSE : {fused_rmse:.3f} deg"
    )
    print(
        f"  Max  : {fused_max:.3f} deg"
    )

    # --------------------------------------------------------
    # Ground Truth Notice
    # --------------------------------------------------------

    print()
    print("----------------------------------------------")

    print(
        "Ground-truth heading was used ONLY "
        "for evaluation."
    )

    print(
        "The estimator itself does NOT use "
        "ground-truth heading."
    )

    print("----------------------------------------------")

    print()
    print(
        "Heading evaluation completed successfully."
    )

    print()


# ============================================================
# Program Entry Point
# ============================================================

if __name__ == "__main__":
    main()