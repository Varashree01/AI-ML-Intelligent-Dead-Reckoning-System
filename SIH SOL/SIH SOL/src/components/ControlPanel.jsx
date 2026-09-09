import React, { useState } from 'react';

import {
  Play,
  Radio,
  RotateCcw,
  Sparkles,
  CheckCircle2,
  Zap
} from 'lucide-react';

import confetti from 'canvas-confetti';

export default function ControlPanel({
  isNavigating,
  gpsState,
  onStartNav,
  onSimulateGpsLoss,
  onRestoreGps,
  onResetSim,
  demoStep,
  setDemoStep,
  setToastMessage
}) {
  const [isDemoRunning, setIsDemoRunning] = useState(false);
  const [demoProgress, setDemoProgress] = useState(0);

  // ============================================================
  // Automated Tunnel Navigation Demo Macro Engine
  // ============================================================

  const runTunnelDemo = () => {
    if (isDemoRunning) return;

    setIsDemoRunning(true);
    setDemoProgress(0);

    setToastMessage({
      type: 'info',
      title: 'TUNNEL NAVIGATION DEMO STARTED',
      desc: 'Executing full automated SIH demonstration sequence...'
    });

    // Step 1: Start Navigation
    setTimeout(() => {
      onResetSim();

      setTimeout(() => {
        onStartNav();
      }, 100);

      setDemoProgress(20);

      setToastMessage({
        type: 'success',
        title: 'STEP 1: GNSS NAVIGATION ACTIVE',
        desc: 'Vehicle navigation started with GNSS-assisted positioning.'
      });
    }, 500);

    // Step 2: Simulate GNSS Loss
    setTimeout(() => {
      onSimulateGpsLoss();

      setDemoProgress(50);

      setToastMessage({
        type: 'warning',
        title: 'STEP 2: ENTERING TUNNEL — GNSS LOSS',
        desc:
          'GNSS unavailable. System switches to IMU-based speed estimation, heading fusion, and dead reckoning.'
      });
    }, 6500);

    // Step 3: AI + Sensor Fusion
    setTimeout(() => {
      setDemoProgress(75);

      setToastMessage({
        type: 'info',
        title: 'STEP 3: AI/ML DEAD RECKONING ACTIVE',
        desc:
          'Random Forest vehicle speed estimation and fused heading are driving GNSS-denied navigation.'
      });
    }, 14000);

    // Step 4: Restore GNSS
    setTimeout(() => {
      onRestoreGps();

      setDemoProgress(90);

      setToastMessage({
        type: 'success',
        title: 'STEP 4: EXITING TUNNEL — GNSS RESTORED',
        desc:
          'GNSS lock re-established. Estimated position is smoothly corrected using GNSS.'
      });
    }, 22000);

    // Step 5: Demo Complete
    setTimeout(() => {
      setIsDemoRunning(false);
      setDemoProgress(100);

      setToastMessage({
        type: 'success',
        title: 'DEMO COMPLETE — SEAMLESS NAVIGATION DEMONSTRATED',
        desc:
          'Navigation continued through the simulated GNSS blackout and recovered after GNSS restoration.'
      });

      confetti({
        particleCount: 80,
        spread: 70,
        origin: { y: 0.6 }
      });
    }, 28000);
  };

  return (
    <div className="glass-panel p-5 rounded-2xl border border-cyan-500/20 shadow-xl space-y-4">

      {/* ========================================================
          Top Banner for SIH Demo Macro
      ======================================================== */}

      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 rounded-xl bg-gradient-to-r from-cyan-950/80 via-slate-900 to-indigo-950/80 border border-cyan-500/30">

        <div className="space-y-1">

          <div className="flex items-center gap-2">

            <span className="flex h-2.5 w-2.5 rounded-full bg-cyan-400 animate-ping" />

            <span className="text-xs font-mono tracking-widest text-cyan-400 uppercase font-bold">
              SIH 2026 Automated Demo Mode
            </span>

          </div>

          <h3 className="font-tech text-lg font-bold text-slate-100 flex items-center gap-2">

            <Zap className="w-5 h-5 text-amber-400" />

            Interactive Navigation Control Center

          </h3>

          <p className="text-xs text-slate-400">
            Simulate GNSS outage and seamless navigation using IMU sensing,
            AI-based vehicle speed estimation, heading fusion, and dead reckoning.
          </p>

        </div>

        {/* Automated Demo Button */}

        <button
          onClick={runTunnelDemo}
          disabled={isDemoRunning}
          className={`relative group overflow-hidden px-5 py-3 rounded-xl font-tech text-sm font-bold tracking-wider uppercase transition-all shadow-lg flex items-center gap-2.5 ${
            isDemoRunning
              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 cursor-wait'
              : 'bg-gradient-to-r from-amber-500 via-orange-500 to-amber-600 hover:from-amber-400 hover:to-orange-500 text-slate-950 border border-amber-300/50 shadow-[0_0_20px_rgba(245,158,11,0.4)] hover:scale-[1.02] active:scale-[0.98]'
          }`}
        >

          <Sparkles
            className={`w-5 h-5 ${
              isDemoRunning
                ? 'animate-spin text-amber-400'
                : 'text-slate-950'
            }`}
          />

          {isDemoRunning
            ? `RUNNING DEMO (${demoProgress}%)`
            : 'RUN TUNNEL NAVIGATION DEMO'}

        </button>

      </div>

      {/* ========================================================
          Progress Bar
      ======================================================== */}

      {isDemoRunning && (
        <div className="w-full bg-slate-800/80 h-2 rounded-full overflow-hidden p-0.5 border border-slate-700">

          <div
            className="bg-gradient-to-r from-cyan-400 via-amber-400 to-emerald-400 h-full rounded-full transition-all duration-500 shadow-[0_0_10px_#38bdf8]"
            style={{
              width: `${demoProgress}%`
            }}
          />

        </div>
      )}

      {/* ========================================================
          Manual Control Action Buttons
      ======================================================== */}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">

        {/* 1. Start Navigation */}

        <button
          onClick={onStartNav}
          disabled={isNavigating || isDemoRunning}
          className={`flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-tech text-sm font-bold uppercase tracking-wider transition-all border shadow-md ${
            isNavigating
              ? 'bg-blue-500/20 border-blue-500/40 text-blue-300 cursor-not-allowed'
              : 'bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white border-blue-400/40 hover:shadow-[0_0_15px_rgba(59,130,246,0.4)] active:scale-95'
          }`}
        >

          <Play className="w-4 h-4 fill-current" />

          Start Navigation

        </button>

        {/* 2. Simulate GNSS Loss */}

        <button
          onClick={onSimulateGpsLoss}
          disabled={
            !isNavigating ||
            gpsState === 'LOST' ||
            isDemoRunning
          }
          className={`flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-tech text-sm font-bold uppercase tracking-wider transition-all border shadow-md ${
            gpsState === 'LOST' || !isNavigating
              ? 'bg-red-950/30 border-slate-800 text-slate-500 cursor-not-allowed'
              : 'bg-gradient-to-r from-red-600 to-orange-600 hover:from-red-500 hover:to-orange-500 text-white border-red-400/40 hover:shadow-[0_0_15px_rgba(239,68,68,0.4)] active:scale-95'
          }`}
        >

          <Radio className="w-4 h-4 text-red-200 animate-pulse" />

          Simulate GNSS Loss

        </button>

        {/* 3. Restore GNSS */}

        <button
          onClick={onRestoreGps}
          disabled={
            gpsState !== 'LOST' ||
            isDemoRunning
          }
          className={`flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-tech text-sm font-bold uppercase tracking-wider transition-all border shadow-md ${
            gpsState !== 'LOST'
              ? 'bg-emerald-950/30 border-slate-800 text-slate-500 cursor-not-allowed'
              : 'bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white border-emerald-400/40 hover:shadow-[0_0_15px_rgba(16,185,129,0.4)] active:scale-95'
          }`}
        >

          <CheckCircle2 className="w-4 h-4 text-emerald-200" />

          Restore GNSS

        </button>

        {/* 4. Reset Simulation */}

        <button
          onClick={onResetSim}
          disabled={isDemoRunning}
          className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-tech text-sm font-bold uppercase tracking-wider transition-all bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 border border-slate-700 hover:border-slate-500 active:scale-95"
        >

          <RotateCcw className="w-4 h-4" />

          Reset Sim

        </button>

      </div>

    </div>
  );
}