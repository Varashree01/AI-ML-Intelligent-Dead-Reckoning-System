"""
data_simulation.py

Vehicle-oriented synthetic dataset generator for the
AI-ML based Intelligent Dead Reckoning project.

Generates:
    - Smooth vehicle trajectory
    - Variable vehicle speed
    - Accelerometer
    - Gyroscope
    - Magnetometer
    - GNSS measurements
    - GNSS blackout
    - Bump / pothole disturbances
    - Smartphone mounting misalignment

Ground truth is used only inside the simulator to generate
physical sensor measurements and later for evaluation.
"""

import os

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal.windows import gaussian


def simulate_rectangular_path(
    segment_lengths=(20.0, 10.0),
    speed=1.4,
    dt=0.01,
    seed=1,
    tunnel_start=25.0,
    tunnel_duration=10.0
):
    """
    Generate a vehicle-oriented synthetic dataset.

    The original function name is preserved for compatibility
    with the existing project files.
    """

    rng = np.random.RandomState(seed)

    # =========================================================
    # 1. TIME
    # =========================================================

    total_time = 52.0

    t = np.arange(
        0.0,
        total_time,
        dt
    )

    N = len(t)

    # =========================================================
    # 2. REALISTIC VEHICLE SPEED PROFILE
    # =========================================================

    base_speed = max(
        float(speed),
        0.8
    )

    speed_profile = np.full(
        N,
        base_speed,
        dtype=float
    )

    def add_speed_change(center, amplitude, width):
        nonlocal speed_profile

        speed_profile += (
            amplitude
            * np.exp(
                -0.5
                * ((t - center) / width) ** 2
            )
        )

    # Acceleration
    add_speed_change(
        7.0,
        0.65 * base_speed,
        2.0
    )

    # Braking
    add_speed_change(
        15.0,
        -0.45 * base_speed,
        2.2
    )

    # Recovery
    add_speed_change(
        23.0,
        0.35 * base_speed,
        2.5
    )

    # Slowdown
    add_speed_change(
        31.0,
        -0.30 * base_speed,
        2.0
    )

    # Acceleration
    add_speed_change(
        40.0,
        0.55 * base_speed,
        2.8
    )

    # Braking
    add_speed_change(
        48.0,
        -0.40 * base_speed,
        2.5
    )

    # Low-frequency speed variation
    speed_profile += (
        0.10 * base_speed * np.sin(0.16 * t)
        + 0.05 * base_speed * np.sin(0.43 * t + 0.7)
    )

    speed_profile = np.clip(
        speed_profile,
        0.65,
        4.0
    )

    # Integrate speed to obtain travelled distance
    distance = (
        np.cumsum(speed_profile)
        * dt
    )

    distance -= distance[0]

    # =========================================================
    # 3. SMOOTH CURVED ROAD
    # =========================================================

    y = (
        5.2
        * np.sin(
            0.055 * distance + 0.25
        )
        + 1.8
        * np.sin(
            0.115 * distance + 0.8
        )
        + 0.55
        * np.sin(
            0.23 * distance
        )
    )

    x = (
        distance
        + 0.35
        * np.sin(
            0.035 * distance
        )
        + 0.12
        * np.sin(
            0.11 * distance
        )
    )

    gt_pos = np.column_stack(
        (
            x,
            y
        )
    )

    # =========================================================
    # 4. VELOCITY / ACCELERATION / HEADING
    # =========================================================

    gt_velocity = np.gradient(
        gt_pos,
        dt,
        axis=0
    )

    gt_acceleration = np.gradient(
        gt_velocity,
        dt,
        axis=0
    )

    gt_heading = np.unwrap(
        np.arctan2(
            gt_velocity[:, 1],
            gt_velocity[:, 0]
        )
    )

    vehicle_speed = np.linalg.norm(
        gt_velocity,
        axis=1
    )

    # =========================================================
    # 5. PHONE MOUNTING PARAMETERS
    # =========================================================

    mounting_yaw = np.deg2rad(4.0)
    mounting_roll = np.deg2rad(2.0)
    mounting_pitch = np.deg2rad(-1.5)

    # Yaw rotation
    cy = np.cos(mounting_yaw)
    sy = np.sin(mounting_yaw)

    yaw_mount = np.array(
        [
            [cy, -sy, 0.0],
            [sy, cy, 0.0],
            [0.0, 0.0, 1.0]
        ]
    )

    # Pitch rotation
    cp = np.cos(mounting_pitch)
    sp = np.sin(mounting_pitch)

    pitch_mount = np.array(
        [
            [cp, 0.0, sp],
            [0.0, 1.0, 0.0],
            [-sp, 0.0, cp]
        ]
    )

    # Roll rotation
    cr = np.cos(mounting_roll)
    sr = np.sin(mounting_roll)

    roll_mount = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, cr, -sr],
            [0.0, sr, cr]
        ]
    )

    # Same mounting rotation is used for both
    # accelerometer and magnetometer.
    mount_rotation = (
        yaw_mount
        @ pitch_mount
        @ roll_mount
    )

    # =========================================================
    # 6. GYROSCOPE
    # =========================================================

    gyro_z = np.gradient(
        gt_heading,
        dt
    )

    gyro = np.zeros(
        (N, 3),
        dtype=float
    )

    gyro[:, 2] = gyro_z

    # Slowly varying gyro bias
    gyro_bias = np.column_stack(
        [
            0.0015
            * np.sin(0.08 * t),

            0.0010
            * np.cos(0.06 * t),

            0.0018
            * np.sin(0.05 * t + 0.4)
        ]
    )

    gyro += gyro_bias

    # Gyroscope noise
    gyro += rng.normal(
        scale=0.008,
        size=gyro.shape
    )

    # =========================================================
    # 7. ACCELEROMETER
    # =========================================================

    acc = np.zeros(
        (N, 3),
        dtype=float
    )

    gravity = np.array(
        [
            0.0,
            0.0,
            -9.81
        ]
    )

    for i in range(N):

        yaw = gt_heading[i]

        c = np.cos(yaw)
        s = np.sin(yaw)

        # World -> vehicle horizontal frame
        R_yaw = np.array(
            [
                [c, s, 0.0],
                [-s, c, 0.0],
                [0.0, 0.0, 1.0]
            ]
        )

        acceleration_world = np.array(
            [
                gt_acceleration[i, 0],
                gt_acceleration[i, 1],
                0.0
            ]
        )

        acceleration_vehicle = (
            R_yaw
            @ acceleration_world
        )

        acc[i, 0] = acceleration_vehicle[0]
        acc[i, 1] = acceleration_vehicle[1]
        acc[i, 2] = gravity[2]

    # Apply smartphone mounting misalignment
    acc = (
        mount_rotation
        @ acc.T
    ).T

    # =========================================================
    # 8. ENGINE / ROAD VIBRATION
    # =========================================================

    vibration = np.zeros(
        (N, 3),
        dtype=float
    )

    vibration[:, 0] = (
        0.045
        * np.sin(
            2.0 * np.pi * 8.0 * t
        )
        + 0.025
        * np.sin(
            2.0 * np.pi * 13.0 * t + 0.4
        )
    )

    vibration[:, 1] = (
        0.035
        * np.sin(
            2.0 * np.pi * 7.0 * t + 0.8
        )
        + 0.020
        * np.sin(
            2.0 * np.pi * 11.0 * t
        )
    )

    vibration[:, 2] = (
        0.10
        * np.sin(
            2.0 * np.pi * 9.0 * t
        )
        + 0.045
        * np.sin(
            2.0 * np.pi * 17.0 * t + 0.3
        )
    )

    acc += vibration

    # =========================================================
    # 9. BUMP / POTHOLE EVENTS
    # =========================================================

    bump_times = np.array(
        [
            8.5,
            18.2,
            27.4,
            33.6,
            42.3,
            49.1
        ]
    )

    bump_indices = []

    bump_width_sec = 0.10

    bump_width = max(
        int(
            round(
                bump_width_sec / dt
            )
        ),
        5
    )

    bump_window = gaussian(
        bump_width,
        std=max(
            bump_width / 6.0,
            1.0
        )
    )

    bump_window /= np.max(
        bump_window
    )

    for bump_time in bump_times:

        idx0 = int(
            np.searchsorted(
                t,
                bump_time
            )
        )

        if idx0 >= N:
            continue

        bump_indices.append(
            idx0
        )

        sign = (
            1.0
            if len(bump_indices) % 2
            else -1.0
        )

        for k in range(
            len(bump_window)
        ):

            ii = (
                idx0
                + k
                - len(bump_window) // 2
            )

            if 0 <= ii < N:

                # Vertical bump disturbance
                acc[ii, 2] += (
                    sign
                    * 1.8
                    * bump_window[k]
                )

                # Longitudinal disturbance
                acc[ii, 0] += (
                    0.35
                    * bump_window[k]
                )

                # Angular disturbance
                gyro[ii, 0] += (
                    0.12
                    * bump_window[k]
                )

                gyro[ii, 1] += (
                    0.08
                    * sign
                    * bump_window[k]
                )

    bump_indices = np.array(
        bump_indices,
        dtype=int
    )

    # =========================================================
    # 10. SENSOR NOISE
    # =========================================================

    acc += rng.normal(
        scale=0.035,
        size=acc.shape
    )

    gyro += rng.normal(
        scale=0.006,
        size=gyro.shape
    )

    # Small orientation disturbance
    yaw_jitter = (
        0.004
        * np.sin(0.31 * t)
        + rng.normal(
            scale=0.0015,
            size=N
        )
    )

    for i in range(N):

        c = np.cos(
            yaw_jitter[i]
        )

        s = np.sin(
            yaw_jitter[i]
        )

        Rj = np.array(
            [
                [c, -s],
                [s, c]
            ]
        )

        acc[i, 0:2] = (
            Rj
            @ acc[i, 0:2]
        )

    # =========================================================
    # 11. MAGNETOMETER
    # =========================================================

    # Earth's magnetic field in WORLD coordinates.
    #
    # Horizontal component = 25 uT
    # Vertical component   = 43 uT
    #
    # Total magnitude is approximately 49.7 uT.

    magnetic_field_world = np.array(
        [
            25.0,
            0.0,
            43.0
        ]
    )

    mag = np.zeros(
        (N, 3),
        dtype=float
    )

    for i in range(N):

        yaw = gt_heading[i]

        c = np.cos(yaw)
        s = np.sin(yaw)

        # World -> vehicle/body frame
        R_yaw = np.array(
            [
                [c, s, 0.0],
                [-s, c, 0.0],
                [0.0, 0.0, 1.0]
            ]
        )

        mag_vehicle = (
            R_yaw
            @ magnetic_field_world
        )

        # IMPORTANT:
        # Apply the SAME phone mounting rotation
        # used by the accelerometer.
        mag_phone = (
            mount_rotation
            @ mag_vehicle
        )

        mag[i] = mag_phone

    # Slowly changing magnetometer bias
    mag_bias = np.zeros(
        (N, 3),
        dtype=float
    )

    for i in range(1, N):

        mag_bias[i] = (
            0.995
            * mag_bias[i - 1]
            + rng.normal(
                scale=0.008,
                size=3
            )
        )

    mag += mag_bias

    # Magnetometer sensor noise
    mag += rng.normal(
        scale=0.8,
        size=mag.shape
    )

    # Magnetic disturbances near bumps
    for idx in bump_indices:

        start = max(
            0,
            idx - int(0.05 / dt)
        )

        end = min(
            N,
            idx + int(0.10 / dt)
        )

        mag[start:end] += rng.normal(
            scale=1.5,
            size=(
                end - start,
                3
            )
        )

    # =========================================================
    # 12. COMPATIBILITY MOTION EVENTS
    # =========================================================

    # These are NOT human footsteps.
    # They are vehicle motion-event markers retained
    # for compatibility with older project files.

    avg_event_distance = 0.75

    mean_interval = (
        avg_event_distance
        / max(
            base_speed,
            0.65
        )
    )

    step_times = []

    current_time = 0.5

    while current_time < t[-1] - 0.5:

        step_times.append(
            current_time
        )

        idx = min(
            int(
                current_time / dt
            ),
            N - 1
        )

        local_speed = max(
            vehicle_speed[idx],
            0.65
        )

        interval = (
            avg_event_distance
            / local_speed
        )

        interval *= rng.normal(
            loc=1.0,
            scale=0.035
        )

        interval = max(
            interval,
            0.18
        )

        current_time += interval

    step_times = np.asarray(
        step_times,
        dtype=float
    )

    step_indices = np.array(
        [
            int(
                np.searchsorted(
                    t,
                    st
                )
            )
            for st in step_times
            if np.searchsorted(
                t,
                st
            ) < N
        ],
        dtype=int
    )

    # =========================================================
    # 13. GNSS SIMULATION
    # =========================================================

    gps_dt = 1.0

    gps_t = np.arange(
        0.0,
        t[-1] + gps_dt,
        gps_dt
    )

    gps_pos_samples = np.vstack(
        [
            np.interp(
                gps_t,
                t,
                gt_pos[:, 0]
            ),
            np.interp(
                gps_t,
                t,
                gt_pos[:, 1]
            )
        ]
    ).T

    # GNSS measurement noise
    gps_noise_sigma = 1.8

    gps_pos_samples += rng.normal(
        scale=gps_noise_sigma,
        size=gps_pos_samples.shape
    )

    # =========================================================
    # 14. GNSS BLACKOUT
    # =========================================================

    gps_available_samples = np.ones(
        len(gps_t),
        dtype=bool
    )

    tunnel_mask = (
        (gps_t >= tunnel_start)
        &
        (
            gps_t
            < tunnel_start + tunnel_duration
        )
    )

    gps_available_samples[
        tunnel_mask
    ] = False

    # =========================================================
    # 15. GPS -> SENSOR TIMELINE
    # =========================================================

    gps_pos = np.full(
        (N, 2),
        np.nan
    )

    gps_available = np.zeros(
        N,
        dtype=bool
    )

    gps_indices = np.minimum(
        (t / gps_dt).astype(int),
        len(gps_t) - 1
    )

    for i in range(N):

        gi = gps_indices[i]

        if gps_available_samples[gi]:

            gps_pos[i] = (
                gps_pos_samples[gi]
            )

            gps_available[i] = True

    # =========================================================
    # 16. SMALL GNSS BIAS / DRIFT
    # =========================================================

    drift = np.column_stack(
        [
            0.006 * t,
            -0.003 * t
        ]
    )

    valid = np.isfinite(
        gps_pos[:, 0]
    )

    gps_pos[valid] += drift[valid]

    # =========================================================
    # 17. RETURN DATA
    # =========================================================

    data = {

        "t": t,

        "gt_pos": gt_pos,

        "gt_heading": gt_heading,

        "acc": acc,

        "gyro": gyro,

        "mag": mag,

        "gps_pos": gps_pos,

        "gps_available": gps_available,

        "step_times": step_times,

        "step_indices": step_indices,

        "dt": dt,

        "gt_velocity": gt_velocity,

        "gt_acceleration": gt_acceleration,

        "vehicle_speed": vehicle_speed,

        "bump_indices": bump_indices,

        "mounting_yaw_rad": mounting_yaw,

        "tunnel_start": tunnel_start,

        "tunnel_duration": tunnel_duration
    }

    return data


