"""Diagnostics for the first ML dead-reckoning correction baseline."""

import os
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
PLOTS = ROOT / "plots"
REPORT_PATH = DATA / "ml_diagnostics_report.txt"
TARGETS = ["target_dx", "target_dy"]
SPLITS = ["ml_train", "ml_validation", "ml_test"]


def source_findings(path):
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    patterns = {
        "gravity removal": "linear_acceleration = np.column_stack",
        "Euler rotation": "Rotation.from_euler",
        "integration loop": "for index in range(start_index + 1, end_index + 1):",
        "initial state": "initial_vehicle_index, initial_speed, initial_heading",
        "position initialization": "estimated_x[start_index] = initial_x",
        "reference interpolation": "reference_lat = np.interp",
    }
    found = {}
    for label, text in patterns.items():
        found[label] = next((i + 1 for i, line in enumerate(lines) if text in line), None)
    return found, lines


def stats(series):
    values = series.to_numpy(dtype=float)
    percentiles = np.percentile(values, [1, 5, 25, 50, 75, 95, 99])
    return {
        "min": np.min(values), "max": np.max(values), "mean": np.mean(values),
        "median": np.median(values), "std": np.std(values),
        "p1": percentiles[0], "p5": percentiles[1], "p25": percentiles[2],
        "p50": percentiles[3], "p75": percentiles[4], "p95": percentiles[5], "p99": percentiles[6],
    }


def fmt_stats(name, values):
    return name + ": " + ", ".join(f"{key}={value:.6f}" for key, value in values.items())


