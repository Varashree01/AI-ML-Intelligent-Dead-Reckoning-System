import React from 'react';
import { X, Shield, Award, MapPin, Cpu, CheckCircle } from 'lucide-react';

export default function ProfileDrawer({ isOpen, onClose }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/60 backdrop-blur-sm">
      <div className="surface-level-2 w-full max-w-sm h-full p-6 border-l border-slate-800 light:border-slate-200 shadow-2xl space-y-6 overflow-y-auto">
        <div className="flex items-center justify-between border-b border-slate-800 light:border-slate-200 pb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white font-bold">
              06
            </div>
            <div>
              <h3 className="font-bold text-base text-slate-100 light:text-slate-900 font-tech">TEAM 06</h3>
              <span className="text-xs text-slate-400 font-mono">SIH 2026 Submission</span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-slate-800 light:hover:bg-slate-100 text-slate-400"
          >
            <X size={18} />
          </button>
        </div>

        {/* Project Specifications */}
        <div className="space-y-4 text-xs font-mono">
          <div className="p-4 rounded-xl bg-slate-900/60 light:bg-slate-50 border border-slate-800 light:border-slate-200 space-y-2">
            <div className="flex items-center gap-2 text-cyan-400 font-bold">
              <Award size={16} />
              <span>Problem Statement SIH26168</span>
            </div>
            <p className="text-slate-300 light:text-slate-700 leading-relaxed font-sans">
              AI/ML-based Intelligent Dead Reckoning System for Seamless Navigation
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 light:bg-slate-50 border border-slate-800 light:border-slate-200 space-y-2">
            <div className="flex items-center gap-2 text-blue-400 font-bold">
              <MapPin size={16} />
              <span>Organization</span>
            </div>
            <p className="text-slate-300 light:text-slate-700 font-sans font-semibold">
              ISRO / Department of Space
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 light:bg-slate-50 border border-slate-800 light:border-slate-200 space-y-2">
            <div className="flex items-center gap-2 text-emerald-400 font-bold">
              <Shield size={16} />
              <span>System Verification</span>
            </div>
            <div className="space-y-1.5 text-[11px] text-slate-400">
              <div className="flex items-center gap-2">
                <CheckCircle size={13} className="text-emerald-400" />
                <span>Zero ground-truth leakage in inference</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle size={13} className="text-emerald-400" />
                <span>Synchronized 10Hz IMU ingestion</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle size={13} className="text-emerald-400" />
                <span>2-State EKF + RF Speed Estimator</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
