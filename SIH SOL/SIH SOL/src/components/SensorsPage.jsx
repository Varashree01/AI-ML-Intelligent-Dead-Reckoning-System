import React from 'react';
import { Cpu, Activity, Radio, AlertOctagon, RefreshCw } from 'lucide-react';
import SensorDashboard from './SensorDashboard';

export default function SensorsPage({ sensorData, pythonResults }) {
  return (
    <div className="space-y-6">
      {/* Header Info */}
      <div className="surface-level-2 p-5 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-cyan-400">
            <Cpu size={14} />
            <span>Smartphone Sensor Ingestion Pipeline</span>
          </div>
          <h2 className="text-lg font-bold text-slate-100 light:text-slate-900 mt-1">
            Real-Time & Recorded IMU Telemetry Stream
          </h2>
          <p className="text-xs text-slate-400">
            10 Hz synchronized accelerometer, gyroscope, magnetometer, and adaptive vibration filtering metrics.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono">
          <span className="px-3 py-1.5 rounded-xl bg-slate-900 light:bg-slate-100 border border-slate-800 light:border-slate-200 text-slate-300">
            Vibration Cut: <strong className="text-emerald-400">71.7% RMS</strong>
          </span>
        </div>
      </div>

      {/* Main Sensor Dashboard Component */}
      <SensorDashboard sensorData={sensorData} />
    </div>
  );
}
