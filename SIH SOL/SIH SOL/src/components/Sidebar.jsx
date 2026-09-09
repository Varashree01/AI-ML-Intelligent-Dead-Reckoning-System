import React from 'react';
import { 
  Navigation, 
  BarChart3, 
  Cpu, 
  Activity, 
  Network, 
  Settings, 
  User, 
  ChevronLeft, 
  ChevronRight,
  Shield
} from 'lucide-react';

export default function Sidebar({ 
  activeTab, 
  setActiveTab, 
  isCollapsed, 
  setIsCollapsed,
  onOpenSettings,
  onOpenProfile,
  mobileOpen,
  setMobileOpen
}) {
  const navItems = [
    { id: 'navigation', label: 'Navigation', icon: Navigation },
    { id: 'benchmark', label: 'Benchmark & Ablation', icon: BarChart3 },
    { id: 'sensors', label: 'Sensors Telemetry', icon: Cpu },
    { id: 'analytics', label: 'Performance Analytics', icon: Activity },
    { id: 'architecture', label: 'System Architecture', icon: Network },
  ];

  const sidebarWidth = isCollapsed ? 'w-18' : 'w-64';

  return (
    <>
      {/* Mobile Backdrop */}
      {mobileOpen && (
        <div 
          onClick={() => setMobileOpen(false)}
          className="fixed inset-0 bg-slate-950/60 backdrop-blur-sm z-40 lg:hidden"
        />
      )}

      <aside className={`
        fixed lg:static top-0 left-0 h-full z-50
        ${sidebarWidth} transition-all duration-300 ease-in-out
        flex flex-col bg-slate-900/95 dark:bg-slate-900/95 light:bg-white
        border-r border-slate-800 light:border-slate-200
        ${mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        {/* Top Header Logo */}
        <div className="h-16 px-4 flex items-center justify-between border-b border-slate-800 light:border-slate-200">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white shrink-0 shadow-md">
              <Shield className="w-5 h-5" />
            </div>
            {!isCollapsed && (
              <div className="flex flex-col">
                <span className="font-bold text-base tracking-tight text-slate-100 light:text-slate-900 font-tech">NAVAURA</span>
                <span className="text-[10px] text-slate-400 font-mono tracking-wider">TEAM 06 • ISRO</span>
              </div>
            )}
          </div>

          {/* Desktop Toggle Button */}
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="hidden lg:flex p-1.5 rounded-lg hover:bg-slate-800 light:hover:bg-slate-100 text-slate-400 hover:text-slate-200 transition-colors"
            title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {isCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          </button>
        </div>

        {/* Primary Navigation Links */}
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  setActiveTab(item.id);
                  setMobileOpen(false);
                }}
                className={`
                  w-full flex items-center gap-3 px-3 py-2.5 rounded-xl font-medium text-sm transition-all duration-200 group relative
                  ${isActive 
                    ? 'bg-cyan-500/10 text-cyan-400 light:bg-cyan-50 light:text-cyan-700 border border-cyan-500/20' 
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 light:hover:bg-slate-100'}
                `}
                title={isCollapsed ? item.label : undefined}
              >
                <Icon className={`w-5 h-5 shrink-0 ${isActive ? 'text-cyan-400 light:text-cyan-600' : 'text-slate-400 group-hover:text-slate-200'}`} />
                {!isCollapsed && (
                  <span className="truncate">{item.label}</span>
                )}
                {isActive && !isCollapsed && (
                  <span className="ml-auto w-1.5 h-1.5 rounded-full bg-cyan-400 light:bg-cyan-600" />
                )}
              </button>
            );
          })}
        </nav>

        {/* Bottom Utility Menu */}
        <div className="p-3 border-t border-slate-800 light:border-slate-200 space-y-1">
          <button
            onClick={onOpenSettings}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl font-medium text-sm text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 light:hover:bg-slate-100 transition-colors"
            title={isCollapsed ? "Settings" : undefined}
          >
            <Settings className="w-5 h-5 shrink-0" />
            {!isCollapsed && <span>Settings</span>}
          </button>

          <button
            onClick={onOpenProfile}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl font-medium text-sm text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 light:hover:bg-slate-100 transition-colors"
            title={isCollapsed ? "Team Profile" : undefined}
          >
            <User className="w-5 h-5 shrink-0" />
            {!isCollapsed && <span>Team & Info</span>}
          </button>
        </div>
      </aside>
    </>
  );
}
