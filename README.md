# NAVAURA 🛰️
### AI/ML-Based Intelligent Dead Reckoning System for Seamless Navigation

[![Smart India Hackathon 2026](https://img.shields.io/badge/SIH-2026-blue.svg)](https://www.sih.gov.in/)
[![Problem Statement](https://img.shields.io/badge/Problem%20Statement-SIH26168-orange.svg)]()
[![Organization](https://img.shields.io/badge/Organization-ISRO%20%2F%20DoS-green.svg)](https://www.isro.gov.in/)
[![Team](https://img.shields.io/badge/Team-TEAM%2006-cyan.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Vite](https://img.shields.io/badge/Frontend-React%20%2B%20Vite%20%2B%20Tailwind-blueviolet.svg)]()
[![Python](https://img.shields.io/badge/Backend-Python%203.11%2B%20%7C%20SciPy%20%7C%20Scikit--Learn-blue.svg)]()

---

## 📌 Executive Overview

**NAVAURA** is a research-grade, GNSS-resilient tactical navigation system developed for **Smart India Hackathon 2026 (Problem Statement: SIH26168)** under the **Indian Space Research Organisation (ISRO) / Department of Space**.

Conventional navigation systems experience catastrophic positioning failures when GNSS (GPS/NavIC) signals are obstructed in tunnels, deep urban canyons, underground facilities, and signal-jammed/spoofed theaters. Traditional unconstrained Inertial Dead Reckoning (DR) diverges exponentially due to low-cost MEMS IMU sensor noise, drift, and vibration.

NAVAURA solves this by combining **adaptive IMU pre-filtering**, **EKF-based heading & orientation estimation**, **AI/ML vehicle speed & displacement inference**, and **innovation-gated EKF re-fusion** to provide seamless, high-accuracy trajectory continuity during signal blackouts.

---

## 🚀 Key Architectural Innovations

```
               ┌──────────────────────────────────────────────┐
               │    Raw Sensor Ingestion (IMU + Mag + GNSS)   │
               └──────────────────────┬───────────────────────┘
                                      │
               ┌──────────────────────▼───────────────────────┐
               │   1. Adaptive Vibration & Disturbance Filter  │
               │   (Bandpass filtering + dynamic thresholding)│
               └──────────────────────┬───────────────────────┘
                                      │
         ┌────────────────────────────┴────────────────────────────┐
         │                                                         │
┌────────▼─────────────────────────┐     ┌─────────────────────────▼────────────────┐
│   2. EKF Heading Estimator       │     │   3. AI Speed & Displacement Regressor   │
│   • Gyro rate integration        │     │   • Random Forest & Gradient Boosted ML  │
│   • Mag anomaly rejection        │     │   • High-frequency feature extraction    │
│   • Continuous bias tracking     │     │   • Zero ground-truth leakage inference  │
└────────────────┬─────────────────┘     └─────────────────────────┬────────────────┘
                 │                                                 │
                 └────────────────────┬────────────────────────────┘
                                      │
               ┌──────────────────────▼───────────────────────┐
               │   4. Extended Kalman Filter (EKF) Estimator  │
               │   • State: [x, y, v, ψ, b_gyro]              │
               │   • Covariance prediction & propagation      │
               │   • Outage-gated innovation update           │
               └──────────────────────┬───────────────────────┘
                                      │
         ┌────────────────────────────┴────────────────────────────┐
         │                                                         │
┌────────▼─────────────────────────┐     ┌─────────────────────────▼────────────────┐
│      GNSS Normal Operation       │     │        GNSS Blackout / Outage            │
│   • Continuous state re-anchoring│     │   • Smooth autonomous DR propagation     │
│   • Sensor bias online learning  │     │   • Sub-3m RMSE error containment        │
└──────────────────────────────────┘     └──────────────────────────────────────────┘
```

1. **Adaptive IMU Disturbance Filter**:
   Isolates high-frequency chassis vibrations, engine noise, and phone jitter from authentic kinematic motion vectors.
2. **2-State EKF Heading Fusion**:
   Fuses 3-axis gyroscope angular velocities with magnetometer heading while discarding transient magnetic anomalies (bridges, power lines, train tracks).
3. **ML Motion & Velocity Inference**:
   Extracts rolling statistical, energy, and frequency features to infer forward vehicle speed directly from inertial dynamics without relying on wheel odometry or GNSS derivatives.
4. **Resilient Re-Anchoring**:
   When satellite lock is restored, NAVAURA executes innovation gating and smooth Kalman correction to prevent sudden position snapping.

---

## 🖥️ Interactive Web Dashboard & Telemetry

The frontend workspace provides tactical-grade telemetry and simulation capabilities:

- **Tactical Map**: OpenStreetMap, Esri Dark Gray Canvas, World Topo, and Satellite Imagery with zero API key dependencies.
- **Simulation Control Toolbar**:
  - `PLAY / PAUSE`: Real-time trajectory playback control.
  - `TRIGGER OUTAGE`: Instantly simulate GNSS blackout to trigger autonomous dead reckoning.
  - `RESTORE GNSS`: Re-acquire satellite lock and demonstrate EKF position re-anchoring.
  - `SPEED MULTIPLIER`: 1x, 2x, and 5x simulation clock rates.
  - `RUN AUTOMATED DEMO`: Complete end-to-end tunnel outage macro sequence with automated milestone telemetry.
- **Diagnostics**: Real-time position error (RMSE), heading, G-force telemetry, and processing pipeline monitor.
- **Fullscreen Tactical Mode**: Root-level HUD overlay with quick-action toggles and `ESC` hotkey support.

---

## 📂 Repository Structure

```
├── data/                               # Calibration and filtered run telemetry
│   ├── simulated_run_filtered.npz      # Processed multi-sensor simulation run
│   └── vehicle_dr_result.json          # Pre-computed 5,200 sample navigation output
├── models/                             # Trained ML inference weights
│   └── vehicle_speed_model.joblib      # Random Forest speed regressor
├── mobile_app/                         # Flutter/Android sensor logger client
├── SIH SOL/
│   └── SIH SOL/                        # React + Vite Tactical Dashboard
│       ├── src/
│       │   ├── components/
│       │   │   ├── MapView.jsx         # Multi-layer GIS canvas & trajectory renderer
│       │   │   ├── SimulationControls.jsx # Playback & outage simulation toolbar
│       │   │   ├── NavigationPage.jsx  # Primary tactical dashboard
│       │   │   ├── BenchmarkPage.jsx   # Ablation and error comparisons
│       │   │   ├── SensorsPage.jsx     # High-frequency 9-DoF IMU telemetry
│       │   │   └── AnalyticsPage.jsx   # Error distribution & drift curves
│       │   ├── App.jsx                 # Central application controller
│       │   └── index.css               # Clean engineering visual theme
│       ├── package.json
│       └── vite.config.js
├── imu_disturbance_filter.py           # Vibration & noise preprocessing
├── heading_estimator.py                # Gyro + Magnetometer EKF fusion
├── vehicle_speed_estimator.py          # ML feature extraction & speed inference
├── vehicle_dead_reckoning.py           # Unified EKF dead-reckoning engine
├── export_results.py                   # Exports synchronized JSON for frontend
├── main.py                             # Master pipeline runner
├── requirements.txt                    # Python dependencies
└── README.md
```

---

## ⚡ Quick Start Guide

### 1. Prerequisites
- **Python**: 3.10+
- **Node.js**: 18+ & npm

### 2. Run Python Navigation Engine
```bash
# Clone the repository
git clone https://github.com/your-username/NAVAURA.git
cd NAVAURA

# Install Python requirements
pip install -r requirements.txt

# Run full navigation pipeline and export frontend results
python main.py
```

### 3. Run Tactical Frontend Dashboard
```bash
# Navigate to the frontend directory
cd "SIH SOL/SIH SOL"

# Install dependencies
npm install

# Start local Vite development server
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 🌐 Deploy to Vercel

The frontend is ready for 1-click deployment on **Vercel**:

### Option A: Via Vercel Web Dashboard (Recommended)
1. Push this repository to your GitHub account.
2. Go to [Vercel Dashboard](https://vercel.com/new).
3. Import your `NAVAURA` repository.
4. Set **Root Directory** to: `SIH SOL/SIH SOL`.
5. Framework Preset: **Vite**.
6. Click **Deploy**.

### Option B: Via Vercel CLI
```bash
cd "SIH SOL/SIH SOL"
npx vercel --prod
```

---

## 📈 Benchmarks & Experimental Results

| Metric | Raw IMU Dead Reckoning | Baseline EKF | NAVAURA (AI-ML + EKF) |
| :--- | :---: | :---: | :---: |
| **Max Drift Rate** | ~14.2 m/s | ~4.8 m/s | **0.31 m/s** |
| **RMSE (60s Outage)** | 89.4 m | 28.1 m | **2.72 m** |
| **Heading Stability** | ±18.4° drift | ±6.2° drift | **±1.1° fused** |
| **Inference Latency** | < 1 ms | < 2 ms | **3.8 ms** |

---

## 👥 Team & Acknowledgements

- **Event**: Smart India Hackathon 2026 (SIH 2026)
- **Problem Statement ID**: SIH26168
- **Organization**: ISRO / Department of Space
- **Team**: TEAM 06
- **Lead Researcher & Engineer**: Team 06 Developers

Developed with pride for India's indigenous navigation and aerospace research initiatives.
