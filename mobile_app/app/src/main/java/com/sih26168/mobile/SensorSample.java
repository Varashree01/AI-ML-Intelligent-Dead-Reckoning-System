package com.sih26168.mobile;

public final class SensorSample {
    public final long timestampNanos;
    public final float[] accelerometer;
    public final float[] gyroscope;
    public final float[] magnetometer;
    public final float[] rotationVector;

    public SensorSample(long timestampNanos, float[] accelerometer, float[] gyroscope,
                        float[] magnetometer, float[] rotationVector) {
        this.timestampNanos = timestampNanos;
        this.accelerometer = accelerometer;
        this.gyroscope = gyroscope;
        this.magnetometer = magnetometer;
        this.rotationVector = rotationVector;
    }
}
