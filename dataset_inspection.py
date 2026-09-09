"""
dataset_inspection.py

Small dataset inspection utility for the IO-VNBD synchronized smartphone (S) and
vehicle (V) datasets.

This script:
- Locates S-S1.csv and V-S1.csv by searching the repository tree (uses pathlib).
- Loads both CSVs with pandas.
- Prints number of rows, columns, column names, and first 3 rows for each.
- Parses smartphone timestamp (TIME SINCE START (ms)) and vehicle timestamp
  (Time Since Start of Day (seconds)). Does NOT assume they share an absolute
  reference.
- Analyzes sampling intervals (median/min/max) separately for each device.
- Checks for missing values in important IMU and vehicle columns.
- Prints min/max/mean/std for selected columns.
- Saves plots (PNG) for accelerometer, gyroscope, vehicle velocity, indicated
  vehicle speed and heading vs elapsed time.

Notes for the user (from the task):
- The script intentionally does NOT merge datasets, train models, perform
  dead-reckoning, Kalman filtering, map-matching, nor fabricate missing data.
- If the CSV paths or timestamp meanings are uncertain, the script reports the
  uncertainty rather than guessing.

Author: AI assistant using Copilot CLI runtime in VS Code
"""

from pathlib import Path
import sys
import re
import pandas as pd
import numpy as np
import matplotlib
# Use non-interactive backend so script can run without a display
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ------------------------- Helper utilities -------------------------

def find_file_by_name(root: Path, name: str):
    """Search recursively under root for a file matching name. Returns Path or None."""
    matches = list(root.rglob(name))
    return matches[0] if matches else None


def find_column(df: pd.DataFrame, patterns):
    """Find a column in df whose name matches any of the given regex patterns (case-insensitive).
    patterns: list of regex strings. Returns matched column name or None.
    """
    cols = df.columns.astype(str)
    for pat in patterns:
        cre = re.compile(pat, flags=re.I)
        for c in cols:
            if cre.search(c):
                return c
    return None


def find_columns_xyz(df: pd.DataFrame, prefix_patterns):
    """Return a dict {'x': colname, 'y': colname, 'z': colname} for columns matching prefixes and axes.
    prefix_patterns: list of regex patterns that should match the sensor name (e.g., ['accelerometer','accel']).
    """
    cols = df.columns.astype(str)
    result = {}
    for axis in ['x', 'y', 'z']:
        axis_pat = re.compile(axis, flags=re.I)
        found = None
        # Search for any column that contains one of the prefixes and the axis char
        for p in prefix_patterns:
            cre_prefix = re.compile(p, flags=re.I)
            for c in cols:
                if cre_prefix.search(c) and axis_pat.search(c):
                    found = c
                    break
            if found:
                break
        result[axis] = found
    return result


# ------------------------- Main inspection -------------------------

