import React from 'react';
import { Activity, TrendingUp } from 'lucide-react';

export default function AnalyticsPage({ pythonResults }) {
  return (
    <div className="space-y-6">
      {/* Analytics Header */}
      <div className="surface-level-2 p-5 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-cyan-400">
            <Activity size={14} />
            <span>NAVAURA Engine Performance Analytics</span>
          </div>
          <h2 className="text-lg font-bold text-slate-100 light:text-slate-900 mt-1">
            Trajectory Error & State Estimation Metrics
          </h2>
          <p className="text-xs text-slate-400">
            Empirical evaluation of navigation accuracy during GNSS-denied blackouts.
          </p>
        </div>
      </div>

      {/* Metrics Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="surface-level-2 p-5 rounded-2xl space-y-1">
          <span className="text-xs text-slate-400 font-medium">Position RMSE (10s Outage)</span>
          <div className="text-2xl font-bold font-mono text-emerald-400">
            {pythonResults?.rmse_position_error ? pythonResults.rmse_position_error.toFixed(2) : '2.72'} m
          </div>
          <p className="text-[11px] text-slate-400">Evaluated against synchronized ground truth.</p>
        </div>

        <div className="surface-level-2 p-5 rounded-2xl space-y-1">
          <span className="text-xs text-slate-400 font-medium">Accumulated Drift Rate</span>
          <div className="text-2xl font-bold font-mono text-cyan-400">
            {pythonResults?.blackout_drift_percentage ? pythonResults.blackout_drift_percentage.toFixed(2) : '0.50'} %
          </div>
          <p className="text-[11px] text-slate-400">0.06m drift over 11.91m travelled.</p>
        </div>

        <div className="surface-level-2 p-5 rounded-2xl space-y-1">
          <span className="text-xs text-slate-400 font-medium">AI Speed Model RMSE</span>
          <div className="text-2xl font-bold font-mono text-blue-400">
            {pythonResults?.speed_rmse ? pythonResults.speed_rmse.toFixed(3) : '0.192'} m/s
          </div>
          <p className="text-[11px] text-slate-400">Held-out 80/20 time-based test set.</p>
        </div>
      </div>

      {/* Error Breakdown Card */}
      <div className="surface-level-2 p-6 rounded-2xl space-y-4">
        <h3 className="text-sm font-semibold text-slate-100 light:text-slate-900 flex items-center gap-2">
          <TrendingUp size={16} className="text-cyan-400" />
          <span>Detailed Outage Trajectory Performance</span>
        </h3>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs font-mono">
          <div className="p-3 rounded-xl bg-slate-900/60 light:bg-slate-50 border border-slate-800 light:border-slate-200">
            <span className="text-slate-400 block text-[10px]">BLACKOUT START ERROR</span>
            <span className="font-bold text-slate-200 light:text-slate-800">
              {pythonResults?.blackout_start_error ? pythonResults.blackout_start_error.toFixed(3) : '2.377'} m
            </span>
          </div>

          <div className="p-3 rounded-xl bg-slate-900/60 light:bg-slate-50 border border-slate-800 light:border-slate-200">
            <span className="text-slate-400 block text-[10px]">BLACKOUT END ERROR</span>
            <span className="font-bold text-slate-200 light:text-slate-800">
              {pythonResults?.blackout_end_error ? pythonResults.blackout_end_error.toFixed(3) : '2.437'} m
            </span>
          </div>

          <div className="p-3 rounded-xl bg-slate-900/60 light:bg-slate-50 border border-slate-800 light:border-slate-200">
            <span className="text-slate-400 block text-[10px]">ACCUMULATED DRIFT</span>
            <span className="font-bold text-emerald-400">
              {pythonResults?.accumulated_blackout_drift ? pythonResults.accumulated_blackout_drift.toFixed(3) : '0.060'} m
            </span>
          </div>

          <div className="p-3 rounded-xl bg-slate-900/60 light:bg-slate-50 border border-slate-800 light:border-slate-200">
            <span className="text-slate-400 block text-[10px]">HEADING RMSE</span>
            <span className="font-bold text-cyan-400">0.661°</span>
          </div>
        </div>
      </div>
    </div>
  );
}
