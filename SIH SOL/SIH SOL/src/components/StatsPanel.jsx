import React from "react";

import {
  Radio,
  Gauge,
  Compass,
  Route,
  Clock,
  AlertTriangle,
  Cpu,
  Layers,
} from "lucide-react";

export default function StatsPanel({
  gpsState = "AVAILABLE",
  navMode = "GNSS NAVIGATION",
  speedKmh = 0,
  headingDeg = 0,
  cardinalHeading = "N",
  distanceTravelledMeters = 0,
  outageDuration = 0,
  driftErrorMeters = 0,
  aiConfidence = null,
  sensorFusionStatus = "GNSS + IMU NAVIGATION",
}) {
  const safeNumber = (value, fallback = 0) => {
    const number = Number(value);

    if (Number.isFinite(number)) {
      return number;
    }

    return fallback;
  };

  const speed = safeNumber(speedKmh);
  const heading = safeNumber(headingDeg);

  const distance = Math.max(
    0,
    safeNumber(distanceTravelledMeters)
  );

  const outage = Math.max(
    0,
    safeNumber(outageDuration)
  );

  const driftError = Math.max(
    0,
    safeNumber(driftErrorMeters)
  );

  // AI confidence is shown only when a real value is provided.
  // No fake default confidence percentage.
  const confidence =
    aiConfidence === null || aiConfidence === undefined
      ? null
      : Math.max(
          0,
          Math.min(100, safeNumber(aiConfidence))
        );

  const formattedDistance =
    distance >= 1000
      ? `${(distance / 1000).toFixed(2)} km`
      : `${distance.toFixed(0)} m`;

  const gpsLost = gpsState === "LOST";

  return (
    <div className="glass-panel p-4 rounded-2xl border border-cyan-500/20 shadow-xl space-y-3">

      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">

        <h3 className="font-tech text-sm font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
          <Layers className="w-4 h-4 text-cyan-400" />
          Live Telemetry & Diagnostics Overview
        </h3>

        <span className="text-[10px] font-mono text-cyan-400">
          10Hz Telemetry
        </span>

      </div>

      {/* Telemetry Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-9 gap-2.5">

        {/* GPS Status */}
        <div className="p-2.5 rounded-xl bg-slate-900/90 border border-slate-800 space-y-1">

          <div className="flex items-center gap-1.5 text-slate-400 text-[10px] font-mono uppercase">
            <Radio className="w-3 h-3 text-cyan-400" />
            <span>GPS Status</span>
          </div>

          <div
            className={`font-tech text-xs font-bold ${
              gpsLost
                ? "text-red-400 animate-pulse"
                : "text-emerald-400"
            }`}
          >
            {gpsState}
          </div>

        </div>

        {/* Navigation Mode */}
        <div className="p-2.5 rounded-xl bg-slate-900/90 border border-slate-800 space-y-1">

          <div className="flex items-center gap-1.5 text-slate-400 text-[10px] font-mono uppercase">
            <Cpu className="w-3 h-3 text-indigo-400" />
            <span>Nav Mode</span>
          </div>

          <div
            className="font-tech text-xs font-bold text-cyan-300 truncate"
            title={navMode}
          >
            {navMode}
          </div>

        </div>

        {/* Speed */}
        <div className="p-2.5 rounded-xl bg-slate-900/90 border border-slate-800 space-y-1">

          <div className="flex items-center gap-1.5 text-slate-400 text-[10px] font-mono uppercase">
            <Gauge className="w-3 h-3 text-cyan-400" />
            <span>Speed</span>
          </div>

          <div className="font-tech text-sm font-bold text-white">
            {speed.toFixed(1)}
            <span className="text-[10px] text-slate-400 ml-1">
              km/h
            </span>
          </div>

        </div>

        {/* Heading */}
        <div className="p-2.5 rounded-xl bg-slate-900/90 border border-slate-800 space-y-1">

          <div className="flex items-center gap-1.5 text-slate-400 text-[10px] font-mono uppercase">
            <Compass className="w-3 h-3 text-amber-400" />
            <span>Heading</span>
          </div>

          <div className="font-tech text-sm font-bold text-amber-300">
            {heading.toFixed(1)}°
            <span className="text-[10px] ml-1">
              {cardinalHeading}
            </span>
          </div>

        </div>

        {/* Distance */}
        <div className="p-2.5 rounded-xl bg-slate-900/90 border border-slate-800 space-y-1">

          <div className="flex items-center gap-1.5 text-slate-400 text-[10px] font-mono uppercase">
            <Route className="w-3 h-3 text-emerald-400" />
            <span>Distance</span>
          </div>

          <div className="font-tech text-sm font-bold text-emerald-300">
            {formattedDistance}
          </div>

        </div>

        {/* Outage Duration */}
        <div className="p-2.5 rounded-xl bg-slate-900/90 border border-slate-800 space-y-1">

          <div className="flex items-center gap-1.5 text-slate-400 text-[10px] font-mono uppercase">
            <Clock className="w-3 h-3 text-red-400" />
            <span>Outage Time</span>
          </div>

          <div
            className={`font-tech text-sm font-bold ${
              outage > 0
                ? "text-red-400 animate-pulse"
                : "text-slate-400"
            }`}
          >
            {outage.toFixed(1)}s
          </div>

        </div>

        {/* DR Error */}
        <div className="p-2.5 rounded-xl bg-slate-900/90 border border-slate-800 space-y-1">

          <div className="flex items-center gap-1.5 text-slate-400 text-[10px] font-mono uppercase">
            <AlertTriangle className="w-3 h-3 text-orange-400" />
            <span>DR Error</span>
          </div>

          <div className="font-tech text-sm font-bold text-orange-400">
            {driftError.toFixed(2)}m
          </div>

        </div>

        {/* AI Confidence */}
        <div className="p-2.5 rounded-xl bg-slate-900/90 border border-slate-800 space-y-1">

          <div className="flex items-center gap-1.5 text-slate-400 text-[10px] font-mono uppercase">
            <Cpu className="w-3 h-3 text-emerald-400" />
            <span>AI Confidence</span>
          </div>

          <div
            className={`font-tech text-sm font-bold ${
              confidence === null
                ? "text-slate-400"
                : confidence >= 90
                ? "text-emerald-400"
                : confidence >= 70
                ? "text-amber-400"
                : "text-slate-400"
            }`}
          >
            {confidence === null
              ? "N/A"
              : `${confidence.toFixed(1)}%`}
          </div>

        </div>

        {/* Fusion Status */}
        <div className="p-2.5 rounded-xl bg-slate-900/90 border border-slate-800 space-y-1">

          <div className="flex items-center gap-1.5 text-slate-400 text-[10px] font-mono uppercase">
            <Layers className="w-3 h-3 text-purple-400" />
            <span>Fusion State</span>
          </div>

          <div
            className="font-tech text-[11px] font-bold text-purple-300 truncate"
            title={sensorFusionStatus}
          >
            {sensorFusionStatus}
          </div>

        </div>

      </div>

    </div>
  );
}