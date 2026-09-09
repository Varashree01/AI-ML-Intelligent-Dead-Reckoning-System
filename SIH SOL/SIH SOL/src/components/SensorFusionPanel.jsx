import React from "react";

const SensorFusionPanel = ({
  isGpsLost = false,
  speedKmh = 0,
  headingDeg = 0,
}) => {
  const gpsStatus = isGpsLost ? "DENIED" : "AVAILABLE";

  const gpsAction = isGpsLost
    ? "Inertial navigation active"
    : "Position correction active";

  return (
    <section className="panel sensor-fusion-panel">

      <div className="panel-header">
        <div>
          <h2>Multi-Sensor Fusion Engine</h2>
          <p>
            IMU filtering, heading estimation and GNSS-assisted navigation
          </p>
        </div>

        <div className="status-badge">
          {isGpsLost
            ? "GNSS-DENIED NAVIGATION"
            : "GNSS + IMU NAVIGATION"}
        </div>
      </div>

      {/* Sensor status cards */}
      <div className="fusion-sensors-grid">

        <div className="sensor-card">
          <div className="sensor-title">
            ACCELEROMETER
          </div>

          <strong>3-Axis Motion</strong>

          <span>
            Vibration filtered
          </span>
        </div>

        <div className="sensor-card">
          <div className="sensor-title">
            GYROSCOPE
          </div>

          <strong>Angular Velocity</strong>

          <span>
            Heading prediction
          </span>
        </div>

        <div className="sensor-card">
          <div className="sensor-title">
            MAGNETOMETER
          </div>

          <strong>Magnetic Field</strong>

          <span>
            Field measurement
          </span>
        </div>

        <div className="sensor-card">
          <div className="sensor-title">
            GNSS
          </div>

          <strong>{gpsStatus}</strong>

          <span>
            {gpsAction}
          </span>
        </div>

      </div>

      {/* Processing pipeline */}
      <div className="fusion-processing">

        <h3>Sensor Processing &amp; Fusion</h3>

        <div className="fusion-flow">

          <div className="fusion-step">
            <strong>Adaptive IMU Filter</strong>
            <span>Vibration &amp; bump suppression</span>
          </div>

          <div className="fusion-arrow">→</div>

          <div className="fusion-step">
            <strong>Heading KF</strong>
            <span>Gyro + magnetometer fusion</span>
          </div>

          <div className="fusion-arrow">→</div>

          <div className="fusion-step">
            <strong>RF Speed Model</strong>
            <span>Vehicle speed estimation</span>
          </div>

        </div>

      </div>

      {/* Navigation outputs */}
      <div className="fusion-output-grid">

        <div className="fusion-output-card">
          <span>Estimated Vehicle Speed</span>

          <strong>
            {Number(speedKmh).toFixed(1)} km/h
          </strong>

          <small>
            {(Number(speedKmh) / 3.6).toFixed(2)} m/s
          </small>
        </div>

        <div className="fusion-output-card">
          <span>Fused Heading</span>

          <strong>
            {Number(headingDeg).toFixed(1)}°
          </strong>

          <small>
            Gyro + Magnetometer
          </small>
        </div>

      </div>

      {/* Navigation explanation */}
      <div className="fusion-description">

        <h3>GNSS-Assisted Continuous Navigation</h3>

        <p>
          Estimated speed and fused heading are used to maintain the
          navigation trajectory when GNSS becomes unavailable.
        </p>

        <div className="fusion-status-message">
          {isGpsLost
            ? "GNSS unavailable — AI/ML dead reckoning active"
            : "GNSS available — navigation correction active"}
        </div>

      </div>

    </section>
  );
};

export default SensorFusionPanel;