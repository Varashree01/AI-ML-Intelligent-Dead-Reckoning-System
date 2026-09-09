package com.sih26168.mobile;

public final class NavigationState {
    public final boolean gpsAvailable;
    public final double latitude;
    public final double longitude;
    public final float accuracy;
    public final float speedMps;
    public final float headingDegrees;
    public final long timestampNanos;

    public NavigationState(boolean gpsAvailable, double latitude, double longitude,
                           float accuracy, float speedMps, float headingDegrees,
                           long timestampNanos) {
        this.gpsAvailable = gpsAvailable;
        this.latitude = latitude;
        this.longitude = longitude;
        this.accuracy = accuracy;
        this.speedMps = speedMps;
        this.headingDegrees = headingDegrees;
        this.timestampNanos = timestampNanos;
    }
}
