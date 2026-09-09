package com.sih26168.mobile;

import android.content.Context;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.util.Locale;

public final class CsvRecorder {
    private final Context context;
    private PrintWriter writer;
    private File outputFile;

    public CsvRecorder(Context context) {
        this.context = context.getApplicationContext();
    }

    public synchronized void start() throws IOException {
        File directory = new File(context.getExternalFilesDir(null), "recordings");
        if (!directory.exists() && !directory.mkdirs()) {
            throw new IOException("Could not create recording directory");
        }
        outputFile = new File(directory, "sensor_recording_" + System.currentTimeMillis() + ".csv");
        writer = new PrintWriter(new FileWriter(outputFile));
        writer.println("timestamp,latitude,longitude,gps_accuracy,gps_speed,gps_heading,accelerometer_x,accelerometer_y,accelerometer_z,gyroscope_x,gyroscope_y,gyroscope_z,magnetometer_x,magnetometer_y,magnetometer_z");
    }

    public synchronized boolean isRecording() {
        return writer != null;
    }

    public synchronized void append(SensorSample sample, NavigationState navigation) {
        if (writer == null) return;
        writer.printf(Locale.US, "%d,%.8f,%.8f,%.3f,%.3f,%.3f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f%n",
                sample.timestampNanos, navigation.latitude, navigation.longitude, navigation.accuracy,
                navigation.speedMps, navigation.headingDegrees, sample.accelerometer[0], sample.accelerometer[1], sample.accelerometer[2],
                sample.gyroscope[0], sample.gyroscope[1], sample.gyroscope[2], sample.magnetometer[0], sample.magnetometer[1], sample.magnetometer[2]);
    }

    public synchronized File stop() {
        if (writer == null) return outputFile;
        writer.flush();
        writer.close();
        writer = null;
        return outputFile;
    }
}
