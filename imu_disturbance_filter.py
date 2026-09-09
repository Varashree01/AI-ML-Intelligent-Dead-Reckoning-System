"""
Adaptive IMU disturbance filtering - V2

Detects vibration and bump/shock events using robust,
data-adaptive thresholds instead of fixed thresholds.

This module does not modify ground truth.
"""

import os
import numpy as np


def _causal_ema(signal, alpha):
    """Causal exponential moving average."""
    signal = np.asarray(signal, dtype=float)

    out = np.empty_like(signal)
    out[0] = signal[0]

    for i in range(1, len(signal)):
        out[i] = out[i - 1] + alpha[i] * (
            signal[i] - out[i - 1]
        )

    return out


def _robust_threshold(values, sigma_multiplier=5.0, minimum=0.0):
    """
    Calculate a robust adaptive threshold using median and MAD.
    """

    values = np.asarray(values, dtype=float)

    median_value = np.median(values)

    mad = np.median(
        np.abs(values - median_value)
    )

    robust_sigma = 1.4826 * mad

    threshold = median_value + (
        sigma_multiplier * max(robust_sigma, 1e-5)
    )

    return max(threshold, minimum)


def adaptive_imu_filter(acc, gyro, dt):
    """
    Adaptive causal IMU filtering.

    Returns:
        filtered_acc
        filtered_gyro
        disturbance_score
        vibration_mask
        bump_mask
    """

    acc = np.asarray(acc, dtype=float)
    gyro = np.asarray(gyro, dtype=float)

    if acc.ndim != 2 or acc.shape[1] != 3:
        raise ValueError("acc must have shape (N, 3)")

    if gyro.ndim != 2 or gyro.shape[1] != 3:
        raise ValueError("gyro must have shape (N, 3)")

    if len(acc) != len(gyro):
        raise ValueError(
            "acc and gyro must have the same number of samples"
        )

    n = len(acc)

    if n < 3:
        return (
            acc.copy(),
            gyro.copy(),
            np.zeros(n),
            np.zeros(n, dtype=bool),
            np.zeros(n, dtype=bool),
        )

    # ---------------------------------------------------------
    # 1. Mild baseline smoothing
    # ---------------------------------------------------------

    base_alpha = 0.18

    alpha_base = np.full(n, base_alpha)

    acc_base = np.column_stack([
        _causal_ema(
            acc[:, j],
            alpha_base
        )
        for j in range(3)
    ])

    gyro_base = np.column_stack([
        _causal_ema(
            gyro[:, j],
            alpha_base
        )
        for j in range(3)
    ])

    # ---------------------------------------------------------
    # 2. High-frequency residual
    # ---------------------------------------------------------

    acc_hf = acc - acc_base
    gyro_hf = gyro - gyro_base

    acc_hf_mag = np.linalg.norm(
        acc_hf,
        axis=1
    )

    gyro_hf_mag = np.linalg.norm(
        gyro_hf,
        axis=1
    )

    # ---------------------------------------------------------
    # 3. Short causal RMS
    # ---------------------------------------------------------

    window = max(
        int(round(0.20 / max(dt, 1e-4))),
        3
    )

    disturbance_score = np.zeros(n)

    for i in range(n):

        start = max(
            0,
            i - window + 1
        )

        acc_rms = np.sqrt(
            np.mean(
                acc_hf_mag[start:i + 1] ** 2
            )
        )

        gyro_rms = np.sqrt(
            np.mean(
                gyro_hf_mag[start:i + 1] ** 2
            )
        )

        disturbance_score[i] = (
            acc_rms +
            0.35 * gyro_rms
        )

    # ---------------------------------------------------------
    # 4. Adaptive vibration threshold
    # ---------------------------------------------------------

    # Use the beginning of the recording as a calibration
    # segment for estimating normal sensor noise.

    calibration_samples = max(
        int(0.20 * n),
        window
    )

    calibration_samples = min(
        calibration_samples,
        n
    )

    calibration_score = disturbance_score[
        :calibration_samples
    ]

    vibration_threshold = _robust_threshold(
        calibration_score,
        sigma_multiplier=5.0,
        minimum=0.045
    )

    vibration_mask = (
        disturbance_score >
        vibration_threshold
    )

    # ---------------------------------------------------------
    # 5. Robust bump/shock detection
    # ---------------------------------------------------------

    acc_hf_median = np.median(
        acc_hf_mag
    )

    acc_hf_mad = np.median(
        np.abs(
            acc_hf_mag -
            acc_hf_median
        )
    )

    acc_hf_sigma = max(
        1.4826 * acc_hf_mad,
        1e-5
    )

    bump_threshold = max(
        acc_hf_median +
        8.0 * acc_hf_sigma,

        np.percentile(
            acc_hf_mag,
            99
        ),

        0.45
    )

    # Sudden change in residual

    previous_acc_hf = np.concatenate(
        (
            [acc_hf_mag[0]],
            acc_hf_mag[:-1]
        )
    )

    acc_hf_change = np.abs(
        acc_hf_mag -
        previous_acc_hf
    )

    change_threshold = max(
        np.percentile(
            acc_hf_change,
            99
        ),
        0.20
    )

    bump_mask = (
        (acc_hf_mag > bump_threshold)
        &
        (acc_hf_change > change_threshold)
    )

    # ---------------------------------------------------------
    # 6. Protect a short period around detected bumps
    # ---------------------------------------------------------

    protection_samples = max(
        int(round(0.08 / max(dt, 1e-4))),
        1
    )

    bump_indices = np.where(
        bump_mask
    )[0]

    for idx in bump_indices:

        end_idx = min(
            n,
            idx + protection_samples + 1
        )

        bump_mask[idx:end_idx] = True

    # ---------------------------------------------------------
    # 7. Adaptive causal filtering
    # ---------------------------------------------------------

    filtered_acc = np.zeros_like(acc)
    filtered_gyro = np.zeros_like(gyro)

    filtered_acc[0] = acc[0]
    filtered_gyro[0] = gyro[0]

    for i in range(1, n):

        if bump_mask[i]:

            # Strong filtering during shock
            alpha = 0.045

        elif vibration_mask[i]:

            # Moderate filtering during vibration
            alpha = 0.10

        else:

            # Preserve normal vehicle dynamics
            alpha = 0.20

        filtered_acc[i] = (
            filtered_acc[i - 1]
            +
            alpha *
            (
                acc[i] -
                filtered_acc[i - 1]
            )
        )

        filtered_gyro[i] = (
            filtered_gyro[i - 1]
            +
            alpha *
            (
                gyro[i] -
                filtered_gyro[i - 1]
            )
        )

    return (
        filtered_acc,
        filtered_gyro,
        disturbance_score,
        vibration_mask,
        bump_mask,
        vibration_threshold,
        bump_threshold,
    )


