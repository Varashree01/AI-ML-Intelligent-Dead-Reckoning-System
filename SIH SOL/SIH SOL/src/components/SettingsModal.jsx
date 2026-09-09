import React from 'react';
import { X, SlidersHorizontal, Sun, Moon, Database, Map, Check } from 'lucide-react';

export default function SettingsModal({
  isOpen,
  onClose,
  theme,
  setTheme,
  mapStyle,
  setMapStyle,
  dataSource,
  setDataSource
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm">
      <div className="surface-level-2 w-full max-w-md p-6 rounded-2xl border border-slate-800 light:border-slate-200 shadow-2xl space-y-6">
        <div className="flex items-center justify-between border-b border-slate-800 light:border-slate-200 pb-4">
          <div className="flex items-center gap-2 font-semibold text-slate-100 light:text-slate-900">
            <SlidersHorizontal size={18} className="text-cyan-400" />
            <span>NAVAURA System Preferences</span>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-slate-800 light:hover:bg-slate-100 text-slate-400"
          >
            <X size={18} />
          </button>
        </div>

        {/* Appearance Theme */}
        <div className="space-y-2">
          <label className="text-xs font-medium text-slate-300 light:text-slate-700 block">
            Appearance Theme
          </label>
          <div className="grid grid-cols-2 gap-2 text-xs font-medium">
            <button
              onClick={() => setTheme('dark')}
              className={`p-3 rounded-xl border flex items-center justify-center gap-2 transition-all ${
                theme === 'dark'
                  ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40'
                  : 'bg-slate-900/60 light:bg-slate-100 text-slate-400 border-slate-800'
              }`}
            >
              <Moon size={16} />
              <span>Dark Theme</span>
            </button>
            <button
              onClick={() => setTheme('light')}
              className={`p-3 rounded-xl border flex items-center justify-center gap-2 transition-all ${
                theme === 'light'
                  ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40'
                  : 'bg-slate-900/60 light:bg-slate-100 text-slate-400 border-slate-800'
              }`}
            >
              <Sun size={16} />
              <span>Light Theme</span>
            </button>
          </div>
        </div>

        {/* Map Canvas Style */}
        <div className="space-y-2">
          <label className="text-xs font-medium text-slate-300 light:text-slate-700 block">
            Default Map Canvas Style
          </label>
          <div className="grid grid-cols-3 gap-2 text-xs font-medium">
            {['dark', 'light', 'satellite'].map((style) => (
              <button
                key={style}
                onClick={() => setMapStyle(style)}
                className={`p-2.5 rounded-xl border capitalize transition-all ${
                  mapStyle === style
                    ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40 font-semibold'
                    : 'bg-slate-900/60 light:bg-slate-100 text-slate-400 border-slate-800'
                }`}
              >
                {style}
              </button>
            ))}
          </div>
        </div>

        {/* Data Source */}
        <div className="space-y-2">
          <label className="text-xs font-medium text-slate-300 light:text-slate-700 block">
            Telemetry Data Source
          </label>
          <div className="space-y-2 text-xs font-medium">
            <button
              onClick={() => setDataSource('IO-VNBD Dataset')}
              className={`w-full p-3 rounded-xl border flex items-center justify-between text-left transition-all ${
                dataSource === 'IO-VNBD Dataset'
                  ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40'
                  : 'bg-slate-900/60 light:bg-slate-100 text-slate-400 border-slate-800'
              }`}
            >
              <div>
                <div className="font-semibold text-slate-200 light:text-slate-900">IO-VNBD Recorded Dataset</div>
                <div className="text-[11px] text-slate-400 font-mono">Synchronized 5,200 sample telemetry</div>
              </div>
              {dataSource === 'IO-VNBD Dataset' && <Check size={16} className="text-cyan-400" />}
            </button>

            <button
              onClick={() => setDataSource('Live Android Client')}
              className={`w-full p-3 rounded-xl border flex items-center justify-between text-left transition-all ${
                dataSource === 'Live Android Client'
                  ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40'
                  : 'bg-slate-900/60 light:bg-slate-100 text-slate-400 border-slate-800'
              }`}
            >
              <div>
                <div className="font-semibold text-slate-200 light:text-slate-900">Live Android Sensor Client</div>
                <div className="text-[11px] text-slate-400 font-mono">Stream from smartphone sensors</div>
              </div>
              {dataSource === 'Live Android Client' && <Check size={16} className="text-cyan-400" />}
            </button>
          </div>
        </div>

        <div className="pt-2">
          <button
            onClick={onClose}
            className="w-full py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs transition-colors shadow-md"
          >
            Apply & Close
          </button>
        </div>
      </div>
    </div>
  );
}
