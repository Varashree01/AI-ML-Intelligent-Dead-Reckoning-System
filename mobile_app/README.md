# SIH 26168 Mobile Prototype

Phase 1 collects real Android GPS and motion sensors and displays the latest synchronized state. It does not implement the EKF, ML correction, maps, cloud backend, or simulated measurements.

## Build

Open `mobile_app` in Android Studio with Android SDK 35 installed, then run the `app` configuration on a physical Android device. Grant location permission when prompted. A physical device is recommended because emulators may not expose all motion sensors.

From a machine with Gradle installed, run:

```text
gradle assembleDebug
```

The debug APK is written to `app/build/outputs/apk/debug/app-debug.apk`.

## Recording

Tap **START RECORDING** and then **STOP RECORDING**. CSV files are stored in the app-specific external files directory under `recordings/`; Android exposes this location through the device's app storage tools. The CSV contains platform elapsed-nanosecond timestamp, GPS fields, accelerometer, gyroscope, and magnetometer values.

Missing sensors are reported in the UI. If location permission is denied or the provider becomes unavailable, the screen changes to `DEAD RECKONING (LAST KNOWN STATE)` and does not fabricate a position.
