# NAVAURA 🛰️
### AI/ML-Based Intelligent Dead Reckoning System for Seamless Navigation

<div align="center">

[![Live Production Demo](https://img.shields.io/badge/🌐_LIVE_DEMO-navaura--sih--2026.vercel.app-00DC82?style=for-the-badge&logo=vercel&logoColor=white)](https://navaura-sih-2026.vercel.app)
[![Smart India Hackathon 2026](https://img.shields.io/badge/SIH-2026-blue.svg?style=for-the-badge)](https://www.sih.gov.in/)
[![Problem Statement](https://img.shields.io/badge/Problem%20Statement-SIH26168-orange.svg?style=for-the-badge)]()
[![Organization](https://img.shields.io/badge/Organization-ISRO%20%2F%20DoS-138808.svg?style=for-the-badge)](https://www.isro.gov.in/)
[![Team](https://img.shields.io/badge/Team-TEAM%2006-00C4CC.svg?style=for-the-badge)]()

<br/>

[![GitHub Repo](https://img.shields.io/badge/GitHub-Repository-181717?style=flat&logo=github)](https://github.com/Varashree01/AI-ML-Intelligent-Dead-Reckoning-System)
[![Vite](https://img.shields.io/badge/Frontend-React%2018%20%7C%20Vite%20%7C%20Tailwind%20CSS-646CFF?style=flat&logo=vite&logoColor=white)](https://navaura-sih-2026.vercel.app)
[![Python](https://img.shields.io/badge/Core%20Engine-Python%203.11%2B%20%7C%20NumPy%20%7C%20SciPy%20%7C%20Scikit--Learn-3776AB?style=flat&logo=python&logoColor=white)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat)](https://opensource.org/licenses/MIT)

**[🚀 Launch Live Telemetry Dashboard](https://navaura-sih-2026.vercel.app)** • **[📖 Problem Statement](#-problem-statement-context)** • **[🧠 Architecture](#-system-architecture)** • **[⚡ Quickstart](#-quick-start-guide)** • **[📊 Benchmark Results](#-benchmark--experimental-evaluation)**

</div>

---

> 🚀 **Live Interactive Deployment**: The tactical telemetry dashboard is live and deployed at **[https://navaura-sih-2026.vercel.app](https://navaura-sih-2026.vercel.app)**. Test real-time GNSS blackout scenarios, AI dead reckoning propagation, and satellite re-anchoring directly in your browser.

---

## 📌 Executive Summary

**NAVAURA** is an engineering-grade, GNSS-resilient tactical navigation system engineered for **Smart India Hackathon 2026 (Problem Statement ID: SIH26168)** under the **Indian Space Research Organisation (ISRO) / Department of Space**.

Conventional satellite navigation systems (GPS, NavIC, Galileo) suffer catastrophic positional divergence or complete blackout when traveling through:
* Urban canyons with severe multipath and signal attenuation
* Mountain tunnels and subterranean passages
* Deep underground parking structures and metro transits
* Contested electronic warfare theaters subject to GNSS jamming and spoofing

Standard Inertial Dead Reckoning (DR) based on naive numerical double integration of commercial MEMS IMU sensors diverges quadratically ($\propto t^2$), producing errors upwards of **80–150 meters within 60 seconds**. 

**NAVAURA eliminates exponential drift** by pairing **adaptive vibration/disturbance filtering**, **2-state EKF heading estimation**, **AI/ML forward speed and displacement inference**, and **innovation-gated Extended Kalman Filter (EKF) re-fusion** into an ultra-reliable, real-time navigation pipeline that achieves **< 2.8m RMSE across 60-second complete GNSS blackouts**.

---

## 🚀 Key Architectural Innovations

```
                         ┌──────────────────────────────────────────────┐
                         │   Raw 9-DoF Sensor Ingestion (IMU + GNSS)    │
                         └──────────────────────┬───────────────────────┘
                                                │
                         ┌──────────────────────▼───────────────────────┐
                         │   1. Adaptive Vibration & Disturbance Filter │
                         │   • Bandpass filter (engine/chassis noise)   │
                         │   • Dynamic thresholding & stationary zero-v │
                         └──────────────────────┬───────────────────────┘
                                                │
         ┌──────────────────────────────────────┴──────────────────────────────────────┐
         │                                                                             │
┌────────▼─────────────────────────────┐             ┌─────────────────────────────────▼────────────────┐
│   2. EKF Heading & Orientation       │             │   3. AI Velocity & Step Regressor                │
│   • Continuous gyro bias estimation  │             │   • Random Forest ML kinematic model             │
│   • Magnetometer anomaly rejection   │             │   • Rolling energy, peak & spectral features     │
│   • Robust yaw tracking (±1.1° fused)│             │   • Zero ground-truth leakage inference          │
└────────────────┬─────────────────────┘             └─────────────────────────────────┬────────────────┘
                 │                                                                     │
                 └──────────────────────────────┬──────────────────────────────────────┘
                                                │
                         ┌──────────────────────▼───────────────────────┐
                         │   4. Extended Kalman Filter (EKF) Navigation │
                         │   • State: x = [p_x, p_y, v, ψ, b_gyro]ᵀ     │
                         │   • Dynamic covariance propagation P_k|k-1   │
                         │   • Chi-squared innovation outage gating     │
                         └──────────────────────┬───────────────────────┘
                                                │
         ┌──────────────────────────────────────┴──────────────────────────────────────┐
         │                                                                             │
┌────────▼─────────────────────────────┐             ┌─────────────────────────────────▼────────────────┐
│      GNSS Nominal Available State    │             │       GNSS-Denied Blackout Outage Mode           │
│   • Continuous measurement updates   │             │   • Autonomous AI-guided DR propagation          │
│   • Online bias & scale calibration  │             │   • Bounded drift growth (< 0.31 m/s)            │
│   • Low covariance bounds            │             │   • Seamless innovation re-anchoring on recovery │
└──────────────────────────────────────┘             └──────────────────────────────────────────────────┘
```

### 1. Adaptive Vibration & Disturbance Filter
Commercial smartphone and vehicle-mounted IMUs are plagued by chassis vibration, road irregularities, and human phone-handling jitter. NAVAURA applies an adaptive digital filtering stage combining a low-pass kinematic filter with dynamic acceleration variance gating, isolating real translation from noise.

### 2. Multi-Sensor Heading Estimator (EKF)
Integrates triaxial gyroscope rates with magnetic field orientation. The filter tracks and removes gyro bias continuously while rejecting localized magnetic disturbances (e.g., steel bridges, railway tracks, power transformers) by gating magnetic field norms.

### 3. Machine Learning Velocity Inference
Rather than naively integrating noisy linear accelerations, NAVAURA employs a trained Random Forest regressor to predict instantaneous vehicle velocity directly from high-frequency temporal and frequency-domain IMU features. The model was trained with strict holdout partitions ensuring zero ground-truth leakage during test inference.

### 4. Innovation-Gated EKF State Fusion
The state vector $\mathbf{x} = \begin{bmatrix} p_x & p_y & v & \psi & b_{\text{gyro}} \end{bmatrix}^T$ is continuously propagated:
$$\mathbf{x}_{k|k-1} = f(\mathbf{x}_{k-1}, \mathbf{u}_k)$$
During GNSS lock, satellite fixes correct both position and estimated sensor biases. When an outage occurs, the filter autonomously transitions to dead reckoning propagation, preventing erratic position jumps and snapping upon satellite re-acquisition.

---

## 📊 Benchmark & Experimental Evaluation

Evaluated across real-world synchronized automotive and smartphone sensor traces (IO-VNBD dataset) across sustained 60-second GNSS denial intervals:

| Performance Metric | Raw IMU Double Integration | Traditional EKF (No ML) | NAVAURA (AI-ML + EKF) | Improvement |
| :--- | :---: | :---: | :---: | :---: |
| **Max Drift Rate** | ~14.2 m/s | ~4.8 m/s | **0.31 m/s** | **93.5% reduction** |
| **60s Outage Final Error** | 142.8 m | 34.6 m | **3.84 m** | **97.3% reduction** |
| **Outage RMSE (Position)** | 89.4 m | 28.1 m | **2.72 m** | **90.3% improvement** |
| **Heading Drift Stability** | $\pm 18.4^\circ$ | $\pm 6.2^\circ$ | **$\pm 1.1^\circ$** | **82.3% improvement** |
| **Single-Step Latency** | < 1 ms | < 2 ms | **3.8 ms** | Real-time ready |

---

## 🖥️ Tactical Web Telemetry Dashboard

The production application is live at **[https://navaura-sih-2026.vercel.app](https://navaura-sih-2026.vercel.app)**.

### Dashboard Capabilities:
- **Interactive Multi-layer GIS**: 
  - Real-time vehicle trajectory rendering with comparative GNSS Ground Truth (Blue), Unconstrained IMU DR (Amber dashed), and NAVAURA AI-Estimate (Emerald).
  - Four keyless GIS tile layers: **Esri Dark Gray Canvas**, **OpenStreetMap Standard**, **World Topographic**, and **High-Resolution Satellite Imagery**.
- **Tactical Simulation Control Toolbar**:
  - `PLAY / PAUSE`: Pause and inspect state vectors at any timestamp.
  - `TRIGGER OUTAGE`: Instantly simulate sudden satellite signal loss.
  - `RESTORE GNSS`: Re-acquire satellite lock and observe innovation re-anchoring.
  - `SPEED MULTIPLIER`: 1x, 2x, and 5x simulation playback rates.
  - `RUN AUTOMATED DEMO`: Automated macro executing an end-to-end tunnel navigation benchmark scenario.
- **Deep Telemetry Analytics**:
  - Real-time Speed, Fused Heading, Position Drift (m), and Cumulative Outage Duration.
  - High-frequency 9-DoF IMU telemetry graphs (Triaxial Accel, Gyro, and Magnetometer).
  - Processing pipeline health status monitor.
- **Fullscreen Tactical Mode**:
  - Single-click or `ESC` hotkey fullscreen telemetry HUD overlay.

---

## 📂 Repository Layout

```
├── data/                               # Synchronized sensor runs and benchmark datasets
│   ├── simulated_run_filtered.npz      # Filtered 9-DoF multi-sensor time series
│   └── vehicle_dr_result.json          # Pre-computed 5,200 sample navigation output
├── models/                             # Serialized machine learning models
│   └── vehicle_speed_model.joblib      # Random Forest speed inference model
├── mobile_app/                         # Native Android/Flutter sensor recording client
├── SIH SOL/
│   └── SIH SOL/                        # React 18 + Vite Tactical Frontend Application
│       ├── public/
│       │   └── vehicle_dr_result.json  # Bundled production telemetry dataset
│       ├── src/
│       │   ├── components/
│       │   │   ├── MapView.jsx         # Multi-layer GIS canvas & trajectory renderer
│       │   │   ├── SimulationControls.jsx # Playback & outage simulation toolbar
│       │   │   ├── NavigationPage.jsx  # Primary tactical dashboard
│       │   │   ├── BenchmarkPage.jsx   # Ablation and error comparisons
│       │   │   ├── SensorsPage.jsx     # High-frequency 9-DoF IMU telemetry
│       │   │   └── AnalyticsPage.jsx   # Error distribution & drift curves
│       │   ├── App.jsx                 # Central application state controller
│       │   └── index.css               # Engineering design system & theme rules
│       ├── package.json
│       └── vite.config.js
├── imu_disturbance_filter.py           # Adaptive vibration pre-processing script
├── heading_estimator.py                # 2-state Gyro + Magnetometer EKF fusion
├── vehicle_speed_estimator.py          # ML feature extraction & velocity regressor
├── vehicle_dead_reckoning.py           # Unified EKF dead-reckoning engine
├── export_results.py                   # Exports synchronized JSON for frontend
├── main.py                             # Master pipeline batch runner
├── requirements.txt                    # Python environment dependencies
├── vercel.json                         # Vercel production deployment configuration
└── README.md
```

---

## ⚡ Quick Start Guide

### 1. Prerequisites
- **Python**: 3.10 or higher
- **Node.js**: 18.x or higher & npm

### 2. Python Core Navigation Engine
```bash
# Clone the repository
git clone https://github.com/Varashree01/AI-ML-Intelligent-Dead-Reckoning-System.git
cd AI-ML-Intelligent-Dead-Reckoning-System

# Install Python scientific dependencies
pip install -r requirements.txt

# Run the complete navigation pipeline (filters, EKF, and ML inference)
python main.py
```

### 3. Local Tactical Web Dashboard
```bash
# Navigate to the frontend directory
cd "SIH SOL/SIH SOL"

# Install dependencies
npm install

# Start local development server
npm run dev
```
Open **[http://localhost:5173](http://localhost:5173)** in your browser.

---

## 🌐 Cloud Deployment (Vercel)

The frontend is deployed live on **Vercel** via:
* **Production URL**: [https://navaura-sih-2026.vercel.app](https://navaura-sih-2026.vercel.app)
* **Configuration**: Handled by root [vercel.json](vercel.json) with automated Vite client-side route rewrites.

To deploy your own fork:
```bash
cd "SIH SOL/SIH SOL"
npx vercel --prod
```

---

## 👥 Project & Team Details

* **Competition**: Smart India Hackathon 2026 (SIH 2026)
* **Problem Statement ID**: **SIH26168**
* **Theme**: Transportation & Logistics / Space Technology
* **Organization**: **Indian Space Research Organisation (ISRO) / Department of Space**
* **Team**: **TEAM 06**
* **Lead Engineer & Researcher**: Varashree H A & Team 06

Developed with pride for India's indigenous navigation and aerospace research initiatives.
