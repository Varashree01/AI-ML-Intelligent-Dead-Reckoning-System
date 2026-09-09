import React from 'react';
import { X, Network, CheckCircle, ArrowDown, ArrowRight, ShieldCheck, Cpu } from 'lucide-react';

export default function ArchitectureModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[5000] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md overflow-y-auto">
      <div className="glass-panel w-full max-w-4xl rounded-2xl border border-cyan-500/30 p-6 space-y-6 max-h-[90vh] overflow-y-auto shadow-2xl relative">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-cyan-950/80 border border-cyan-500/30 text-cyan-400">
              <Network className="w-6 h-6" />
            </div>
            <div>
              <h2 className="font-tech text-xl font-bold text-white uppercase tracking-wider">
                System Architecture & Hardware Dataflow
              </h2>
              <p className="text-xs text-slate-400">
                SIH26168 Intelligent Dead Reckoning & AI Trajectory Failover Pipeline
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-400 hover:text-white transition-all"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Visual Architecture Tree Diagram */}
        <div className="space-y-4 p-4 rounded-xl bg-slate-950/90 border border-slate-800">
          <h3 className="font-tech text-sm font-bold text-cyan-300 uppercase tracking-widest text-center">
            Decision & Execution Flowchart
          </h3>

          {/* Node 1: GNSS Input */}
          <div className="flex justify-center">
            <div className="p-3 rounded-xl bg-blue-950/60 border border-blue-500/50 text-blue-300 font-tech font-bold text-sm text-center shadow-[0_0_15px_rgba(59,130,246,0.2)]">
              🛰️ GNSS / GPS Satellite Receiver Signal
            </div>
          </div>

          <div className="flex justify-center text-cyan-400">
            <ArrowDown className="w-5 h-5" />
          </div>

          {/* Decision Node */}
          <div className="flex justify-center">
            <div className="p-3 rounded-xl bg-slate-900 border border-cyan-500/40 text-cyan-300 font-mono text-xs font-bold text-center">
              GNSS Signal Available?
            </div>
          </div>

          {/* Decision Branches */}
          <div className="grid grid-cols-2 gap-4 max-w-2xl mx-auto">
            {/* YES Branch */}
            <div className="space-y-3 p-3 rounded-xl bg-emerald-950/20 border border-emerald-500/30 text-center">
              <span className="text-xs font-bold text-emerald-400 font-mono block">YES (Signal Nominal)</span>
              <ArrowDown className="w-4 h-4 text-emerald-400 mx-auto" />
              <div className="p-2.5 rounded-lg bg-emerald-950/80 border border-emerald-500/40 text-emerald-300 font-tech font-bold text-xs">
                Direct GNSS Position Navigation
              </div>
            </div>

            {/* NO Branch */}
            <div className="space-y-3 p-3 rounded-xl bg-amber-950/20 border border-amber-500/30 text-center">
              <span className="text-xs font-bold text-red-400 font-mono block">NO (Tunnel / Blackout)</span>
              <ArrowDown className="w-4 h-4 text-amber-400 mx-auto" />
              <div className="p-2.5 rounded-lg bg-amber-950/80 border border-amber-500/40 text-amber-300 font-tech font-bold text-xs">
                📱 Failover to Smartphone IMU
              </div>
            </div>
          </div>

          <div className="flex justify-center text-cyan-400">
            <ArrowDown className="w-5 h-5" />
          </div>

          {/* IMU Sensors Node */}
          <div className="max-w-xl mx-auto p-3 rounded-xl bg-slate-900 border border-slate-700 text-center">
            <span className="text-xs font-mono text-cyan-400 font-bold block mb-1">
              Raw Inertial Sensors Stream
            </span>
            <div className="flex justify-center gap-4 text-xs font-mono text-slate-300">
              <span className="bg-slate-800 px-2 py-1 rounded">Accelerometer (3-Axis)</span>
              <span className="bg-slate-800 px-2 py-1 rounded">Gyroscope (3-Axis)</span>
              <span className="bg-slate-800 px-2 py-1 rounded">Magnetometer</span>
            </div>
          </div>

          <div className="flex justify-center text-cyan-400">
            <ArrowDown className="w-5 h-5" />
          </div>

          {/* Sensor Fusion Node */}
          <div className="max-w-xl mx-auto p-3 rounded-xl bg-cyan-950/60 border border-cyan-500/40 text-center">
            <span className="text-xs font-tech font-bold text-cyan-300 uppercase block">
              Multi-Sensor Fusion (Extended Kalman Filter)
            </span>
            <span className="text-[11px] text-slate-400 font-mono">
              Filters sensor noise, estimates orientation vector & velocity
            </span>
          </div>

          <div className="flex justify-center text-cyan-400">
            <ArrowDown className="w-5 h-5" />
          </div>

          {/* Dead Reckoning Engine */}
          <div className="max-w-xl mx-auto p-3 rounded-xl bg-orange-950/60 border border-orange-500/40 text-center">
            <span className="text-xs font-tech font-bold text-orange-300 uppercase block">
              Pedestrian / Vehicle Dead Reckoning (PDR)
            </span>
            <span className="text-[11px] text-slate-400 font-mono">
              Pos(t) = Pos(t-1) + Speed × Direction × Δt
            </span>
          </div>

          <div className="flex justify-center text-cyan-400">
            <ArrowDown className="w-5 h-5" />
          </div>

          {/* AI Drift Correction */}
          <div className="max-w-xl mx-auto p-3 rounded-xl bg-indigo-950/60 border border-indigo-500/40 text-center shadow-[0_0_15px_rgba(99,102,241,0.2)]">
            <span className="text-xs font-tech font-bold text-indigo-300 uppercase block flex items-center justify-center gap-1.5">
              <Cpu className="w-4 h-4 text-indigo-400 animate-spin" />
              AI Neural Trajectory Correction (Bi-LSTM Model)
            </span>
            <span className="text-[11px] text-slate-300 font-mono">
              Predicts accumulated sensor bias & applies real-time trajectory correction vector
            </span>
          </div>

          <div className="flex justify-center text-emerald-400">
            <ArrowDown className="w-5 h-5" />
          </div>

          {/* Final Output */}
          <div className="max-w-xl mx-auto p-3.5 rounded-xl bg-gradient-to-r from-emerald-950 to-teal-950 border border-emerald-400 text-center shadow-[0_0_20px_rgba(16,185,129,0.3)]">
            <span className="font-tech text-base font-bold text-emerald-300 uppercase block flex items-center justify-center gap-2">
              <CheckCircle className="w-5 h-5 text-emerald-400" />
              Continuous Seamless Navigation Output
            </span>
          </div>
        </div>

        {/* Technical Specs Footer */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-wrap justify-between items-center gap-3 text-xs font-mono text-slate-400">
          <div>SIH 2026 Problem ID: <strong className="text-cyan-400">SIH26168</strong></div>
          <div>Update Frequency: <strong className="text-emerald-400">100Hz IMU / 10Hz Display</strong></div>
          <div>Zero External API Key Requirement: <strong className="text-amber-400">Offline Leaflet GIS</strong></div>
        </div>
      </div>
    </div>
  );
}
