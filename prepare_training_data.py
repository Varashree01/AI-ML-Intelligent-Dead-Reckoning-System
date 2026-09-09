"""
prepare_training_data.py

Prepare ML-ready training dataset by aligning smartphone sensor data (S-S1.csv)
with vehicle ground-truth (V-S1.csv) using timestamp-based interpolation.

Instructions from user followed exactly:
- Use the two explicit synchronized CSV files (paths hard-coded below).
- Read with pandas using encoding='cp1252'.
- Do not modify original CSVs.
- Do not guess arbitrary time offsets.
- Use timestamp-based alignment and report diagnostics.

Outputs:
- data/training_dataset.csv
- diagnostic plots in dataset_inspection_plots/

Author: AI assistant using Copilot CLI runtime in VS Code
"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sys

# ------------------------- Configuration (explicit paths) -------------------------
S_CSV = Path(r"C:\Users\sivaraman\OneDrive\Desktop\SIH_2026\IO-VNBD-GIT\Synchronised V abd S datasets\Uncategorised IOVNB Dataset\S-Dataset\S-S1.csv")
V_CSV = Path(r"C:\Users\sivaraman\OneDrive\Desktop\SIH_2026\IO-VNBD-GIT\Synchronised V abd S datasets\Uncategorised IOVNB Dataset\V-Dataset\V-S1.csv")

OUT_DIR = Path('data')
OUT_DIR.mkdir(exist_ok=True)
OUT_CSV = OUT_DIR / 'training_dataset.csv'
PLOTS_DIR = Path('dataset_inspection_plots')
PLOTS_DIR.mkdir(exist_ok=True)

# ------------------------- Helper functions -------------------------

def read_csv_strip(path: Path):
    """Read CSV with cp1252 encoding and strip whitespace from column names."""
    df = pd.read_csv(path, encoding='cp1252', low_memory=False)
    # Strip column names
    df.columns = df.columns.astype(str).str.strip()
    return df


def median_interval_seconds(times):
    """Compute median sampling interval in seconds from an array/series of times in seconds."""
    t = pd.to_numeric(times, errors='coerce').dropna()
    if len(t) < 2:
        return None
    diffs = t.diff().dropna()
    return float(diffs.median()), float(diffs.min()), float(diffs.max())


# ------------------------- Main processing -------------------------

def main():
    # Check files exist
    if not S_CSV.exists():
        print('ERROR: Smartphone CSV not found at', S_CSV)
        return
    if not V_CSV.exists():
        print('ERROR: Vehicle CSV not found at', V_CSV)
        return

    # Read CSVs
    try:
        df_s = read_csv_strip(S_CSV)
        df_v = read_csv_strip(V_CSV)
    except Exception as e:
        print('ERROR: Failed to read CSVs:', e)
        return

    # Detect timestamp columns (use exact names expected)
    # Use stripped names
    s_time_col = 'TIME SINCE START (ms)'
    v_time_col = 'Time Since Start of Day (seconds)'

    if s_time_col not in df_s.columns:
        print('ERROR: Expected smartphone time column not found:', s_time_col)
        print('Available columns:', list(df_s.columns[:20]))
        return
    if v_time_col not in df_v.columns:
        print('ERROR: Expected vehicle time column not found:', v_time_col)
        print('Available columns:', list(df_v.columns[:20]))
        return

    # Convert smartphone time from ms to elapsed seconds starting at zero
    df_s['_time_s'] = pd.to_numeric(df_s[s_time_col], errors='coerce') / 1000.0
    if df_s['_time_s'].isna().all():
        print('ERROR: Smartphone time column could not be converted to numeric.')
        return
    df_s['_time_s'] = df_s['_time_s'] - df_s['_time_s'].dropna().iloc[0]

    # Convert vehicle time to elapsed seconds starting at zero
    df_v['_time_s'] = pd.to_numeric(df_v[v_time_col], errors='coerce')
    if df_v['_time_s'].isna().all():
        print('ERROR: Vehicle time column could not be converted to numeric.')
        return
    df_v['_time_s'] = df_v['_time_s'] - df_v['_time_s'].dropna().iloc[0]

    # Basic counts and ranges
    s_count = len(df_s)
    v_count = len(df_v)
    s_range = (float(df_s['_time_s'].min()), float(df_s['_time_s'].max()))
    v_range = (float(df_v['_time_s'].min()), float(df_v['_time_s'].max()))

    s_median, s_min_i, s_max_i = median_interval_seconds(df_s['_time_s'])
    v_median, v_min_i, v_max_i = median_interval_seconds(df_v['_time_s'])

    # Report basic info
    print('Smartphone row count:', s_count)
    print('Vehicle row count:', v_count)
    print(f'Smartphone time range (s): {s_range[0]:.3f} -> {s_range[1]:.3f}')
    print(f'Vehicle time range (s):    {v_range[0]:.3f} -> {v_range[1]:.3f}')
    if s_median is not None:
        print(f'Smartphone median sampling interval: {s_median:.6f} s (min {s_min_i:.6f}, max {s_max_i:.6f})')
    else:
        print('Smartphone sampling interval: not available')
    if v_median is not None:
        print(f'Vehicle median sampling interval: {v_median:.6f} s (min {v_min_i:.6f}, max {v_max_i:.6f})')
    else:
        print('Vehicle sampling interval: not available')

    # Determine overlap range (no arbitrary offset) — use elapsed times as provided
    overlap_start = max(s_range[0], v_range[0])
    overlap_end = min(s_range[1], v_range[1])
    if overlap_end <= overlap_start:
        print('ERROR: No overlapping elapsed time range between smartphone and vehicle after converting to elapsed seconds.')
        print('Smartphone range:', s_range)
        print('Vehicle range:', v_range)
        return

    print(f'Overlap time range (s): {overlap_start:.3f} -> {overlap_end:.3f}')

    # Select smartphone rows within overlap (these will be the reference times for alignment)
    mask_s_overlap = (df_s['_time_s'] >= overlap_start) & (df_s['_time_s'] <= overlap_end)
    df_s_ov = df_s.loc[mask_s_overlap].copy().reset_index(drop=True)

    # Interpolate vehicle ground-truth onto smartphone elapsed times (within overlap)
    # Define vehicle target columns (must match stripped column names)
    veh_targets = [
        'Velocity (km/hr)',
        'Heading (degrees)',
        'Yaw Rate (deg/sec)',
        'Indicated Vehicle Speed (km/hr)',
        'Indicated Longitudinal Acceleration (g)',
        'Indicated Lateral Acceleration (g)'
    ]

    # Check vehicle columns exist
    missing_targets = [c for c in veh_targets if c not in df_v.columns]
    if missing_targets:
        print('ERROR: Missing expected vehicle target columns:', missing_targets)
        return

    # Prepare interpolation functions using numpy.interp (requires sorted x and finite y)
    v_time = pd.to_numeric(df_v['_time_s'], errors='coerce')

    aligned_rows = 0
    # Create a dict to hold interpolated target arrays
    interp_targets = {}
    for col in veh_targets:
        y = pd.to_numeric(df_v[col], errors='coerce')
        valid = y.notna() & v_time.notna()
        if valid.sum() < 2:
            # Not enough points to interpolate
            interp_targets[col] = np.full(len(df_s_ov), np.nan)
            continue
        x_valid = v_time[valid].values
        y_valid = y[valid].values
        # Ensure monotonic increasing x for interp (should be), but enforce sorting
        order = np.argsort(x_valid)
        x_valid = x_valid[order]
        y_valid = y_valid[order]
        # Interpolate onto smartphone times within overlap
        xi = df_s_ov['_time_s'].values
        yi = np.interp(xi, x_valid, y_valid, left=np.nan, right=np.nan)
        interp_targets[col] = yi

    # Smartphone input features — expected columns
    sm_inputs = [
        'ACCELEROMETER X (m/s^2)',
        'ACCELEROMETER Y (m/s^2)',
        'ACCELEROMETER Z (m/s^2)',
        'GYROSCOPE X (rad/s)',
        'GYROSCOPE Y (rad/s)',
        'GYROSCOPE Z (rad/s)',
        'GRAVITY X (m/s^2)',
        'GRAVITY Y (m/s^2)',
        'GRAVITY Z (m/s^2)',
        'MAGNETIC FIELD X (μT)',
        'MAGNETIC FIELD Y (μT)',
        'MAGNETIC FIELD Z (μT)',
        'ORIENTATION (Azimuth) (°)',
        'ORIENTATION (Pitch) (°)',
        'ORIENTATION (Roll ) (°)'
    ]

    # The original CSV used slightly different characters for meters/sec^2 (some non-ascii); attempt flexible matching
    # Build mapping from expected simplified names to actual columns by searching
    def find_col(df_cols, patterns):
        import re
        for pat in patterns:
            cre = re.compile(pat, flags=re.I)
            for c in df_cols:
                if cre.search(c):
                    return c
        return None

    # Build actual smartphone columns by matching patterns
    sm_col_map = {}
    sm_col_map['ACCEL_X'] = find_col(df_s_ov.columns, [r'accelerometer\s*x', r'accel\s*x'])
    sm_col_map['ACCEL_Y'] = find_col(df_s_ov.columns, [r'accelerometer\s*y', r'accel\s*y'])
    sm_col_map['ACCEL_Z'] = find_col(df_s_ov.columns, [r'accelerometer\s*z', r'accel\s*z'])
    sm_col_map['GYRO_X'] = find_col(df_s_ov.columns, [r'gyroscope\s*x', r'gyro\s*x'])
    sm_col_map['GYRO_Y'] = find_col(df_s_ov.columns, [r'gyroscope\s*y', r'gyro\s*y'])
    sm_col_map['GYRO_Z'] = find_col(df_s_ov.columns, [r'gyroscope\s*z', r'gyro\s*z'])
    sm_col_map['GRAV_X'] = find_col(df_s_ov.columns, [r'gravity\s*x'])
    sm_col_map['GRAV_Y'] = find_col(df_s_ov.columns, [r'gravity\s*y'])
    sm_col_map['GRAV_Z'] = find_col(df_s_ov.columns, [r'gravity\s*z'])
    sm_col_map['MAG_X'] = find_col(df_s_ov.columns, [r'magnetic.*x', r'magnet.*x'])
    sm_col_map['MAG_Y'] = find_col(df_s_ov.columns, [r'magnetic.*y', r'magnet.*y'])
    sm_col_map['MAG_Z'] = find_col(df_s_ov.columns, [r'magnetic.*z', r'magnet.*z'])
    sm_col_map['OR_AZ'] = find_col(df_s_ov.columns, [r'orientation.*azimuth', r'azimuth'])
    sm_col_map['OR_P'] = find_col(df_s_ov.columns, [r'orientation.*pitch', r'pitch'])
    sm_col_map['OR_R'] = find_col(df_s_ov.columns, [r'orientation.*roll', r'roll'])

    # Report any missing smartphone columns (uncertainties) but continue
    missing_sm = [k for k, v in sm_col_map.items() if v is None]
    if missing_sm:
        print('WARNING: Could not find some smartphone columns automatically:', missing_sm)

    # Build aligned DataFrame
    aligned = pd.DataFrame()
    aligned['time_s'] = df_s_ov['_time_s'].values

    # Add smartphone features (as numeric)
    for key, col in sm_col_map.items():
        if col is None:
            aligned[key] = np.nan
        else:
            aligned[key] = pd.to_numeric(df_s_ov[col], errors='coerce').values

    # Derived smartphone features
    aligned['accel_mag'] = np.sqrt(
        np.nan_to_num(aligned.get('ACCEL_X', np.nan))**2 +
        np.nan_to_num(aligned.get('ACCEL_Y', np.nan))**2 +
        np.nan_to_num(aligned.get('ACCEL_Z', np.nan))**2
    )
    aligned['gyro_mag'] = np.sqrt(
        np.nan_to_num(aligned.get('GYRO_X', np.nan))**2 +
        np.nan_to_num(aligned.get('GYRO_Y', np.nan))**2 +
        np.nan_to_num(aligned.get('GYRO_Z', np.nan))**2
    )
    # time delta (difference between consecutive smartphone samples); first row 0
    time_vals = aligned['time_s'].values
    td = np.empty_like(time_vals)
    td[0] = 0.0
    td[1:] = np.diff(time_vals)
    aligned['time_delta'] = td

    # Add interpolated vehicle targets
    for col in veh_targets:
        aligned[col] = interp_targets.get(col, np.full(len(aligned), np.nan))

    # Determine aligned rows: keep rows where all target columns are finite
    target_cols = veh_targets
    finite_mask = np.ones(len(aligned), dtype=bool)
    for c in target_cols:
        finite_mask &= np.isfinite(aligned[c].values)

    n_initial = len(aligned)
    n_aligned = int(finite_mask.sum())
    # Rows dropped due to missing targets
    n_dropped = n_initial - n_aligned

    # Create final_df by dropping rows with missing target values (do not fill)
    final_df = aligned.loc[finite_mask].reset_index(drop=True)

    # Count missing values after alignment
    n_missing_after = int(final_df.isna().sum().sum())

    # Final number of columns
    final_cols = final_df.shape[1]

    # Save training CSV
    try:
        final_df.to_csv(OUT_CSV, index=False, encoding='cp1252')
        saved = True
    except Exception as e:
        print('ERROR: Failed to save training CSV:', e)
        saved = False

    # Diagnostic plots
    # 1. Smartphone elapsed time vs vehicle elapsed time (scatter of time_s vs interpolated vehicle time)
    # Since we aligned vehicle onto smartphone times, compute interpolated vehicle elapsed times by linear mapping
    # For a synchronized dataset where both elapsed starts correspond, this should be near y = x.
    # Use vehicle original times interpolated onto smartphone times (we can compute vehicle elapsed at smartphone times by interpolating v_time itself)
    try:
        v_time_valid = v_time[~v_time.isna()].values
        if len(v_time_valid) >= 2:
            # interpolate vehicle elapsed time onto smartphone times
            vehicle_time_at_s = np.interp(final_df['time_s'].values, v_time[~v_time.isna()].values, v_time[~v_time.isna()].values, left=np.nan, right=np.nan)
            plt.figure(figsize=(6, 4))
            plt.scatter(final_df['time_s'].values, vehicle_time_at_s, s=2)
            plt.xlabel('Smartphone elapsed time (s)')
            plt.ylabel('Vehicle elapsed time (s)')
            plt.title('Smartphone elapsed time vs Vehicle elapsed time')
            plt.tight_layout()
            plt.savefig(PLOTS_DIR / 'time_vs_time.png')
            plt.close()
        else:
            print('WARNING: Not enough vehicle time points to create time-vs-time diagnostic plot.')
    except Exception as e:
        print('WARNING: Failed to create time-vs-time plot:', e)

    # 2. Ground-truth vehicle speed vs time (vehicle original)
    try:
        plt.figure(figsize=(10, 4))
        plt.plot(df_v['_time_s'].values, pd.to_numeric(df_v['Velocity (km/hr)'], errors='coerce').values)
        plt.xlabel('Vehicle elapsed time (s)')
        plt.ylabel('Velocity (km/hr)')
        plt.title('Vehicle Velocity vs Elapsed Time')
        plt.tight_layout()
        plt.savefig(PLOTS_DIR / 'vehicle_speed_vs_time.png')
        plt.close()
    except Exception as e:
        print('WARNING: Failed to create vehicle speed plot:', e)

    # Print summary
    print('\nSUMMARY:')
    print('  Initial smartphone rows:', s_count)
    print('  Initial vehicle rows:   ', v_count)
    print(f'  Smartphone time range: {s_range[0]:.3f} -> {s_range[1]:.3f} (s)')
    print(f'  Vehicle time range:    {v_range[0]:.3f} -> {v_range[1]:.3f} (s)')
    if s_median:
        print(f'  Smartphone median interval: {s_median:.6f} s')
    if v_median:
        print(f'  Vehicle median interval:    {v_median:.6f} s')
    print(f'  Overlap time: {overlap_start:.3f} -> {overlap_end:.3f} (s)')
    print(f'  Rows in overlap (smartphone): {len(df_s_ov)}')
    print(f'  Number of successfully aligned rows: {n_aligned}')
    print(f'  Number of dropped rows due to missing targets: {n_dropped}')
    print(f'  Number of missing values after alignment (in kept rows): {n_missing_after}')
    print(f'  Final number of columns in training dataset: {final_cols}')
    print('  Training CSV saved to:', OUT_CSV if saved else 'NOT SAVED')

    # Give brief assessment of reliability
    # Basic heuristic: if a large fraction (>80%) of smartphone overlap rows have finite targets, consider reliable
    reliability = None
    if len(df_s_ov) > 0:
        frac = n_aligned / len(df_s_ov)
        if frac >= 0.8:
            reliability = 'Likely reliable (>=80% aligned)'
        elif frac >= 0.5:
            reliability = 'Partially reliable (50-80% aligned)'
        else:
            reliability = 'Not reliable (<50% aligned)'
        print('  Alignment assessment:', reliability)


if __name__ == '__main__':
    main()
