import numpy as np
import json
import math
from pathlib import Path


# ============================================================
# FILE PATHS
# ============================================================

RESULT_FILE = Path("data/vehicle_dr_result.npz")
IMU_FILE = Path("data/simulated_run_filtered.npz")

OUTPUT_FILE = Path(
    "SIH SOL/SIH SOL/public/vehicle_dr_result.json"
)


# ============================================================
# SAFE JSON CONVERSION
# ============================================================

def convert(value):
    """
    Convert NumPy data into valid JSON data.

    - NumPy arrays -> Python lists
    - NumPy scalars -> Python scalars
    - NaN / Infinity -> None
    """

    if isinstance(value, np.ndarray):
        return convert(value.tolist())

    if isinstance(value, np.generic):
        return convert(value.item())

    if isinstance(value, list):
        return [convert(item) for item in value]

    if isinstance(value, tuple):
        return [convert(item) for item in value]

    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return value

    if isinstance(value, int):
        return value

    if isinstance(value, bool):
        return value

    return value


# ============================================================
# CHECK INPUT FILES
# ============================================================

if not RESULT_FILE.exists():
    raise FileNotFoundError(
        f"Navigation result file not found: {RESULT_FILE}"
    )

if not IMU_FILE.exists():
    raise FileNotFoundError(
        f"Filtered IMU file not found: {IMU_FILE}"
    )


# ============================================================
# LOAD NAVIGATION RESULT
# ============================================================

print("==============================================")
print(" Python -> React JSON Export")
print("==============================================")

print("\nLoading navigation result...")

result_data = np.load(
    RESULT_FILE,
    allow_pickle=True
)

output = {}

# Preserve all existing navigation results
for key in result_data.files:
    output[key] = convert(result_data[key])

print(
    f"Navigation result keys exported: "
    f"{len(result_data.files)}"
)

result_data.close()


# ============================================================
# LOAD FILTERED IMU DATA
# ============================================================

print("\nLoading filtered IMU dataset...")

imu_data = np.load(
    IMU_FILE,
    allow_pickle=True
)

print(
    f"IMU samples: {len(imu_data['t'])}"
)


# ============================================================
# ACTUAL FILTERED SENSOR DATA
# ============================================================

# Timestamp
output["imu_time"] = convert(
    imu_data["t"]
)


# ------------------------------------------------------------
# FILTERED ACCELEROMETER
# ------------------------------------------------------------
#
# Shape:
#     (5200, 3)
#
# Units:
#     m/s²
#
# Columns:
#     X, Y, Z
#
# This is the actual output of the adaptive IMU filter.
# ------------------------------------------------------------

output["imu_acc"] = convert(
    imu_data["acc_filtered"]
)


# ------------------------------------------------------------
# FILTERED GYROSCOPE
# ------------------------------------------------------------
#
# Shape:
#     (5200, 3)
#
# Units:
#     rad/s or deg/s depending on Python pipeline convention.
#
# We do NOT alter the values here.
# React receives exactly what Python produced.
# ------------------------------------------------------------

output["imu_gyro"] = convert(
    imu_data["gyro_filtered"]
)


# ------------------------------------------------------------
# MAGNETOMETER
# ------------------------------------------------------------
#
# Shape:
#     (5200, 3)
#
# Units:
#     microtesla (µT)
#
# Again, values are transferred without modification.
# ------------------------------------------------------------

output["imu_mag"] = convert(
    imu_data["mag"]
)


# ============================================================
# RAW SENSOR DATA
# ============================================================

# Keep raw accelerometer for diagnostics
output["raw_acc"] = convert(
    imu_data["raw_acc"]
)


# Keep raw gyroscope for diagnostics
output["raw_gyro"] = convert(
    imu_data["raw_gyro"]
)


# ============================================================
# IMU DISTURBANCE INFORMATION
# ============================================================

output["imu_disturbance_score"] = convert(
    imu_data["imu_disturbance_score"]
)

output["vibration_detected"] = convert(
    imu_data["vibration_detected"]
)

output["bump_detected"] = convert(
    imu_data["bump_detected"]
)


# ============================================================
# ADDITIONAL SENSOR / MOTION DATA
# ============================================================

# These are useful for synchronizing the frontend
# with the exact Python simulation timeline.

output["vehicle_speed"] = convert(
    imu_data["vehicle_speed"]
)

output["gt_velocity"] = convert(
    imu_data["gt_velocity"]
)

output["gt_acceleration"] = convert(
    imu_data["gt_acceleration"]
)

output["gt_heading"] = convert(
    imu_data["gt_heading"]
)

output["gps_available"] = convert(
    imu_data["gps_available"]
)

output["gps_pos"] = convert(
    imu_data["gps_pos"]
)


# ============================================================
# CLOSE IMU FILE
# ============================================================

imu_data.close()


# ============================================================
# CREATE OUTPUT DIRECTORY
# ============================================================

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# WRITE JSON
# ============================================================

print("\nWriting JSON...")

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        output,
        f,
        allow_nan=False,
        separators=(",", ":")
    )


# ============================================================
# VALIDATE JSON
# ============================================================

print("Validating JSON...")

with open(
    OUTPUT_FILE,
    "r",
    encoding="utf-8"
) as f:

    validated = json.load(f)


# ============================================================
# BASIC DATA VALIDATION
# ============================================================

required_keys = [
    "imu_time",
    "imu_acc",
    "imu_gyro",
    "imu_mag",
]


missing_keys = [
    key
    for key in required_keys
    if key not in validated
]


if missing_keys:
    raise RuntimeError(
        f"Required IMU keys missing: {missing_keys}"
    )


# Check sample counts
time_samples = len(
    validated["imu_time"]
)

acc_samples = len(
    validated["imu_acc"]
)

gyro_samples = len(
    validated["imu_gyro"]
)

mag_samples = len(
    validated["imu_mag"]
)


if not (
    time_samples
    == acc_samples
    == gyro_samples
    == mag_samples
):
    raise RuntimeError(
        "IMU sample count mismatch: "
        f"time={time_samples}, "
        f"acc={acc_samples}, "
        f"gyro={gyro_samples}, "
        f"mag={mag_samples}"
    )


# ============================================================
# FINAL REPORT
# ============================================================

print("\n==============================================")
print(" Python -> React JSON Export Successful")
print("==============================================")

print(f"Output : {OUTPUT_FILE}")
print(f"Keys   : {len(validated)}")

print("\nPython navigation data : exported")
print("Filtered accelerometer : exported")
print("Filtered gyroscope     : exported")
print("Magnetometer            : exported")
print("Raw IMU data            : exported")
print("Disturbance data        : exported")

print("\nIMU synchronization check")
print("----------------------------------------------")
print(f"Timestamp samples : {time_samples}")
print(f"Accelerometer     : {acc_samples}")
print(f"Gyroscope         : {gyro_samples}")
print(f"Magnetometer      : {mag_samples}")

print("\nNaN / Infinity      : converted to null")
print("JSON validation     : PASSED")
print("Sample alignment    : PASSED")

print("==============================================")