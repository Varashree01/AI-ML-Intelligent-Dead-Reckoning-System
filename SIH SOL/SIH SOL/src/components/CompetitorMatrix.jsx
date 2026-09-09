import React from 'react';
import { 
  Check, 
  X, 
  HelpCircle, 
  ShieldCheck, 
  Cpu, 
  Smartphone, 
  Zap,
  Globe
} from 'lucide-react';

export default function CompetitorMatrix() {
  const categories = [
    {
      name: 'GNSS-Only Navigation',
      hardware: 'Smartphone GPS/NavIC',
      cost: '$0',
      offlineNav: 'No',
      gnssDenied: 'No (Freeze / Lost)',
      orientationHandling: 'No',
      aiMl: 'No',
      accuracy: 'Drifts infinitely during outage'
    },
    {
      name: 'Consumer Offline Maps (e.g. MAPS.ME / Google Offline)',
      hardware: 'Smartphone',
      cost: '$0',
      offlineNav: 'Routing Only',
      gnssDenied: 'No (Requires GNSS Fix)',
      orientationHandling: 'No',
      aiMl: 'No',
      accuracy: 'No positioning without GNSS fix'
    },
    {
      name: 'Commercial GNSS/INS Systems (NovAtel / OxTS)',
      hardware: 'Vehicle-side IMU + Wheel Encoders',
      cost: '$10,000 - $50,000+',
      offlineNav: 'Yes',
      gnssDenied: 'Yes (Sub-meter)',
      orientationHandling: 'Fixed Mount Required',
      aiMl: 'No (Kalman Only)',
      accuracy: '0.1% - 0.5% distance drift'
    },
    {
      name: 'Academic Inertial Odometry Research (RoNIN / RIO)',
      hardware: 'Smartphone',
      cost: '$0',
      offlineNav: 'Yes',
      gnssDenied: 'Pedestrian Only',
      orientationHandling: 'Partial',
      aiMl: 'Deep Neural Net',
      accuracy: 'Pedestrian step-based only'
    },
    {
      name: 'NAVAURA (Proposed System)',
      hardware: 'Commodity Smartphone Only',
      cost: '$0 (No vehicle hardware)',
      offlineNav: 'Yes (Full Offline Engine)',
      gnssDenied: 'Yes (Vehicle DR + AI Speed)',
      orientationHandling: 'Automatic Phone-to-Vehicle Alignment',
      aiMl: 'Random Forest Speed + 2-State EKF',
      accuracy: '0.50% distance drift (~2.4m over 10s)'
    }
  ];

  return (
    <div className="space-y-6">
      <div className="surface-level-2 p-6 rounded-2xl space-y-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 text-xs font-mono font-semibold border border-cyan-500/30">
              System Differentiation
            </span>
            <span className="text-xs text-slate-400 font-mono">SIH26168 • TEAM 06</span>
          </div>
          <h2 className="text-xl font-bold text-slate-100 light:text-slate-900 mt-1">
            Why NAVAURA? Competitor & Baseline Matrix
          </h2>
          <p className="text-xs text-slate-400">
            Honest technical evaluation of NAVAURA against existing consumer, commercial, and research navigation approaches.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono pt-2">
          <div className="p-4 rounded-xl bg-slate-900/60 light:bg-slate-50 border border-slate-800 light:border-slate-200 space-y-1">
            <div className="flex items-center gap-2 text-cyan-400 font-bold">
              <Smartphone size={16} />
              <span>Smartphone-First</span>
            </div>
            <p className="text-slate-400 text-[11px]">
              Zero external vehicle hardware, OBD dongles, or wheel sensors required. Operates using commodity sensors.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 light:bg-slate-50 border border-slate-800 light:border-slate-200 space-y-1">
            <div className="flex items-center gap-2 text-blue-400 font-bold">
              <Zap size={16} />
              <span>AI + Physics Hybrid</span>
            </div>
            <p className="text-slate-400 text-[11px]">
              Combines Random Forest speed inference from IMU features with a 2-State EKF for drift-free heading estimation.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 light:bg-slate-50 border border-slate-800 light:border-slate-200 space-y-1">
            <div className="flex items-center gap-2 text-emerald-400 font-bold">
              <Globe size={16} />
              <span>100% Offline Core</span>
            </div>
            <p className="text-slate-400 text-[11px]">
              Requires zero paid API keys or cloud connections during GNSS outages. Maps and state propagation run locally.
            </p>
          </div>
        </div>

        {/* Matrix Table */}
        <div className="overflow-x-auto pt-2">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-900/60 light:bg-slate-100 text-slate-400 border-b border-slate-800 light:border-slate-200">
              <tr>
                <th className="p-3.5 pl-5">Approach Category</th>
                <th className="p-3.5">Hardware Req.</th>
                <th className="p-3.5">Hardware Cost</th>
                <th className="p-3.5">GNSS-Denied Nav</th>
                <th className="p-3.5">Frame Alignment</th>
                <th className="p-3.5">AI/ML Motion</th>
                <th className="p-3.5 pr-5">Accuracy / Drift</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 light:divide-slate-200">
              {categories.map((c, i) => {
                const isNAVAURA = c.name.startsWith('NAVAURA');
                return (
                  <tr 
                    key={i} 
                    className={`transition-colors ${
                      isNAVAURA 
                        ? 'bg-cyan-500/10 light:bg-cyan-50/70 border-l-4 border-l-cyan-400' 
                        : 'hover:bg-slate-800/40 light:hover:bg-slate-50'
                    }`}
                  >
                    <td className="p-3.5 pl-5 font-semibold text-slate-200 light:text-slate-800 flex items-center gap-2">
                      {isNAVAURA && <ShieldCheck size={16} className="text-cyan-400 shrink-0" />}
                      <span>{c.name}</span>
                    </td>
                    <td className="p-3.5 text-slate-300">{c.hardware}</td>
                    <td className="p-3.5 text-slate-300 font-bold">{c.cost}</td>
                    <td className="p-3.5 text-slate-300">{c.gnssDenied}</td>
                    <td className="p-3.5 text-slate-300">{c.orientationHandling}</td>
                    <td className="p-3.5 text-slate-300">{c.aiMl}</td>
                    <td className={`p-3.5 pr-5 font-semibold ${isNAVAURA ? 'text-emerald-400' : 'text-slate-400'}`}>
                      {c.accuracy}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
