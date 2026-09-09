package com.sih26168.mobile;

import android.content.Context;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.os.SystemClock;

import java.util.Arrays;

public final class SensorRepository implements SensorEventListener {
    public interface Listener {
        void onSensorSample(SensorSample sample);
        void onSensorAvailability(boolean accelerometer, boolean gyroscope, boolean magnetometer, boolean rotationVector);
    }

    private final SensorManager sensorManager;
    private final Listener listener;
    private final float[] accelerometer = new float[3];
    private final float[] gyroscope = new float[3];
    private final float[] magnetometer = new float[3];
    private final float[] rotationVector = new float[5];
    private boolean hasAccelerometer;
    private boolean hasGyroscope;
    private boolean hasMagnetometer;
    private boolean hasRotationVector;

    public SensorRepository(Context context, Listener listener) {
        sensorManager = (SensorManager) context.getSystemService(Context.SENSOR_SERVICE);
        this.listener = listener;
        hasAccelerometer = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER) != null;
        hasGyroscope = sensorManager.getDefaultSensor(Sensor.TYPE_GYROSCOPE) != null;
        hasMagnetometer = sensorManager.getDefaultSensor(Sensor.TYPE_MAGNETIC_FIELD) != null;
        hasRotationVector = sensorManager.getDefaultSensor(Sensor.TYPE_ROTATION_VECTOR) != null;
    }

    public void start() {
        register(Sensor.TYPE_ACCELEROMETER);
        register(Sensor.TYPE_GYROSCOPE);
        register(Sensor.TYPE_MAGNETIC_FIELD);
        register(Sensor.TYPE_ROTATION_VECTOR);
        listener.onSensorAvailability(hasAccelerometer, hasGyroscope, hasMagnetometer, hasRotationVector);
    }

    public void stop() {
        sensorManager.unregisterListener(this);
    }

    private void register(int type) {
        Sensor sensor = sensorManager.getDefaultSensor(type);
        if (sensor != null) {
            sensorManager.registerListener(this, sensor, SensorManager.SENSOR_DELAY_GAME);
        }
    }

    @Override
    public void onSensorChanged(SensorEvent event) {
        if (event.sensor.getType() == Sensor.TYPE_ACCELEROMETER) {
            System.arraycopy(event.values, 0, accelerometer, 0, 3);
        } else if (event.sensor.getType() == Sensor.TYPE_GYROSCOPE) {
            System.arraycopy(event.values, 0, gyroscope, 0, 3);
        } else if (event.sensor.getType() == Sensor.TYPE_MAGNETIC_FIELD) {
            System.arraycopy(event.values, 0, magnetometer, 0, 3);
        } else if (event.sensor.getType() == Sensor.TYPE_ROTATION_VECTOR) {
            System.arraycopy(event.values, 0, rotationVector, 0, Math.min(event.values.length, rotationVector.length));
        } else {
            return;
        }
        listener.onSensorSample(new SensorSample(
                SystemClock.elapsedRealtimeNanos(), Arrays.copyOf(accelerometer, 3),
                Arrays.copyOf(gyroscope, 3), Arrays.copyOf(magnetometer, 3),
                Arrays.copyOf(rotationVector, rotationVector.length)));
    }

    @Override
    public void onAccuracyChanged(Sensor sensor, int accuracy) {
    }
}
