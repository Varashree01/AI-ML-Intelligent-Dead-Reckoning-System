import React from "react";

const AIEnginePanel = ({
  driftErrorMeters = null,
  aiErrorMeters = null,
  aiConfidence = null,
  isGpsLost = false,
  gpsState = "AVAILABLE",
  outageDuration = 0,
}) => {
  const hasError =
    typeof driftErrorMeters === "number" &&
    Number.isFinite(driftErrorMeters);

  const hasConfidence =
    typeof aiConfidence === "number" &&
    Number.isFinite(aiConfidence);

  return (
    <section className="panel ai-engine-panel">
      <div className="panel-header">
        <div>
          <h2>AI Vehicle Speed Estimation</h2>
          <p>
            Random Forest model trained on vehicle IMU features
          </p>
        </div>

        <div className="status-badge">
          RANDOM FOREST
        </div>
      </div>

      <div className="ai-metrics-grid">

        {/* Current navigation error */}
        <div className="metric-card">
          <span className="metric-label">
            Current Trajectory Error
          </span>

          <strong className="metric-value">
            {hasError
              ? `${driftErrorMeters.toFixed(2)} m`
              : "N/A"}
          </strong>

          <span className="metric-subtext">
            Navigation estimate
          </span>
        </div>

        {/* Speed MAE */}
        <div className="metric-card">
          <span className="metric-label">
            Speed MAE
          </span>

          <strong className="metric-value">
            0.165 m/s
          </strong>

          <span className="metric-subtext">
            Held-out evaluation
          </span>
        </div>

        {/* Speed RMSE */}
        <div className="metric-card">
          <span className="metric-label">
            Speed RMSE
          </span>

          <strong className="metric-value">
            0.192 m/s
          </strong>

          <span className="metric-subtext">
            Held-out evaluation
          </span>
        </div>

        {/* Confidence */}
        <div className="metric-card">
          <span className="metric-label">
            Navigation Confidence
          </span>

          <strong className="metric-value">
            {hasConfidence
              ? `${(aiConfidence * 100).toFixed(0)}%`
              : "N/A"}
          </strong>

          <span className="metric-subtext">
            {hasConfidence
              ? "Validated confidence model"
              : "Confidence model not implemented"}
          </span>
        </div>

      </div>

      {/* Navigation state */}
      <div className="ai-status-section">

        <div className="ai-status-row">
          <span>GNSS Status</span>

          <strong>
            {gpsState}
          </strong>
        </div>

        <div className="ai-status-row">
          <span>Navigation Mode</span>

          <strong>
            {isGpsLost
              ? "AI/ML DEAD RECKONING"
              : "GNSS ASSISTED"}
          </strong>
        </div>

        <div className="ai-status-row">
          <span>GNSS Outage Duration</span>

          <strong>
            {Number(outageDuration).toFixed(1)} s
          </strong>
        </div>

      </div>

      {/* Explanation */}
      <div className="ai-description">
        <h3>AI/ML Vehicle Speed Estimation</h3>

        <p>
          The Random Forest model estimates vehicle speed from noisy
          accelerometer and gyroscope features. The estimated speed
          is combined with heading information for dead-reckoning
          during GNSS-denied periods.
        </p>
      </div>

      {/* Processing pipeline */}
      <div className="processing-pipeline">
        <h3>Navigation Processing Pipeline</h3>

        <div className="pipeline-flow">
          <span>Raw IMU</span>
          <span>→</span>
          <span>Adaptive Filtering</span>
          <span>→</span>
          <span>RF Speed Estimator</span>
          <span>→</span>
          <span>DR Trajectory</span>
        </div>
      </div>

      {/* Validation note */}
      <div className="validation-note">
        <strong>Validation:</strong>

        <p>
          Speed metrics are calculated on a held-out portion of the
          vehicle-realistic synthetic dataset. Ground-truth vehicle
          speed is used only as the training/evaluation target and
          is not provided as an inference feature.
        </p>
      </div>

    </section>
  );
};

export default AIEnginePanel;