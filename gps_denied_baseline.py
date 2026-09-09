import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from math import cos, sin, radians
from scipy.spatial.transform import Rotation as R

# Config
S_PATH = r"C:\Users\sivaraman\OneDrive\Desktop\SIH_2026\IO-VNBD-GIT\Synchronised V abd S datasets\Uncategorised IOVNB Dataset\S-Dataset\S-S1.csv"
V_PATH = r"C:\Users\sivaraman\OneDrive\Desktop\SIH_2026\IO-VNBD-GIT\Synchronised V abd S datasets\Uncategorised IOVNB Dataset\V-Dataset\V-S1.csv"
ENCODING = 'cp1252'
OUTAGE_START = 60.0  # seconds
OUTAGE_DURATION = 60.0  # seconds
OUT_CSV = os.path.join('data', 'gps_denied_baseline_results.csv')
OUT_PLOTS_DIR = os.path.join('data', 'gps_denied_plots')

R_EARTH = 6378137.0


def find_col(cols, keywords):
    cols_l = [c.lower() for c in cols]
    for kw in keywords:
        kw_l = kw.lower()
        for i, c in enumerate(cols_l):
            if kw_l in c:
                return cols[i]
    return None


def latlon_to_enu(lat, lon, lat0, lon0):
    # simple equirectangular approx
    lat = np.asarray(lat, dtype=float)
    lon = np.asarray(lon, dtype=float)
    dlat = np.deg2rad(lat - lat0)
    dlon = np.deg2rad(lon - lon0)
    x = dlon * np.cos(np.deg2rad(lat0)) * R_EARTH
    y = dlat * R_EARTH
    return x, y


def load_and_inspect():
    s = pd.read_csv(S_PATH, encoding=ENCODING)
    v = pd.read_csv(V_PATH, encoding=ENCODING)
    print('S columns:', list(s.columns))
    print('V columns:', list(v.columns))
    return s, v


