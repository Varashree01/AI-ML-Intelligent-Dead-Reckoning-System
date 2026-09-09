package com.sih26168.mobile;

import android.Manifest;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import java.io.IOException;
import java.util.Locale;

public final class MainActivity extends Activity implements SensorRepository.Listener, LocationListener {
    private static final int LOCATION_REQUEST = 41;
    private LocationManager locationManager;
    private SensorRepository sensorRepository;
    private NavigationEngine navigationEngine;
    private CsvRecorder recorder;
    private TextView gpsStatus;
    private TextView locationText;
    private TextView navigationMode;
    private TextView sensorAvailability;
    private TextView sensorPanel;
    private Button recordButton;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        navigationEngine = new NavigationEngine();
        recorder = new CsvRecorder(this);
        buildUi();
        sensorRepository = new SensorRepository(this, this);
        locationManager = (LocationManager) getSystemService(LOCATION_SERVICE);
        requestLocationPermission();
    }

    private void buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(28, 24, 28, 24);
        root.setBackgroundColor(Color.rgb(246, 248, 247));

        TextView title = label("SIH 26168  /  LIVE NAVIGATION", 20, Color.rgb(16, 42, 67));
        root.addView(title);
        TextView subtitle = label("AI-ML based Intelligent Dead Reckoning System", 14, Color.DKGRAY);
        root.addView(subtitle);

        gpsStatus = label("GPS STATUS: WAITING FOR PERMISSION", 17, Color.rgb(160, 83, 0));
        gpsStatus.setPadding(0, 24, 0, 6);
        root.addView(gpsStatus);
        navigationMode = label("MODE: WAITING FOR GPS", 15, Color.rgb(11, 110, 105));
        root.addView(navigationMode);
        locationText = label("Latitude: --\nLongitude: --\nAccuracy: --\nSpeed: --\nHeading: --", 16, Color.DKGRAY);
        locationText.setPadding(0, 16, 0, 16);
        root.addView(locationText);

        recordButton = new Button(this);
        recordButton.setText("START RECORDING");
        recordButton.setOnClickListener(view -> toggleRecording());
        root.addView(recordButton, new LinearLayout.LayoutParams(-1, 56));

        sensorAvailability = label("Sensors: checking...", 14, Color.DKGRAY);
        sensorAvailability.setPadding(0, 18, 0, 8);
        root.addView(sensorAvailability);
        TextView panelTitle = label("DEBUG SENSOR STREAM", 15, Color.rgb(16, 42, 67));
        root.addView(panelTitle);
        sensorPanel = label("Waiting for sensor samples...", 13, Color.DKGRAY);
        ScrollView scroll = new ScrollView(this);
        scroll.addView(sensorPanel);
        root.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));
        setContentView(root);
    }

    private TextView label(String text, int size, int color) {
        TextView view = new TextView(this);
        view.setText(text);
        view.setTextSize(size);
        view.setTextColor(color);
        return view;
    }

    private void requestLocationPermission() {
        if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION}, LOCATION_REQUEST);
        } else {
            startAcquisition();
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == LOCATION_REQUEST && grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            startAcquisition();
        } else {
            gpsStatus.setText("GPS STATUS: DENIED");
            navigationMode.setText("MODE: DEAD RECKONING (NO GPS FIX)");
            startSensorsOnly();
        }
    }

    private void startAcquisition() {
        startSensorsOnly();
        if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED && checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) != PackageManager.PERMISSION_GRANTED) return;
        try {
            locationManager.requestLocationUpdates(LocationManager.GPS_PROVIDER, 500L, 0.0f, this);
            locationManager.requestLocationUpdates(LocationManager.NETWORK_PROVIDER, 1000L, 0.0f, this);
        } catch (SecurityException error) {
            gpsStatus.setText("GPS STATUS: DENIED");
        }
    }

    private void startSensorsOnly() {
        sensorRepository.start();
    }

    private void toggleRecording() {
        if (!recorder.isRecording()) {
            try {
                recorder.start();
                recordButton.setText("STOP RECORDING");
                Toast.makeText(this, "Recording started", Toast.LENGTH_SHORT).show();
            } catch (IOException error) {
                Toast.makeText(this, "Could not start recording: " + error.getMessage(), Toast.LENGTH_LONG).show();
            }
        } else {
            String path = recorder.stop().getAbsolutePath();
            recordButton.setText("START RECORDING");
            Toast.makeText(this, "CSV saved: " + path, Toast.LENGTH_LONG).show();
        }
    }

    @Override
    public void onLocationChanged(Location location) {
        NavigationState state = navigationEngine.onLocation(location);
        runOnUiThread(() -> updateNavigation(state));
    }

    private void updateNavigation(NavigationState state) {
        gpsStatus.setText("GPS STATUS: AVAILABLE");
        navigationMode.setText("MODE: GPS");
        locationText.setText(String.format(Locale.US, "Latitude: %.7f\nLongitude: %.7f\nAccuracy: %.1f m\nSpeed: %.2f m/s\nHeading: %.1f deg", state.latitude, state.longitude, state.accuracy, state.speedMps, state.headingDegrees));
    }

    @Override
    public void onProviderDisabled(String provider) {
        NavigationState state = navigationEngine.currentState();
        gpsStatus.setText("GPS STATUS: DENIED");
        navigationMode.setText("MODE: DEAD RECKONING (LAST KNOWN STATE)");
        if (!Double.isNaN(state.latitude)) updateNavigationLoss(state);
    }

    private void updateNavigationLoss(NavigationState state) {
        navigationMode.setText("MODE: DEAD RECKONING (LAST KNOWN STATE)");
        gpsStatus.setText("GPS STATUS: DENIED");
    }

    @Override
    public void onSensorSample(SensorSample sample) {
        NavigationState state = navigationEngine.currentState();
        if (recorder.isRecording()) recorder.append(sample, state);
        runOnUiThread(() -> sensorPanel.setText(String.format(Locale.US,
                "timestamp (elapsed ns): %d\n\naccelerometer\n  x %.5f\n  y %.5f\n  z %.5f\n\ngyroscope (rad/s)\n  x %.5f\n  y %.5f\n  z %.5f\n\nmagnetometer (uT)\n  x %.5f\n  y %.5f\n  z %.5f\n\nrotation vector\n  %.5f  %.5f  %.5f  %.5f",
                sample.timestampNanos, sample.accelerometer[0], sample.accelerometer[1], sample.accelerometer[2], sample.gyroscope[0], sample.gyroscope[1], sample.gyroscope[2], sample.magnetometer[0], sample.magnetometer[1], sample.magnetometer[2], sample.rotationVector[0], sample.rotationVector[1], sample.rotationVector[2], sample.rotationVector[3])));
    }

    @Override
    public void onSensorAvailability(boolean accelerometer, boolean gyroscope, boolean magnetometer, boolean rotationVector) {
        sensorAvailability.setText(String.format(Locale.US, "Sensors: accelerometer %s  |  gyroscope %s  |  magnetometer %s  |  rotation vector %s", available(accelerometer), available(gyroscope), available(magnetometer), available(rotationVector)));
    }

    private String available(boolean value) { return value ? "available" : "unavailable"; }

    @Override
    protected void onDestroy() {
        if (recorder.isRecording()) recorder.stop();
        if (sensorRepository != null) sensorRepository.stop();
        if (locationManager != null) locationManager.removeUpdates(this);
        super.onDestroy();
    }
}