# =============================================================
# MAIN
# =============================================================

if __name__ == "__main__":

    print(
        "Generating vehicle-realistic synthetic simulation..."
    )

    data = simulate_rectangular_path()

    t = data["t"]

    gt_pos = data["gt_pos"]

    gps_pos = data["gps_pos"]

    gps_available = data["gps_available"]

    acc = data["acc"]

    gyro = data["gyro"]

    mag = data["mag"]

    # =========================================================
    # Save dataset
    # =========================================================

    os.makedirs(
        "data",
        exist_ok=True
    )

    out_path = os.path.join(
        "data",
        "simulated_run.npz"
    )

    np.savez(
        out_path,
        **data
    )

    print()

    print(
        "Dataset generated successfully."
    )

    print(
        f"Saved: {out_path}"
    )

    print(
        f"Samples: {len(t)}"
    )

    print(
        f"Duration: {t[-1]:.2f} seconds"
    )

    print(
        f"GNSS blackout: "
        f"{data['tunnel_start']:.1f}s - "
        f"{data['tunnel_start'] + data['tunnel_duration']:.1f}s"
    )

    print(
        f"Motion events: "
        f"{len(data['step_indices'])}"
    )

    print(
        f"Magnetometer shape: "
        f"{mag.shape}"
    )

    print(
        f"Magnetometer mean: "
        f"{np.mean(mag, axis=0)} uT"
    )

    print(
        f"Magnetometer magnitude mean: "
        f"{np.mean(np.linalg.norm(mag, axis=1)):.2f} uT"
    )

    # =========================================================
    # Plot trajectory
    # =========================================================

    plt.figure(
        figsize=(10, 7)
    )

    plt.plot(
        gt_pos[:, 0],
        gt_pos[:, 1],
        linewidth=2,
        label="Ground Truth"
    )

    valid = np.isfinite(
        gps_pos[:, 0]
    )

    plt.scatter(
        gps_pos[valid, 0],
        gps_pos[valid, 1],
        s=10,
        label="GPS Available"
    )

    blackout = ~valid

    plt.scatter(
        gt_pos[blackout, 0],
        gt_pos[blackout, 1],
        s=10,
        label="GNSS Blackout"
    )

    plt.xlabel(
        "X Position (m)"
    )

    plt.ylabel(
        "Y Position (m)"
    )

    plt.title(
        "Vehicle-like Trajectory with GNSS Blackout"
    )

    plt.axis(
        "equal"
    )

    plt.grid(
        True
    )

    plt.legend()

    plt.show()

    # =========================================================
    # Accelerometer
    # =========================================================

    plt.figure(
        figsize=(10, 4)
    )

    plt.plot(
        t,
        np.linalg.norm(
            acc,
            axis=1
        ),
        label="Accelerometer Magnitude"
    )

    plt.xlabel(
        "Time (s)"
    )

    plt.ylabel(
        "Acceleration (m/s²)"
    )

    plt.title(
        "Simulated Accelerometer"
    )

    plt.grid(
        True
    )

    plt.legend()

    plt.show()

    # =========================================================
    # Gyroscope
    # =========================================================

    plt.figure(
        figsize=(10, 4)
    )

    plt.plot(
        t,
        gyro[:, 2],
        label="Gyroscope Z"
    )

    plt.xlabel(
        "Time (s)"
    )

    plt.ylabel(
        "Angular Velocity (rad/s)"
    )

    plt.title(
        "Simulated Gyroscope"
    )

    plt.grid(
        True
    )

    plt.legend()

    plt.show()

    # =========================================================
    # Magnetometer
    # =========================================================

    plt.figure(
        figsize=(10, 4)
    )

    plt.plot(
        t,
        mag[:, 0],
        label="Magnetometer X"
    )

    plt.plot(
        t,
        mag[:, 1],
        label="Magnetometer Y"
    )

    plt.plot(
        t,
        mag[:, 2],
        label="Magnetometer Z"
    )

    plt.xlabel(
        "Time (s)"
    )

    plt.ylabel(
        "Magnetic Field (uT)"
    )

    plt.title(
        "Simulated Magnetometer"
    )

    plt.grid(
        True
    )

    plt.legend()

    plt.show()