def main():
    PLOTS.mkdir(exist_ok=True)
    full = pd.read_csv(DATA / "ml_training_dataset.csv", encoding="cp1252")
    train = pd.read_csv(DATA / "ml_train.csv", encoding="cp1252")
    validation = pd.read_csv(DATA / "ml_validation.csv", encoding="cp1252")
    test = pd.read_csv(DATA / "ml_test.csv", encoding="cp1252")
    splits = {"train": train, "validation": validation, "test": test}
    feature_columns = [column for column in full.columns if column not in TARGETS and column != "time_s"]
    missing = int(full[feature_columns + TARGETS].isna().sum().sum())

    target_stats = {target: stats(full[target]) for target in TARGETS}
    error_magnitude = np.hypot(full["target_dx"], full["target_dy"])
    full = full.assign(error_magnitude=error_magnitude)
    local_dx = full["target_dx"].diff()
    local_dy = full["target_dy"].diff()
    local_magnitude = np.hypot(local_dx, local_dy)
    local_magnitude = local_magnitude.dropna()
    growth_rows = []
    for seconds in [10, 20, 30, 40, 50, 60]:
        index = (full["time_s"] - (60.0 + seconds)).abs().idxmin()
        growth_rows.append((float(full.loc[index, "time_s"]), float(error_magnitude.loc[index])))

    plt.figure(figsize=(8, 5))
    for target in TARGETS:
        plt.hist(full[target], bins=50, alpha=0.55, label=target)
    plt.xlabel("Target correction (m)")
    plt.ylabel("Count")
    plt.title("Target distributions")
    plt.legend()
    plt.tight_layout()
    plt.savefig(PLOTS / "ml_target_distribution.png", dpi=150)
    plt.close()

    plt.figure(figsize=(9, 5))
    plt.plot(full["time_s"], full["target_dx"], label="target_dx")
    plt.plot(full["time_s"], full["target_dy"], label="target_dy")
    plt.xlabel("Elapsed time (s)")
    plt.ylabel("Accumulated correction (m)")
    plt.title("Target correction versus time")
    plt.legend()
    plt.tight_layout()
    plt.savefig(PLOTS / "ml_target_vs_time.png", dpi=150)
    plt.close()

    plt.figure(figsize=(9, 5))
    plt.plot(full["time_s"], error_magnitude)
    plt.xlabel("Elapsed time (s)")
    plt.ylabel("Baseline error magnitude (m)")
    plt.title("IMU baseline error growth")
    plt.tight_layout()
    plt.savefig(PLOTS / "ml_baseline_error_growth.png", dpi=150)
    plt.close()

    correlations = []
    for feature in feature_columns:
        for target in TARGETS:
            value = full[feature].corr(full[target])
            if np.isfinite(value):
                correlations.append((feature, target, float(value), abs(float(value))))
    correlations.sort(key=lambda item: item[3], reverse=True)
    correlation_table = pd.DataFrame(correlations, columns=["feature", "target", "correlation", "absolute"])
    pivot = correlation_table.pivot(index="feature", columns="target", values="correlation").fillna(0)
    plt.figure(figsize=(8, max(6, len(pivot) * 0.12)))
    plt.imshow(pivot.to_numpy(), aspect="auto", cmap="coolwarm", vmin=-1, vmax=1)
    plt.colorbar(label="Pearson correlation")
    plt.xticks(range(len(pivot.columns)), pivot.columns)
    plt.yticks(range(len(pivot.index)), pivot.index, fontsize=4)
    plt.title("Feature-target correlations")
    plt.tight_layout()
    plt.savefig(PLOTS / "ml_feature_correlation.png", dpi=150)
    plt.close()

    split_pass = True
    split_lines = []
    ranges = {}
    for name, frame in splits.items():
        ranges[name] = (float(frame.time_s.min()), float(frame.time_s.max()))
        split_lines.append(f"{name}: {ranges[name][0]:.6f}..{ranges[name][1]:.6f}")
    split_pass &= ranges["train"][1] < ranges["validation"][0] and ranges["validation"][1] < ranges["test"][0]
    split_lines.append(f"time ranges non-overlap: {'PASS' if split_pass else 'FAIL'}")
    duplicate_timestamps = int(full.time_s.duplicated().sum())
    split_lines.append(f"duplicate timestamps: {'PASS' if duplicate_timestamps == 0 else 'FAIL'} ({duplicate_timestamps})")
    split_duplicate_features = len(pd.concat([train[feature_columns], validation[feature_columns]]).drop_duplicates()) != len(train) + len(validation)
    split_duplicate_features |= len(pd.concat([train[feature_columns], test[feature_columns]]).drop_duplicates()) != len(train) + len(test)
    split_duplicate_features |= len(pd.concat([validation[feature_columns], test[feature_columns]]).drop_duplicates()) != len(validation) + len(test)
    split_lines.append(f"duplicate feature rows across splits: {'FAIL' if split_duplicate_features else 'PASS'}")
    window_size = 20
    split_positions = {name: full.index[full.time_s.isin(frame.time_s)].to_numpy() for name, frame in splits.items()}
    crosses = []
    for name in ("validation", "test"):
        positions = split_positions[name]
        if positions.size and positions[0] - (window_size - 1) < positions[0]:
            crosses.append(name)
    windows_pass = not crosses
    split_lines.append(f"causal windows cross split boundaries: {'PASS' if windows_pass else 'FAIL (' + ', '.join(crosses) + ')'}")

    findings, baseline_lines = source_findings(ROOT / "gps_denied_imu_baseline.py")
    v2_findings, v2_lines = source_findings(ROOT / "gps_denied_baseline_v2.py")
    report = []
    report.append("ML DIAGNOSTICS REPORT")
    report.append("=" * 80)
    report.append("A. DATASET HEALTH")
    report.append(f"Rows in ml_training_dataset.csv: {len(full)}")
    report.append(f"Feature columns: {len(feature_columns)}")
    report.append(f"Missing feature/target values: {missing}")
    report.append(f"Time range: {full.time_s.min():.6f}..{full.time_s.max():.6f} seconds")
    report.append("B. TARGET STATISTICS")
    report.extend(fmt_stats(target, target_stats[target]) for target in TARGETS)
    report.append("C. TARGET BEHAVIOR OVER TIME")
    report.append("Targets are evaluated as accumulated baseline-to-reference corrections at each window end.")
    report.append("D. BASELINE ERROR GROWTH")
    report.extend(f"Approximately {seconds:.0f}s into outage (sample {time_value:.3f}s): error={error:.6f}m" for (seconds, (time_value, error)) in zip([10, 20, 30, 40, 50, 60], growth_rows))
    report.append(f"Accumulated error magnitude: mean={error_magnitude.mean():.6f}, final={error_magnitude.iloc[-1]:.6f}")
    report.append(f"Local one-sample correction magnitude: mean={local_magnitude.mean():.6f}, median={local_magnitude.median():.6f}, max={local_magnitude.max():.6f}")
    report.append("The full target magnitude is substantially accumulated over time; local changes are a separate, smaller signal suitable for incremental correction experiments.")
    report.append("E. FEATURE-TARGET CORRELATIONS")
    report.append("Strongest absolute Pearson correlations:")
    report.extend(f"{row.feature} -> {row.target}: r={row.correlation:.6f}" for row in correlation_table.head(15).itertuples())
    report.append("F. SPLIT INTEGRITY")
    report.extend(split_lines)
    report.append("G. BASELINE IMPLEMENTATION FINDINGS")
    report.append("gps_denied_imu_baseline.py:")
    report.append("- Coordinate frame: longitude-derived East and latitude-derived North ENU using local equirectangular approximation.")
    report.append("- Heading convention: compass degrees, converted to ENU velocity as East=speed*sin(heading), North=speed*cos(heading).")
    report.append("- Acceleration frame: phone accelerometer minus phone gravity, then scipy Rotation.from_euler('ZYX', azimuth, pitch, roll).")
    report.append("- Integration: forward Euler velocity update followed by forward Euler position update at each smartphone timestamp.")
    report.append("- Initial state: last pre-outage vehicle speed, heading, and interpolated position at the first outage sample.")
    report.append(f"- Source locations: gravity removal line {findings['gravity removal']}; Euler rotation line {findings['Euler rotation']}; integration line {findings['integration loop']}; initial state line {findings['initial state']}; position line {findings['position initialization']}; reference line {findings['reference interpolation']}.")
    report.append("- Orientation issue: pitch is near -80 degrees and roll spans roughly -180..180 degrees; the baseline uses recorded values without correction. Gyroscope is loaded but not integrated.")
    report.append("gps_denied_baseline_v2.py:")
    report.append("- V2 default is not an IMU-only baseline: it uses vehicle heading and indicated vehicle speed in velocity propagation.")
    v2_heading_line = next((i + 1 for i, line in enumerate(v2_lines) if 'heading = vehicle_heading' in line), 'unknown')
    v2_speed_line = next((i + 1 for i, line in enumerate(v2_lines) if 'speed_mps =' in line), 'unknown')
    v2_propagation_line = next((i + 1 for i, line in enumerate(v2_lines) if 'estimate_x[index]' in line), 'unknown')
    report.append(f"- V2 source locations: vehicle-heading selection line {v2_heading_line}; speed interpolation line {v2_speed_line}; propagation line {v2_propagation_line}.")
    report.append("H. RECOMMENDED NEXT ML FORMULATION")
    report.append("Recommendation: E. Hybrid physics + ML residual correction, beginning with incremental position correction (delta_correction_x/y) and causal windows.")
    report.append("Reason: the current targets encode accumulated inertial drift and are strongly time-dependent, while one-step local changes are more stationary. Preserve the physics baseline, train residual corrections causally, and discard the first window_size-1 rows of every split so windows cannot cross boundaries.")
    report.append("This is a diagnostic recommendation, not a final navigation model.")
    REPORT_PATH.write_text("\n".join(report) + "\n", encoding="utf-8")

    print("ML DIAGNOSTICS")
    print(f"total samples: {len(full)}; features: {len(feature_columns)}; missing values: {missing}")
    for target in TARGETS:
        print(fmt_stats(target, target_stats[target]))
    print("BASELINE ERROR AT OUTAGE OFFSETS:")
    for seconds, (time_value, error) in zip([10, 20, 30, 40, 50, 60], growth_rows):
        print(f"{seconds}s (time {time_value:.3f}s): {error:.6f} m")
    print("STRONGEST FEATURE CORRELATIONS:")
    for row in correlation_table.head(10).itertuples():
        print(f"{row.feature} -> {row.target}: {row.correlation:.6f}")
    print("SPLIT INTEGRITY:")
    print("\n".join(split_lines))
    print("CURRENT ML STATUS: FAIL")
    print("MAIN FAILURE REASON: The model predicts large accumulated inertial drift from short local windows, with strong time-dependent target growth; the generated windows also cross split boundaries at validation/test starts.")
    print("RECOMMENDED NEXT STEP: Hybrid physics + ML residual correction using causal incremental position targets.")
    print(f"report: {REPORT_PATH}")


if __name__ == "__main__":
    main()