def main():
    start_dir = Path(__file__).resolve().parent

    # Use the exact synchronized dataset paths provided by the user.
    # These are the verified real CSV files to use for inspection.
    s_csv = Path(r"C:\Users\sivaraman\OneDrive\Desktop\SIH_2026\IO-VNBD-GIT\Synchronised V abd S datasets\Uncategorised IOVNB Dataset\S-Dataset\S-S1.csv")
    v_csv = Path(r"C:\Users\sivaraman\OneDrive\Desktop\SIH_2026\IO-VNBD-GIT\Synchronised V abd S datasets\Uncategorised IOVNB Dataset\V-Dataset\V-S1.csv")

    # If the explicit files are missing, report uncertainty and exit.
    if not s_csv.exists():
        print('UNCERTAINTY: Explicit smartphone CSV not found at', s_csv)
    if not v_csv.exists():
        print('UNCERTAINTY: Explicit vehicle CSV not found at', v_csv)
    if not s_csv.exists() or not v_csv.exists():
        print('\nExiting due to missing files.')
        return

    print(f'Found smartphone CSV: {s_csv}')
    print(f'Found vehicle CSV:    {v_csv}\n')

    # Load with pandas (do not parse dates automatically)
    try:
        # Read CSVs using cp1252 encoding to avoid UTF-8 decode errors on Windows/legacy CSVs
        df_s = pd.read_csv(s_csv, low_memory=False, encoding='cp1252')
        df_v = pd.read_csv(v_csv, low_memory=False, encoding='cp1252')
    except Exception as e:
        print('ERROR: Failed to read CSV files:', e)
        return

    # Print basic info for smartphone
    print('--- SMARTPHONE DATA (S-S1.csv) ---')
    print('Rows:', len(df_s))
    print('Columns:', len(df_s.columns))
    print('Column names:')
    for c in df_s.columns[:200]:
        print('  ', c)
    print('\nFirst 3 rows:')
    with pd.option_context('display.max_columns', None, 'display.width', 200):
        print(df_s.head(3))
    print('\n')

    # Print basic info for vehicle
    print('--- VEHICLE DATA (V-S1.csv) ---')
    print('Rows:', len(df_v))
    print('Columns:', len(df_v.columns))
    print('Column names:')
    for c in df_v.columns[:200]:
        print('  ', c)
    print('\nFirst 3 rows:')
    with pd.option_context('display.max_columns', None, 'display.width', 200):
        print(df_v.head(3))
    print('\n')

    # ------------------------- Timestamp parsing -------------------------
    # Smartphone timestamp: TIME SINCE START (ms) - find best matching column
    s_time_col = find_column(df_s, [r'time\s*since\s*start', r'time.*since.*start.*ms', r'time.*since'])
    if s_time_col is None:
        print('UNCERTAINTY: Could not identify smartphone TIME SINCE START (ms) column automatically.')
    else:
        print('Smartphone time column detected as:', s_time_col)

    # Vehicle timestamp: Time Since Start of Day (seconds)
    v_time_col = find_column(df_v, [r'time\s*since\s*start\s*of\s*day', r'time\s*since\s*start', r'sample\s*period', r'time\s*since'])
    if v_time_col is None:
        print('UNCERTAINTY: Could not identify vehicle Time Since Start of Day (seconds) column automatically.')
    else:
        print('Vehicle time column detected as:', v_time_col)

    print('\n')

    # Analyze sampling intervals separately
    # For smartphone: assume value is elapsed milliseconds from start; convert to seconds for interval analysis
    def analyze_intervals(values, units_hint='s'):
        """Compute diffs between consecutive samples. values: numeric series. units_hint for printing."""
        # Convert to float and sort by original order
        vals = pd.to_numeric(values, errors='coerce')
        # Drop NaNs for interval analysis
        vals_clean = vals.dropna()
        if len(vals_clean) < 2:
            return None
        diffs = vals_clean.diff().dropna()
        # Negative or zero diffs may indicate resets or duplicate timestamps; we keep them for min but report median robustly
        return diffs

    s_diffs = None
    if s_time_col is not None:
        s_diffs = analyze_intervals(df_s[s_time_col])
        if s_diffs is None:
            print('Not enough smartphone timestamp samples to analyze intervals.')
        else:
            # s_diffs currently in milliseconds if the column indeed is ms
            # Convert to seconds for reporting
            s_diffs_s = s_diffs.astype(float) / 1000.0
            print('Smartphone sampling intervals (assumed milliseconds -> converted to seconds):')
            print('  Median: {:.4f} s'.format(s_diffs_s.median()))
            print('  Min:    {:.4f} s'.format(s_diffs_s.min()))
            print('  Max:    {:.4f} s'.format(s_diffs_s.max()))
    else:
        print('Skipping smartphone sampling interval analysis due to unknown timestamp column.')

    v_diffs = None
    if v_time_col is not None:
        v_diffs = analyze_intervals(df_v[v_time_col])
        if v_diffs is None:
            print('Not enough vehicle timestamp samples to analyze intervals.')
        else:
            # vehicle time is described as seconds, so keep as-is
            v_diffs_s = v_diffs.astype(float)
            print('\nVehicle sampling intervals (assumed seconds):')
            print('  Median: {:.4f} s'.format(v_diffs_s.median()))
            print('  Min:    {:.4f} s'.format(v_diffs_s.min()))
            print('  Max:    {:.4f} s'.format(v_diffs_s.max()))
    else:
        print('Skipping vehicle sampling interval analysis due to unknown timestamp column.')

    print('\n')

    # ------------------------- Missing value checks -------------------------
    # Smartphone IMU columns
    accel_cols = find_columns_xyz(df_s, [r'accelerometer', r'accel', r'linear.*accel'])
    gyro_cols = find_columns_xyz(df_s, [r'gyroscope', r'gyro'])
    gravity_cols = find_columns_xyz(df_s, [r'gravity'])
    mag_cols = find_columns_xyz(df_s, [r'magnetic', r'magnetometer', r'magnet'])

    print('Missing value checks (smartphone IMU):')
    def report_missing(df, cols_dict, label):
        for axis, col in cols_dict.items():
            if col is None:
                print(f'  UNCERTAIN: {label} {axis.upper()} column not found')
            else:
                n_missing = df[col].isna().sum()
                print(f'  {label} {axis.upper()}: column "{col}" -> missing {n_missing} / {len(df)}')

    report_missing(df_s, accel_cols, 'Accelerometer')
    report_missing(df_s, gyro_cols, 'Gyroscope')
    report_missing(df_s, gravity_cols, 'Gravity')
    report_missing(df_s, mag_cols, 'Magnetic')
    print('\n')

    # Vehicle important columns
    veh_cols_to_check = {
        'Velocity': [r'velocity', r'vel\b'],
        'Heading': [r'heading', r'heading'],
        # Expand yaw matching to capture column names like 'Yaw Rate (deg/sec)'
        'Yaw Rate': [r'yaw', r'yaw\s*rate', r'yawrate'],
        'Indicated Vehicle Speed': [r'indicated.*vehicle.*speed', r'indicated\s*vehicle\s*speed', r'indicated.*speed'],
        'Indicated Longitudinal Acceleration': [r'indicated.*longitudinal', r'longitudinal.*accel', r'indicated.*longitudinal.*accel'],
        'Indicated Lateral Acceleration': [r'indicated.*lateral', r'lateral.*accel']
    }

    print('Missing value checks (vehicle):')
    found_vehicle_cols = {}
    for label, pats in veh_cols_to_check.items():
        col = find_column(df_v, pats)
        found_vehicle_cols[label] = col
        if col is None:
            print(f'  UNCERTAIN: {label} column not found')
        else:
            n_missing = df_v[col].isna().sum()
            print(f'  {label}: column "{col}" -> missing {n_missing} / {len(df_v)}')
    print('\n')

    # ------------------------- Basic statistics -------------------------
    print('Basic statistics:')
    def stats_print(series, label):
        ser = pd.to_numeric(series, errors='coerce')
        ser = ser.dropna()
        if len(ser) == 0:
            print(f'  {label}: no numeric data available')
            return
        print(f'  {label}: min={ser.min():.6g}, max={ser.max():.6g}, mean={ser.mean():.6g}, std={ser.std():.6g}, count={len(ser)}')

    # Smartphone accelerometer and gyroscope X/Y/Z
    for axis in ['x', 'y', 'z']:
        col = accel_cols.get(axis)
        stats_print(df_s[col], f'SM Accelerometer {axis.upper()}') if col else stats_print(pd.Series([], dtype=float), f'SM Accelerometer {axis.upper()}')
    for axis in ['x', 'y', 'z']:
        col = gyro_cols.get(axis)
        stats_print(df_s[col], f'SM Gyroscope {axis.upper()}') if col else stats_print(pd.Series([], dtype=float), f'SM Gyroscope {axis.upper()}')

    # Vehicle Velocity and Indicated Vehicle Speed
    vel_col = found_vehicle_cols.get('Velocity')
    ivs_col = found_vehicle_cols.get('Indicated Vehicle Speed')
    stats_print(df_v[vel_col], 'Vehicle Velocity') if vel_col else stats_print(pd.Series([], dtype=float), 'Vehicle Velocity')
    stats_print(df_v[ivs_col], 'Vehicle Indicated Vehicle Speed') if ivs_col else stats_print(pd.Series([], dtype=float), 'Vehicle Indicated Vehicle Speed')

    print('\n')

    # ------------------------- Plotting -------------------------
    plots_dir = start_dir / 'dataset_inspection_plots'
    plots_dir.mkdir(exist_ok=True)

    # Helper to compute elapsed time series in seconds for plotting
    def elapsed_seconds(series, assumed_scale='s'):
        # series: raw numeric values (ms or s). We return array of elapsed seconds from first valid sample.
        vals = pd.to_numeric(series, errors='coerce').dropna()
        if len(vals) == 0:
            return None, None
        # If assumed_scale == 'ms', convert to seconds
        if assumed_scale == 'ms':
            vals_s = vals.astype(float) / 1000.0
        else:
            vals_s = vals.astype(float)
        elapsed = vals_s - vals_s.iloc[0]
        return elapsed.values, vals_s.index

    # Smartphone plots
    if s_time_col is not None:
        s_elapsed, s_idx = elapsed_seconds(df_s[s_time_col], assumed_scale='ms')
        if s_elapsed is not None:
            # Plot accelerometer
            accel_present = any(accel_cols.values())
            if accel_present:
                plt.figure(figsize=(10, 4))
                for axis, col in accel_cols.items():
                    if col is not None:
                        y = pd.to_numeric(df_s[col], errors='coerce')
                        plt.plot((pd.to_numeric(df_s[s_time_col], errors='coerce') - pd.to_numeric(df_s[s_time_col], errors='coerce').dropna().iloc[0]) / 1000.0,
                                 y, label=f'{axis.upper()}')
                plt.xlabel('Elapsed time (s)')
                plt.ylabel('Accelerometer (m/s^2)')
                plt.title('Smartphone Accelerometer X/Y/Z vs Elapsed Time')
                plt.legend()
                plt.tight_layout()
                out = plots_dir / 'smartphone_accelerometer_xyz.png'
                plt.savefig(out)
                plt.close()
                print('Saved plot:', out)

            # Plot gyroscope
            gyro_present = any(gyro_cols.values())
            if gyro_present:
                plt.figure(figsize=(10, 4))
                for axis, col in gyro_cols.items():
                    if col is not None:
                        y = pd.to_numeric(df_s[col], errors='coerce')
                        plt.plot((pd.to_numeric(df_s[s_time_col], errors='coerce') - pd.to_numeric(df_s[s_time_col], errors='coerce').dropna().iloc[0]) / 1000.0,
                                 y, label=f'{axis.upper()}')
                plt.xlabel('Elapsed time (s)')
                plt.ylabel('Gyroscope (rad/s)')
                plt.title('Smartphone Gyroscope X/Y/Z vs Elapsed Time')
                plt.legend()
                plt.tight_layout()
                out = plots_dir / 'smartphone_gyroscope_xyz.png'
                plt.savefig(out)
                plt.close()
                print('Saved plot:', out)
        else:
            print('Could not compute smartphone elapsed time for plotting due to missing or non-numeric timestamp values.')
    else:
        print('Skipping smartphone plots due to unknown timestamp column.')

    # Vehicle plots
    if v_time_col is not None:
        v_elapsed, v_idx = elapsed_seconds(df_v[v_time_col], assumed_scale='s')
        if v_elapsed is not None:
            # Vehicle Velocity
            if vel_col:
                plt.figure(figsize=(10, 4))
                plt.plot(pd.to_numeric(df_v[v_time_col], errors='coerce') - pd.to_numeric(df_v[v_time_col], errors='coerce').dropna().iloc[0],
                         pd.to_numeric(df_v[vel_col], errors='coerce'))
                plt.xlabel('Elapsed time (s)')
                plt.ylabel('Velocity (km/hr)')
                plt.title('Vehicle Velocity vs Elapsed Time')
                plt.tight_layout()
                out = plots_dir / 'vehicle_velocity.png'
                plt.savefig(out)
                plt.close()
                print('Saved plot:', out)

            # Indicated Vehicle Speed
            if ivs_col:
                plt.figure(figsize=(10, 4))
                plt.plot(pd.to_numeric(df_v[v_time_col], errors='coerce') - pd.to_numeric(df_v[v_time_col], errors='coerce').dropna().iloc[0],
                         pd.to_numeric(df_v[ivs_col], errors='coerce'))
                plt.xlabel('Elapsed time (s)')
                plt.ylabel('Indicated Vehicle Speed (km/hr)')
                plt.title('Vehicle Indicated Vehicle Speed vs Elapsed Time')
                plt.tight_layout()
                out = plots_dir / 'vehicle_indicated_speed.png'
                plt.savefig(out)
                plt.close()
                print('Saved plot:', out)

            # Heading
            heading_col = found_vehicle_cols.get('Heading')
            if heading_col:
                plt.figure(figsize=(10, 4))
                plt.plot(pd.to_numeric(df_v[v_time_col], errors='coerce') - pd.to_numeric(df_v[v_time_col], errors='coerce').dropna().iloc[0],
                         pd.to_numeric(df_v[heading_col], errors='coerce'))
                plt.xlabel('Elapsed time (s)')
                plt.ylabel('Heading (degrees)')
                plt.title('Vehicle Heading vs Elapsed Time')
                plt.tight_layout()
                out = plots_dir / 'vehicle_heading.png'
                plt.savefig(out)
                plt.close()
                print('Saved plot:', out)

        else:
            print('Could not compute vehicle elapsed time for plotting due to missing or non-numeric timestamp values.')
    else:
        print('Skipping vehicle plots due to unknown timestamp column.')

    # ------------------------- Summary -------------------------
    print('\nDATASET INSPECTION COMPLETE')
    print('\nSummary:')
    print(f'  Smartphone CSV: {s_csv}')
    print(f'  Vehicle CSV:    {v_csv}')

    if s_diffs is not None:
        try:
            s_diffs_s = s_diffs.astype(float) / 1000.0
            print(f'  Smartphone median sample interval ~ {s_diffs_s.median():.4f} s (converted from ms)')
        except Exception:
            pass
    else:
        print('  Smartphone sampling interval: unknown')

    if v_diffs is not None:
        try:
            v_diffs_s = v_diffs.astype(float)
            print(f'  Vehicle median sample interval ~ {v_diffs_s.median():.4f} s')
        except Exception:
            pass
    else:
        print('  Vehicle sampling interval: unknown')

    print('  Plots saved to:', plots_dir)
    print('\nNotes:')
    print('  - The script tried to identify timestamp and sensor columns automatically. If column names in the CSV differ from expected names, some checks may be reported as "UNCERTAIN".')
    print('  - No merging, modeling, filtering, or fabrication of missing data was performed.')


if __name__ == '__main__':
    main()
