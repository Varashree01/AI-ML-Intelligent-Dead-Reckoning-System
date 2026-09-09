import React from 'react';
import { 
  Activity, 
  Gauge, 
  Compass, 
  Clock, 
  Zap,
  Maximize2
} from 'lucide-react';
import MapView from './MapView';
import SimulationControls from './SimulationControls';

export default function NavigationPage({
  gpsState,
  navMode,
  speedKmh,
  headingDeg,
  driftErrorMeters,
  outageDuration,
  distanceTravelledMeters,
  sensorData,
  pythonResults,
  pythonIndex,
  autoPan,
  setAutoPan,
  isFullscreenMap,
  setIsFullscreenMap,
  mapStyle,
  isPlaying,
  setIsPlaying,
  onSimulateGpsLoss,
  onRestoreGps,
  onResetSim,
  speedMultiplier,
  setSpeedMultiplier
}) {
  const getNavModeBadge = () => {
    switch (gpsState) {
      case 'AVAILABLE':
        return { label: 'GNSS Navigation', color: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' };
      case 'LOST':
        return { label: 'GNSS-Denied Dead Reckoning', color: 'bg-amber-500/15 text-amber-400 border-amber-500/40' };
      case 'RESTORED':
        return { label: 'GNSS Restored Re-fusion', color: 'bg-cyan-500/15 text-cyan-400 border-cyan-500/40' };
      default:
        return { label: 'Dead Reckoning Active', color: 'bg-blue-500/10 text-blue-400 border-blue-500/30' };
    }
  };

  const navBadge = getNavModeBadge();

  return (
    <div className="space-y-6">
      {/* Simulation Controls Toolbar */}
      <SimulationControls
        isPlaying={isPlaying}
        setIsPlaying={setIsPlaying}
        gpsState={gpsState}
        onSimulateGpsLoss={onSimulateGpsLoss}
        onRestoreGps={onRestoreGps}
        onResetSim={onResetSim}
        speedMultiplier={speedMultiplier}
        setSpeedMultiplier={setSpeedMultiplier}
      />

      {/* Top Telemetry Summary Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {/* Speed */}
        <div className="surface-level-2 p-4 rounded-2xl space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
            <span>Vehicle Speed</span>
            <Gauge size={16} className="text-cyan-400" />
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl sm:text-3xl font-bold font-mono text-slate-100">{speedKmh.toFixed(1)}</span>
            <span className="text-xs text-slate-400 font-mono">km/h</span>
          </div>
          <div className="text-[11px] text-slate-400 font-mono">
            AI Speed: {(speedKmh / 3.6).toFixed(2)} m/s
          </div>
        </div>

        {/* Heading */}
        <div className="surface-level-2 p-4 rounded-2xl space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
            <span>Fused Heading</span>
            <Compass size={16} className="text-blue-400" />
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl sm:text-3xl font-bold font-mono text-slate-100">{headingDeg.toFixed(1)}°</span>
          </div>
          <div className="text-[11px] text-slate-400 font-mono">
            EKF Gyro + Mag Fusion
          </div>
        </div>

        {/* Current Error */}
        <div className="surface-level-2 p-4 rounded-2xl space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
            <span>Position Error</span>
            <Activity size={16} className={driftErrorMeters > 5 ? "text-amber-400" : "text-emerald-400"} />
          </div>
          <div className="flex items-baseline gap-1">
            <span className={`text-2xl sm:text-3xl font-bold font-mono ${driftErrorMeters > 5 ? "text-amber-400" : "text-emerald-400"}`}>
              {driftErrorMeters.toFixed(2)}
            </span>
            <span className="text-xs text-slate-400 font-mono">m</span>
          </div>
          <div className="text-[11px] text-slate-400 font-mono">
            RMSE: {pythonResults?.rmse_position_error?.toFixed(2) || '2.72'}m
          </div>
        </div>

        {/* Outage Duration */}
        <div className="surface-level-2 p-4 rounded-2xl space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
            <span>GNSS Outage Duration</span>
            <Clock size={16} className={outageDuration > 0 ? "text-amber-400" : "text-slate-400"} />
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl sm:text-3xl font-bold font-mono text-slate-100">{outageDuration.toFixed(1)}</span>
            <span className="text-xs text-slate-400 font-mono">s</span>
          </div>
          <div className="text-[11px] text-slate-400 font-mono">
            Travelled: {distanceTravelledMeters.toFixed(1)}m
          </div>
        </div>
      </div>

      {/* Main Workspace Layout (Map 60-70% + Right Sidebar HUD) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Map Workspace Area */}
        <div className="lg:col-span-8 space-y-3">
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center gap-2">
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-mono font-medium border ${navBadge.color}`}>
                {navBadge.label}
              </span>
            </div>
            <button
              onClick={() => setIsFullscreenMap(true)}
              className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-xs text-cyan-400 font-semibold border border-cyan-500/30 transition-all active:scale-95"
            >
              <Maximize2 size={14} />
              <span>EXPAND MAP FULLSCREEN</span>
            </button>
          </div>

          <div className="h-[520px] rounded-2xl overflow-hidden border border-slate-800 light:border-slate-200 shadow-xl relative">
            <MapView
              gpsState={gpsState}
              driftErrorMeters={driftErrorMeters}
              speedKmh={speedKmh}
              headingDeg={headingDeg}
              outageDuration={outageDuration}
              autoPan={autoPan}
              setAutoPan={setAutoPan}
              isFullscreen={false}
              onToggleFullscreen={() => setIsFullscreenMap(true)}
              mapStyle={mapStyle}
              pythonResults={pythonResults}
              pythonIndex={pythonIndex}
            />
          </div>
        </div>

        {/* Right Telemetry & Processing Pipeline Panels */}
        <div className="lg:col-span-4 space-y-6">
          {/* NAVAURA Processing Chain Status */}
          <div className="surface-level-2 p-5 rounded-2xl space-y-4">
            <h3 className="text-sm font-semibold text-slate-200 light:text-slate-900 flex items-center gap-2">
              <Zap size={16} className="text-cyan-400" />
              <span>Processing Pipeline</span>
            </h3>

            <div className="space-y-3 text-xs font-mono">
              <div className="p-3 rounded-xl bg-slate-900/60 light:bg-slate-50 border border-slate-800 light:border-slate-200 flex items-center justify-between">
                <div>
                  <div className="text-slate-400 text-[10px]">1. IMU PREPROCESSING</div>
                  <div className="font-semibold text-slate-200 light:text-slate-800">Adaptive Vibration Filter</div>
                </div>
                <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-[10px]">ACTIVE</span>
              </div>

              <div className="p-3 rounded-xl bg-slate-900/60 light:bg-slate-50 border border-slate-800 light:border-slate-200 flex items-center justify-between">
                <div>
                  <div className="text-slate-400 text-[10px]">2. AI MOTION INFERENCE</div>
                  <div className="font-semibold text-slate-200 light:text-slate-800">Random Forest Speed Model</div>
                </div>
                <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-[10px]">ACTIVE</span>
              </div>

              <div className="p-3 rounded-xl bg-slate-900/60 light:bg-slate-50 border border-slate-800 light:border-slate-200 flex items-center justify-between">
                <div>
                  <div className="text-slate-400 text-[10px]">3. STATE ESTIMATION</div>
                  <div className="font-semibold text-slate-200 light:text-slate-800">2-State EKF (Heading & Bias)</div>
                </div>
                <span className="px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 text-[10px]">PREDICTING</span>
              </div>

              <div className="p-3 rounded-xl bg-slate-900/60 light:bg-slate-50 border border-slate-800 light:border-slate-200 flex items-center justify-between">
                <div>
                  <div className="text-slate-400 text-[10px]">4. NAVIGATION MODE</div>
                  <div className="font-semibold text-slate-200 light:text-slate-800">
                    {gpsState === 'LOST' ? 'Dead Reckoning Propagation' : 'GNSS + INS Re-Fusion'}
                  </div>
                </div>
                <span className={`px-2 py-0.5 rounded text-[10px] ${
                  gpsState === 'LOST' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                }`}>
                  {gpsState === 'LOST' ? 'DEAD RECKONING' : 'FUSED'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
