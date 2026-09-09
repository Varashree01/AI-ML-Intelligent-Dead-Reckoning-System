import React from 'react';
import { 
  Menu, 
  Sun, 
  Moon, 
  Database, 
  User, 
  Radio,
  SlidersHorizontal
} from 'lucide-react';

export default function Header({
  gpsState,
  navMode,
  dataSource = 'IO-VNBD',
  theme,
  setTheme,
  onOpenMobileMenu,
  onOpenSettings,
  onOpenProfile,
  activeTabTitle = 'Navigation'
}) {
  // Status Badge Logic
  const renderStatusBadge = () => {
    switch (gpsState) {
      case 'AVAILABLE':
        return (
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>GNSS Available</span>
          </div>
        );
      case 'LOST':
        return (
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/15 border border-amber-500/40 text-amber-400 text-xs font-medium animate-pulse">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
            <span>GNSS Lost • Dead Reckoning Active</span>
          </div>
        );
      case 'RESTORED':
        return (
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/15 border border-cyan-500/40 text-cyan-400 text-xs font-medium">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
            <span>GNSS Restored • Re-fusion</span>
          </div>
        );
      default:
        return (
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-slate-800 border border-slate-700 text-slate-300 text-xs font-medium">
            <span className="w-2 h-2 rounded-full bg-slate-400" />
            <span>Navigation Active</span>
          </div>
        );
    }
  };

  return (
    <header className="h-16 px-4 sm:px-6 bg-slate-900/80 light:bg-white/90 backdrop-blur-md border-b border-slate-800 light:border-slate-200 flex items-center justify-between gap-4 sticky top-0 z-30 transition-colors">
      {/* Left: Mobile Menu Toggle & Title */}
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenMobileMenu}
          className="lg:hidden p-2 rounded-lg hover:bg-slate-800 light:hover:bg-slate-100 text-slate-400"
          aria-label="Open menu"
        >
          <Menu size={20} />
        </button>

        <div className="flex items-center gap-2">
          <h1 className="text-base sm:text-lg font-semibold text-slate-100 light:text-slate-900 tracking-tight">
            {activeTabTitle}
          </h1>
          <span className="text-xs text-slate-500 hidden sm:inline">•</span>
          <span className="text-xs text-slate-400 hidden sm:inline font-mono">
            SIH26168 / ISRO
          </span>
        </div>
      </div>

      {/* Right: Telemetry Badges, Theme Toggle, Profile */}
      <div className="flex items-center gap-3">
        {/* Status Pill */}
        {renderStatusBadge()}

        {/* Data Source Tag */}
        <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800/80 light:bg-slate-100 border border-slate-700/60 light:border-slate-200 text-slate-300 light:text-slate-700 text-xs font-mono">
          <Database size={13} className="text-cyan-400 light:text-cyan-600" />
          <span>{dataSource}</span>
        </div>

        {/* Theme Toggle */}
        <button
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          className="p-2 rounded-xl bg-slate-800/60 light:bg-slate-100 hover:bg-slate-700 light:hover:bg-slate-200 text-slate-300 light:text-slate-700 border border-slate-700/50 light:border-slate-200 transition-colors"
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
        >
          {theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}
        </button>

        {/* Settings Shortcut */}
        <button
          onClick={onOpenSettings}
          className="hidden sm:flex p-2 rounded-xl bg-slate-800/60 light:bg-slate-100 hover:bg-slate-700 light:hover:bg-slate-200 text-slate-300 light:text-slate-700 border border-slate-700/50 light:border-slate-200 transition-colors"
          title="Settings"
        >
          <SlidersHorizontal size={17} />
        </button>

        {/* Team Profile Button */}
        <button
          onClick={onOpenProfile}
          className="flex items-center gap-2 p-1.5 sm:px-3 sm:py-1.5 rounded-xl bg-slate-800/80 light:bg-slate-100 hover:bg-slate-700 light:hover:bg-slate-200 border border-slate-700/60 light:border-slate-200 transition-colors text-xs font-medium text-slate-200 light:text-slate-800"
        >
          <div className="w-6 h-6 rounded-lg bg-cyan-500/20 text-cyan-400 flex items-center justify-center font-bold text-xs">
            06
          </div>
          <span className="hidden sm:inline">Team 06</span>
        </button>
      </div>
    </header>
  );
}
