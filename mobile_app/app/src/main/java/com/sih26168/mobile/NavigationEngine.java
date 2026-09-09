package com.sih26168.mobile;

import android.location.Location;
import android.os.SystemClock;

public final class NavigationEngine {
    private static final long GPS_FRESHNESS_NANOS = 5_000_000_000L;
    private NavigationState state = new NavigationState(false, Double.NaN, Double.NaN,
            Float.NaN, Float.NaN, Float.NaN, 0L);

    public synchronized NavigationState onLocation(Location location) {
        float heading = location.hasBearing() ? location.getBearing() : state.headingDegrees;
        float speed = location.hasSpeed() ? location.getSpeed() : Float.NaN;
        state = new NavigationState(true, location.getLatitude(), location.getLongitude(),
                location.hasAccuracy() ? location.getAccuracy() : Float.NaN, speed, heading,
                SystemClock.elapsedRealtimeNanos());
        return state;
    }

    public synchronized NavigationState currentState() {
        boolean fresh = state.gpsAvailable
                && SystemClock.elapsedRealtimeNanos() - state.timestampNanos <= GPS_FRESHNESS_NANOS;
        if (fresh == state.gpsAvailable) {
            return state;
        }
        return new NavigationState(false, state.latitude, state.longitude, state.accuracy,
                state.speedMps, state.headingDegrees, state.timestampNanos);
    }
}
