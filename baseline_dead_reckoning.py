import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.spatial.transform import Rotation as R


def load_data(path):
    df = pd.read_csv(path)
    return df


def compute_linear_accel(df):
    # ACCEL includes gravity; GRAV_* columns provided. Use linear accel = ACCEL - GRAV
    ax = df['ACCEL_X'].values - df['GRAV_X'].values
    ay = df['ACCEL_Y'].values - df['GRAV_Y'].values
    az = df['ACCEL_Z'].values - df['GRAV_Z'].values
    return np.vstack([ax, ay, az]).T


def get_dt_array(df):
    # Derive dt from the time_s column to avoid inconsistencies in time_delta
    t = df['time_s'].values.astype(float)
    dt = np.concatenate([[0.0], np.diff(t)])
    # Replace any non-positive dt with a tiny epsilon to keep integrator stable
    dt[dt <= 0] = 1e-6
    return dt


def rotate_to_world(linear_accel, df):
    # OR_AZ (azimuth/yaw), OR_P (pitch), OR_R (roll) appear in degrees
    # Use euler sequence roll(X), pitch(Y), yaw(Z) -> 'xyz' input
    # We'll apply rotation to accel vectors to get world-frame accelerations
    yaw = df['OR_AZ'].values.astype(float)
    pitch = df['OR_P'].values.astype(float)
    roll = df['OR_R'].values.astype(float)

    acc_world = np.zeros_like(linear_accel)
    for i in range(len(linear_accel)):
        # rotation from device -> world
        try:
            rot = R.from_euler('xyz', [roll[i], pitch[i], yaw[i]], degrees=True)
            acc_world[i] = rot.apply(linear_accel[i])
        except Exception:
            # fallback: no rotation
            acc_world[i] = linear_accel[i]
    return acc_world


def integrate_dead_reckoning(acc_world, dt):
    # Remove static bias from horizontal axes to reduce drift
    acc_bias = np.median(acc_world, axis=0)
    acc_unbiased = acc_world - acc_bias

    vx = np.zeros(len(dt))
    vy = np.zeros(len(dt))
    vz = np.zeros(len(dt))
    px = np.zeros(len(dt))
    py = np.zeros(len(dt))
    pz = np.zeros(len(dt))

    for i in range(1, len(dt)):
        vx[i] = vx[i-1] + acc_unbiased[i,0] * dt[i]
        vy[i] = vy[i-1] + acc_unbiased[i,1] * dt[i]
        vz[i] = vz[i-1] + acc_unbiased[i,2] * dt[i]

        px[i] = px[i-1] + vx[i] * dt[i]
        py[i] = py[i-1] + vy[i] * dt[i]
        pz[i] = pz[i-1] + vz[i] * dt[i]

    return px, py, pz, vx, vy, vz


def build_vehicle_reference(df, dt):
    # Integrate Indicated Vehicle Speed (km/hr) using Heading (degrees) to get reference XY trajectory
    if 'Indicated Vehicle Speed (km/hr)' in df.columns and 'Heading (degrees)' in df.columns:
        v_kmh = df['Indicated Vehicle Speed (km/hr)'].values.astype(float)
        heading_deg = df['Heading (degrees)'].values.astype(float)
        v_ms = v_kmh * (1000.0/3600.0)

        ref_x = np.zeros(len(dt))
        ref_y = np.zeros(len(dt))
        for i in range(1, len(dt)):
            theta = np.deg2rad(heading_deg[i])
            ref_x[i] = ref_x[i-1] + v_ms[i] * np.cos(theta) * dt[i]
            ref_y[i] = ref_y[i-1] + v_ms[i] * np.sin(theta) * dt[i]
        return ref_x, ref_y
    else:
        # if no indicated speed, fall back to zeros
        return np.zeros(len(dt)), np.zeros(len(dt))


def evaluate(dr_x, dr_y, ref_x, ref_y):
    errs = np.sqrt((dr_x - ref_x)**2 + (dr_y - ref_y)**2)
    rmse = np.sqrt(np.mean(errs**2))
    return errs, rmse


def save_results(out_path, df, dr_x, dr_y, ref_x, ref_y, errs):
    res = pd.DataFrame({
        'time_s': df['time_s'].values,
        'dr_x_m': dr_x,
        'dr_y_m': dr_y,
        'ref_x_m': ref_x,
        'ref_y_m': ref_y,
        'pos_error_m': errs,
    })
    res.to_csv(out_path, index=False)
    return res


def plot_trajectories(dr_x, dr_y, ref_x, ref_y, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    plt.figure(figsize=(8,6))
    plt.plot(ref_x, ref_y, label='Vehicle reference', linewidth=2)
    plt.plot(dr_x, dr_y, label='Smartphone DR baseline', linewidth=1)
    plt.axis('equal')
    plt.xlabel('X (m)')
    plt.ylabel('Y (m)')
    plt.title('Trajectory: Dead Reckoning vs Vehicle Reference')
    plt.legend()
    traj_path = os.path.join(out_dir, 'baseline_dr_trajectory.png')
    plt.savefig(traj_path, bbox_inches='tight')
    plt.close()
    return traj_path


def plot_errors(time_s, errs, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    plt.figure(figsize=(8,4))
    plt.plot(time_s, errs)
    plt.xlabel('Time (s)')
    plt.ylabel('Position error (m)')
    plt.title('Dead Reckoning Position Error over Time')
    err_path = os.path.join(out_dir, 'baseline_dr_errors.png')
    plt.savefig(err_path, bbox_inches='tight')
    plt.close()
    return err_path


def main():
    repo_root = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(repo_root, 'data', 'training_dataset.csv')
    out_csv = os.path.join(repo_root, 'data', 'baseline_dr_results.csv')
    out_plots_dir = os.path.join(repo_root, 'plots')

    print('Loading data from', data_path)
    df = load_data(data_path)
    dt = get_dt_array(df)

    linear_accel = compute_linear_accel(df)
    acc_world = rotate_to_world(linear_accel, df)

    dr_x, dr_y, dr_z, vx, vy, vz = integrate_dead_reckoning(acc_world, dt)

    ref_x, ref_y = build_vehicle_reference(df, dt)

    errs, rmse = evaluate(dr_x, dr_y, ref_x, ref_y)
    print(f'Position RMSE (m): {rmse:.3f}')

    res = save_results(out_csv, df, dr_x, dr_y, ref_x, ref_y, errs)
    print('Results saved to', out_csv)

    traj_path = plot_trajectories(dr_x, dr_y, ref_x, ref_y, out_plots_dir)
    err_path = plot_errors(df['time_s'].values, errs, out_plots_dir)
    print('Saved plots to', out_plots_dir)


if __name__ == '__main__':
    main()
