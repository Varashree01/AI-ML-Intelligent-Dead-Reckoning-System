import React, { useState } from 'react';
import { 
  Play, 
  Pause, 
  RotateCcw, 
  Radio, 
  CheckCircle2, 
  Sparkles,
  Zap,
  Gauge
} from 'lucide-react';
import confetti from 'canvas-confetti';

export default function SimulationControls({
  isPlaying,
  setIsPlaying,
  gpsState,
  onSimulateGpsLoss,
  onRestoreGps,
  onResetSim,
  speedMultiplier,
  setSpeedMultiplier,
  compact = false
}) {
  const [isDemoRunning, setIsDemoRunning] = useState(false);
  const [demoProgress, setDemoProgress] = useState(0);

  // Automated Tunnel Demo Macro Sequence
  const runTunnelDemo = () => {
    if (isDemoRunning) return;
    setIsDemoRunning(true);
    setDemoProgress(0);

    // Step 1: Reset & Start
    onResetSim();
    setIsPlaying(true);
    setDemoProgress(20);

    // Step 2: Simulate Outage at 5s
    setTimeout(() => {
      onSimulateGpsLoss();
      setDemoProgress(50);
    }, 4000);

    // Step 3: AI Dead Reckoning Active
    setTimeout(() => {
      setDemoProgress(75);
    }, 9000);

    // Step 4: Restore GNSS at 14s
    setTimeout(() => {
      onRestoreGps();
      setDemoProgress(90);
    }, 14000);

    // Step 5: Complete
    setTimeout(() => {
      setIsDemoRunning(false);
      setDemoProgress(100);
      try {
        confetti({
          particleCount: 60,
          spread: 60,
          origin: { y: 0.6 }
        });
      } catch (e) {
        // Safe fallback if confetti isn't available
      }
    }, 18000);
  };

  if (compact) {
    return (
      <div className="flex items-center gap-2">
        <button
          onClick={() => setIsPlaying(!isPlaying)}
          className={`p-2 rounded-xl border flex items-center gap-1.5 text-xs font-semibold font-mono transition-all ${
            isPlaying 
              ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' 
              : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
          }`}
          title={isPlaying ? "Pause simulation" : "Play simulation"}
        >
          {isPlaying ? <Pause size={14} /> : <Play size={14} />}
          <span>{isPlaying ? 'PAUSE' : 'PLAY'}</span>
        </button>

        <button
          onClick={gpsState === 'LOST' ? onRestoreGps : onSimulateGpsLoss}
          className={`p-2 rounded-xl border flex items-center gap-1.5 text-xs font-semibold font-mono transition-all ${
            gpsState === 'LOST'
              ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
              : 'bg-red-500/20 text-red-300 border-red-500/40 animate-pulse'
          }`}
          title={gpsState === 'LOST' ? 'Restore GNSS Signal' : 'Trigger GNSS Outage'}
        >
          {gpsState === 'LOST' ? <CheckCircle2 size={14} /> : <Radio size={14} />}
          <span>{gpsState === 'LOST' ? 'RESTORE GNSS' : 'OUTAGE'}</span>
        </button>

        <button
          onClick={onResetSim}
          className="p-2 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs font-mono"
          title="Reset Simulation"
        >
          <RotateCcw size={14} />
        </button>
      </div>
    );
  }

  return (
    <div className="surface-level-2 p-5 rounded-2xl border border-slate-800 light:border-slate-200 space-y-4">
      {/* Top Banner: SIH Automated Demo Macro */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 rounded-xl bg-gradient-to-r from-cyan-950/70 via-slate-900 to-blue-950/70 border border-cyan-500/30">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
            <span className="text-xs font-mono font-bold text-cyan-400 uppercase tracking-wider">
              SIH 2026 Interactive Simulation Engine
            </span>
          </div>
          <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
            <Zap size={18} className="text-amber-400" />
            <span>Navigation Control Toolbar</span>
          </h3>
          <p className="text-xs text-slate-400">
            Control live playback, trigger GNSS blackout outages, or execute the automated tunnel demo macro.
          </p>
        </div>

        {/* Automated Macro Button */}
        <button
          onClick={runTunnelDemo}
          disabled={isDemoRunning}
          className={`px-4 py-2.5 rounded-xl font-bold text-xs uppercase tracking-wider transition-all flex items-center gap-2 shadow-lg shrink-0 ${
            isDemoRunning
              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 cursor-wait'
              : 'bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-slate-950 shadow-amber-500/20 hover:scale-[1.02] active:scale-[0.98]'
          }`}
        >
          <Sparkles size={16} className={isDemoRunning ? 'animate-spin' : ''} />
          <span>{isDemoRunning ? `RUNNING DEMO (${demoProgress}%)` : 'RUN AUTOMATED DEMO'}</span>
        </button>
      </div>

      {/* Manual Control Action Buttons Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-xs font-mono">
        {/* Play/Pause */}
        <button
          onClick={() => setIsPlaying(!isPlaying)}
          className={`p-3 rounded-xl border flex items-center justify-center gap-2 font-bold uppercase transition-all ${
            isPlaying
              ? 'bg-amber-500/15 text-amber-400 border-amber-500/30 hover:bg-amber-500/25'
              : 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/25'
          }`}
        >
          {isPlaying ? <Pause size={16} /> : <Play size={16} />}
          <span>{isPlaying ? 'PAUSE' : 'PLAY SIM'}</span>
        </button>

        {/* Simulate Outage */}
        <button
          onClick={onSimulateGpsLoss}
          disabled={gpsState === 'LOST'}
          className={`p-3 rounded-xl border flex items-center justify-center gap-2 font-bold uppercase transition-all ${
            gpsState === 'LOST'
              ? 'bg-slate-900 border-slate-800 text-slate-600 cursor-not-allowed'
              : 'bg-red-500/15 text-red-400 border-red-500/30 hover:bg-red-500/25 animate-pulse'
          }`}
        >
          <Radio size={16} />
          <span>TRIGGER OUTAGE</span>
        </button>

        {/* Restore GNSS */}
        <button
          onClick={onRestoreGps}
          disabled={gpsState !== 'LOST'}
          className={`p-3 rounded-xl border flex items-center justify-center gap-2 font-bold uppercase transition-all ${
            gpsState !== 'LOST'
              ? 'bg-slate-900 border-slate-800 text-slate-600 cursor-not-allowed'
              : 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/25'
          }`}
        >
          <CheckCircle2 size={16} />
          <span>RESTORE GNSS</span>
        </button>

        {/* Reset Simulation */}
        <button
          onClick={onResetSim}
          className="p-3 rounded-xl bg-slate-800/80 light:bg-slate-100 hover:bg-slate-700 light:hover:bg-slate-200 text-slate-300 light:text-slate-800 border border-slate-700/60 light:border-slate-300 flex items-center justify-center gap-2 font-bold uppercase transition-colors"
        >
          <RotateCcw size={16} />
          <span>RESET SIM</span>
        </button>

        {/* Speed Multiplier */}
        <div className="flex items-center justify-between p-2.5 rounded-xl bg-slate-900/60 light:bg-slate-100 border border-slate-800 light:border-slate-200 text-slate-300">
          <span className="text-[10px] text-slate-400">SPEED:</span>
          <div className="flex items-center gap-1">
            {[1, 2, 5].map((s) => (
              <button
                key={s}
                onClick={() => setSpeedMultiplier(s)}
                className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                  speedMultiplier === s
                    ? 'bg-cyan-500 text-slate-950'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {s}x
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