def main():

    input_path = os.path.join(
        "data",
        "simulated_run.npz"
    )

    output_path = os.path.join(
        "data",
        "simulated_run_filtered.npz"
    )

    if not os.path.exists(input_path):

        raise FileNotFoundError(
            f"Input dataset not found: {input_path}\n"
            "Run `python data_simulation.py` first."
        )

    data = dict(
        np.load(
            input_path,
            allow_pickle=True
        )
    )

    required = [
        "acc",
        "gyro",
        "dt"
    ]

    missing = [
        key
        for key in required
        if key not in data
    ]

    if missing:

        raise KeyError(
            f"Missing required dataset keys: {missing}"
        )

    acc = np.asarray(
        data["acc"],
        dtype=float
    )

    gyro = np.asarray(
        data["gyro"],
        dtype=float
    )

    dt = float(data["dt"])

    (
        filtered_acc,
        filtered_gyro,
        disturbance_score,
        vibration_mask,
        bump_mask,
        vibration_threshold,
        bump_threshold,
    ) = adaptive_imu_filter(
        acc,
        gyro,
        dt
    )

    # ---------------------------------------------------------
    # Preserve original dataset
    # ---------------------------------------------------------

    data["raw_acc"] = acc
    data["raw_gyro"] = gyro

    data["acc_filtered"] = filtered_acc
    data["gyro_filtered"] = filtered_gyro

    data["imu_disturbance_score"] = (
        disturbance_score
    )

    data["vibration_detected"] = (
        vibration_mask
    )

    data["bump_detected"] = (
        bump_mask
    )

    np.savez(
        output_path,
        **data
    )

    # ---------------------------------------------------------
    # RMS comparison
    # ---------------------------------------------------------

    raw_base = np.column_stack([
        _causal_ema(
            acc[:, j],
            np.full(len(acc), 0.18)
        )
        for j in range(3)
    ])

    filtered_base = np.column_stack([
        _causal_ema(
            filtered_acc[:, j],
            np.full(len(acc), 0.18)
        )
        for j in range(3)
    ])

    raw_hf = acc - raw_base

    filtered_hf = (
        filtered_acc -
        filtered_base
    )

    raw_rms = float(
        np.sqrt(
            np.mean(
                raw_hf ** 2
            )
        )
    )

    filtered_rms = float(
        np.sqrt(
            np.mean(
                filtered_hf ** 2
            )
        )
    )

    # ---------------------------------------------------------
    # Statistics
    # ---------------------------------------------------------

    vibration_count = int(
        vibration_mask.sum()
    )

    bump_count = int(
        bump_mask.sum()
    )

    vibration_percentage = (
        100.0 *
        vibration_count /
        len(acc)
    )

    bump_percentage = (
        100.0 *
        bump_count /
        len(acc)
    )

    print(
        "Adaptive IMU filtering V2 completed."
    )

    print(
        f"Input : {input_path}"
    )

    print(
        f"Output: {output_path}"
    )

    print(
        f"Samples: {len(acc)}"
    )

    print(
        f"Adaptive vibration threshold: "
        f"{vibration_threshold:.5f}"
    )

    print(
        f"Adaptive bump threshold: "
        f"{bump_threshold:.5f}"
    )

    print(
        f"Vibration samples detected: "
        f"{vibration_count}"
    )

    print(
        f"Vibration percentage: "
        f"{vibration_percentage:.2f}%"
    )

    print(
        f"Bump/shock samples detected: "
        f"{bump_count}"
    )

    print(
        f"Bump/shock percentage: "
        f"{bump_percentage:.2f}%"
    )

    print(
        f"High-frequency acceleration RMS before: "
        f"{raw_rms:.5f}"
    )

    print(
        f"High-frequency acceleration RMS after : "
        f"{filtered_rms:.5f}"
    )

    if raw_rms > 0:

        reduction = (
            100.0 *
            (
                1.0 -
                filtered_rms /
                raw_rms
            )
        )

        print(
            f"High-frequency RMS reduction: "
            f"{reduction:.2f}%"
        )

    print(
        "No ground-truth values were modified."
    )


if __name__ == "__main__":
    main()