def main():
    os.makedirs(OUT_PLOTS_DIR, exist_ok=True)

    print('Loading and inspecting CSVs...')
    s, v = load_and_inspect()

    # find columns robustly
    s_cols = s.columns.tolist()
    v_cols = v.columns.tolist()

    s_lat_col = find_col(s_cols, ['gps latitude', 'latitude'])
    s_lon_col = find_col(s_cols, ['gps longitude', 'longitude'])
    s_time_col = find_col(s_cols, ['time since start'])
    s_accel_x = find_col(s_cols, ['accelerometer x', 'accel'])
    s_accel_y = find_col(s_cols, ['accelerometer y'])
    s_accel_z = find_col(s_cols, ['accelerometer z'])
    s_grav_x = find_col(s_cols, ['gravity x'])
    s_grav_y = find_col(s_cols, ['gravity y'])
    s_grav_z = find_col(s_cols, ['gravity z'])
    s_or_az = find_col(s_cols, ['orientation (azimuth)', 'orientation (azimuth) (°)', 'orientation (azimuth)'])
    s_or_p = find_col(s_cols, ['orientation (pitch)', 'orientation (pitch) (°)'])
    s_or_r = find_col(s_cols, ['orientation (roll', 'orientation (roll )'])

    v_lat_col = find_col(v_cols, ['latitude'])
    v_lon_col = find_col(v_cols, ['longitude'])
    v_time_col = find_col(v_cols, ['time since start', 'time since start of day'])
    v_heading_col = find_col(v_cols, ['heading'])
    v_speed_col = find_col(v_cols, ['indicated vehicle speed', 'indicated vehicle speed (km/hr)', 'velocity (km/hr)', 'velocity'])

    # Basic checks
    if None in [s_lat_col, s_lon_col, s_time_col, s_accel_x, s_accel_y, s_accel_z, s_grav_x, s_grav_y, s_grav_z]:
        raise RuntimeError('Could not find necessary smartphone columns; see printed column names')
    if None in [v_lat_col, v_lon_col, v_time_col]:
        raise RuntimeError('Could not find necessary vehicle columns; see printed column names')

    # Prepare time arrays
    # S: time in ms according to header
    s_time = s[s_time_col].astype(float).values
    # convert to seconds relative to first sample
    s_time = (s_time - s_time[0]) / 1000.0

    v_time = v[v_time_col].astype(float).values
    # make relative to first sample
    v_time = v_time - v_time[0]

    # Interpolate vehicle GPS to smartphone timestamps (common timeline)
    v_lat = v[v_lat_col].astype(float).values
    v_lon = v[v_lon_col].astype(float).values

    lat0 = v_lat[0]
    lon0 = v_lon[0]

    v_lat_interp = np.interp(s_time, v_time, v_lat)
    v_lon_interp = np.interp(s_time, v_time, v_lon)

    gps_x, gps_y = latlon_to_enu(v_lat_interp, v_lon_interp, lat0, lon0)

    # GPS available mask
    outage_start = OUTAGE_START
    outage_end = OUTAGE_START + OUTAGE_DURATION
    gps_available = np.logical_or(s_time < outage_start, s_time >= outage_end)

    # Build reference trajectory (vehicle GPS in ENU) already as gps_x/gps_y

    # DR: use smartphone sensors
    acc_x = s[s_accel_x].astype(float).values
    acc_y = s[s_accel_y].astype(float).values
    acc_z = s[s_accel_z].astype(float).values

    grav_x = s[s_grav_x].astype(float).values
    grav_y = s[s_grav_y].astype(float).values
    grav_z = s[s_grav_z].astype(float).values

    lin_ax = acc_x - grav_x
    lin_ay = acc_y - grav_y
    lin_az = acc_z - grav_z

    # Orientation angles (degrees)
    or_az = None
    or_p = None
    or_r = None
    if s_or_az is not None:
        or_az = s[s_or_az].astype(float).values
    if s_or_p is not None:
        or_p = s[s_or_p].astype(float).values
    if s_or_r is not None:
        or_r = s[s_or_r].astype(float).values

    # Estimate phone-to-vehicle yaw offset using period immediately before outage (last 5 seconds)
    pre_window_start = max(0.0, outage_start - 5.0)
    pre_mask = np.logical_and(s_time >= pre_window_start, s_time < outage_start)

    # vehicle heading at those times (interpolate)
    if v_heading_col is not None:
        v_heading = v[v_heading_col].astype(float).values
        v_heading_interp = np.interp(s_time, v_time, v_heading)
    else:
        v_heading_interp = np.zeros_like(s_time)

    phone_yaw = or_az if or_az is not None else None
    if phone_yaw is None:
        # fallback: use gyro Z to integrate yaw (rad/s -> deg)
        print('Phone azimuth missing; integrating gyro z to estimate yaw')
        gyro_z_col = find_col(s_cols, ['gyroscope z', 'gyro z'])
        if gyro_z_col is None:
            raise RuntimeError('No phone yaw information available')
        gyro_z = s[gyro_z_col].astype(float).values
        # integrate rad/s -> degrees
        phone_yaw = np.cumsum(gyro_z) * np.mean(np.diff(s_time)) * (180.0/np.pi)

    # compute median offset (vehicle - phone) over pre-mask
    if np.any(pre_mask):
        offset_vals = (v_heading_interp[pre_mask] - phone_yaw[pre_mask])
        # wrap to [-180,180]
        offset_vals = (offset_vals + 180) % 360 - 180
        yaw_offset = np.median(offset_vals)
    else:
        yaw_offset = 0.0
    print(f'Using yaw offset (vehicle - phone) = {yaw_offset:.3f} deg')

    # Adjust phone yaw by offset to estimate vehicle heading from phone
    est_heading = (phone_yaw + yaw_offset) % 360

    # Prepare integration arrays
    n = len(s_time)
    dt = np.concatenate([[0.0], np.diff(s_time)])

    dr_x = np.zeros(n)
    dr_y = np.zeros(n)
    dr_vx = np.zeros(n)
    dr_vy = np.zeros(n)

    # initialize at outage start using GPS
    # find index closest to outage_start
    idx_start = np.argmin(np.abs(s_time - outage_start))
    idx_end = np.argmin(np.abs(s_time - outage_end))

    # initial GPS position at outage start
    init_gps_x = gps_x[idx_start]
    init_gps_y = gps_y[idx_start]

    # initial vehicle speed and heading from vehicle data at that time
    v_speed = None
    if v_speed_col is not None:
        v_speed_full = v[v_speed_col].astype(float).values
        v_speed_interp = np.interp(s_time, v_time, v_speed_full)
        init_speed_kmh = v_speed_interp[idx_start]
    else:
        init_speed_kmh = 0.0
    init_speed_ms = init_speed_kmh * (1000.0/3600.0)

    init_heading = v_heading_interp[idx_start] if v_heading_col is not None else est_heading[idx_start]

    # initialize DR at outage start
    dr_x[idx_start] = init_gps_x
    dr_y[idx_start] = init_gps_y
    dr_vx[idx_start] = init_speed_ms * cos(radians(init_heading))
    dr_vy[idx_start] = init_speed_ms * sin(radians(init_heading))

    # Integrate through outage using phone sensors only
    for i in range(idx_start+1, idx_end+1):
        # rotate phone linear accel into ENU world frame using full phone orientation (roll,pitch,yaw)
        # Apply phone->vehicle yaw offset to align phone yaw with vehicle heading
        roll_i = or_r[i] if or_r is not None else 0.0
        pitch_i = or_p[i] if or_p is not None else 0.0
        # phone_yaw may be the raw phone azimuth (in degrees). Use it and add yaw_offset to align with vehicle frame
        yaw_i = phone_yaw[i] + yaw_offset
        try:
            # Rotation from phone frame to world frame
            rot = R.from_euler('xyz', [roll_i, pitch_i, yaw_i], degrees=True)
            acc_world_vec = rot.apply([lin_ax[i], lin_ay[i], lin_az[i]])
            ax_world = acc_world_vec[0]
            ay_world = acc_world_vec[1]
        except Exception:
            # fallback to previous yaw-only horizontal rotation
            yaw = radians(est_heading[i])
            ax_phone = lin_ax[i]
            ay_phone = lin_ay[i]
            ax_world = ax_phone * cos(yaw) - ay_phone * sin(yaw)
            ay_world = ax_phone * sin(yaw) + ay_phone * cos(yaw)

        dr_vx[i] = dr_vx[i-1] + ax_world * dt[i]
        dr_vy[i] = dr_vy[i-1] + ay_world * dt[i]

        dr_x[i] = dr_x[i-1] + dr_vx[i] * dt[i]
        dr_y[i] = dr_y[i-1] + dr_vy[i] * dt[i]

    # For times before outage, set DR to GPS (we are allowed to use GPS when available)
    for i in range(0, idx_start):
        dr_x[i] = gps_x[i]
        dr_y[i] = gps_y[i]
        # estimate speed from vehicle
    for i in range(idx_end+1, n):
        # after outage, allow GPS available => DR = GPS for evaluation purposes
        dr_x[i] = gps_x[i]
        dr_y[i] = gps_y[i]

    # Compute errors
    pos_err = np.sqrt((dr_x - gps_x)**2 + (dr_y - gps_y)**2)

    # Metrics during outage window
    outage_mask = np.logical_and(s_time >= outage_start, s_time < outage_end)
    if not np.any(outage_mask):
        raise RuntimeError('No samples in outage window; check OUTAGE_START/OUTAGE_DURATION and timestamps')

    rmse = np.sqrt(np.mean(pos_err[outage_mask]**2))
    mean_err = np.mean(pos_err[outage_mask])
    max_err = np.max(pos_err[outage_mask])
    final_err = pos_err[idx_end]
    drift_rate = final_err / OUTAGE_DURATION

    # Save CSV
    df_out = pd.DataFrame({
        'time_s': s_time,
        'gps_x': gps_x,
        'gps_y': gps_y,
        'dr_x': dr_x,
        'dr_y': dr_y,
        'gps_available': gps_available,
        'estimated_heading': est_heading,
        'estimated_speed': np.sqrt(dr_vx**2 + dr_vy**2),
        'position_error': pos_err,
    })
    df_out.to_csv(OUT_CSV, index=False)
    print('Saved results to', OUT_CSV)

    # Plots
    plt.figure(figsize=(8,6))
    plt.plot(gps_x, gps_y, label='GPS reference', linewidth=2)
    plt.plot(dr_x, dr_y, label='DR estimate', linewidth=1)
    # shade outage region
    plt.axvspan(gps_x[idx_start], gps_x[idx_end] if idx_end < len(gps_x) else gps_x[-1], color='orange', alpha=0.2, label='GPS outage region (approx X span)')
    plt.xlabel('East (m)')
    plt.ylabel('North (m)')
    plt.title('Trajectory: GPS vs DR')
    plt.legend()
    traj_path = os.path.join(OUT_PLOTS_DIR, 'gps_denied_trajectory.png')
    plt.savefig(traj_path, bbox_inches='tight')
    plt.close()

    plt.figure(figsize=(8,4))
    plt.plot(s_time, pos_err)
    plt.axvspan(outage_start, outage_end, color='orange', alpha=0.2)
    plt.xlabel('Time (s)')
    plt.ylabel('Position error (m)')
    plt.title('Position error over time')
    err_path = os.path.join(OUT_PLOTS_DIR, 'gps_denied_error.png')
    plt.savefig(err_path, bbox_inches='tight')
    plt.close()

    plt.figure(figsize=(8,4))
    plt.plot(s_time, est_heading)
    plt.axvspan(outage_start, outage_end, color='orange', alpha=0.2)
    plt.xlabel('Time (s)')
    plt.ylabel('Estimated heading (deg)')
    plt.title('Estimated heading')
    head_path = os.path.join(OUT_PLOTS_DIR, 'gps_denied_heading.png')
    plt.savefig(head_path, bbox_inches='tight')
    plt.close()

    plt.figure(figsize=(8,4))
    plt.plot(s_time, np.sqrt(dr_vx**2 + dr_vy**2), label='DR speed')
    plt.axvspan(outage_start, outage_end, color='orange', alpha=0.2)
    plt.xlabel('Time (s)')
    plt.ylabel('Speed (m/s)')
    plt.title('Estimated speed')
    speed_path = os.path.join(OUT_PLOTS_DIR, 'gps_denied_speed.png')
    plt.savefig(speed_path, bbox_inches='tight')
    plt.close()

    # Print summary
    print('\nGPS-DENIED BASELINE RESULTS')
    print('--------------------------------')
    print(f'GPS outage: start={OUTAGE_START}s, duration={OUTAGE_DURATION}s')
    print(f'Initial GPS position: x={init_gps_x:.3f} m, y={init_gps_y:.3f} m')
    print(f'Initial GPS speed: {init_speed_kmh:.3f} km/h ({init_speed_ms:.3f} m/s)')
    print(f'Initial GPS heading: {init_heading:.3f} deg')
    print('')
    print(f'RMSE position error (during outage): {rmse:.3f} m')
    print(f'Mean position error (during outage): {mean_err:.3f} m')
    print(f'Max position error (during outage): {max_err:.3f} m')
    print(f'Final position error (at outage end): {final_err:.3f} m')
    print(f'Drift rate: {drift_rate:.6f} m/s')

    print('\nOutput files:')
    print('Results CSV:', os.path.abspath(OUT_CSV))
    print('Trajectory plot:', os.path.abspath(traj_path))
    print('Error plot:', os.path.abspath(err_path))
    print('Heading plot:', os.path.abspath(head_path))
    print('Speed plot:', os.path.abspath(speed_path))


if __name__ == '__main__':
    main()
