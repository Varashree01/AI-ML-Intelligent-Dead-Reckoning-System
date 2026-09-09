import React, { useEffect, useState, useCallback } from "react";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import NavigationPage from "./components/NavigationPage";
import BenchmarkPage from "./components/BenchmarkPage";
import SensorsPage from "./components/SensorsPage";
import AnalyticsPage from "./components/AnalyticsPage";
import ArchitectureModal from "./components/ArchitectureModal";
import SettingsModal from "./components/SettingsModal";
import ProfileDrawer from "./components/ProfileDrawer";
import MapView from "./components/MapView";
import SimulationControls from "./components/SimulationControls";
import { Minimize2, Navigation, Compass, Shield } from "lucide-react";

export default function App() {
  // Navigation Active Tab: 'navigation' | 'benchmark' | 'sensors' | 'analytics' | 'architecture'
  const [activeTab, setActiveTab] = useState("navigation");

  // Sidebar States
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Modals & Drawers
  const [isArchitectureModalOpen, setIsArchitectureModalOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);

  // Theme & Map Settings
  const [theme, setTheme] = useState("dark");
  const [mapStyle, setMapStyle] = useState("dark");
  const [dataSource, setDataSource] = useState("IO-VNBD Dataset");

  // Fullscreen Map State
  const [isFullscreenMap, setIsFullscreenMap] = useState(false);
  const [autoPan, setAutoPan] = useState(true);

  // Simulation Playback & Control States (Default: PAUSED until user clicks play)
  const [isPlaying, setIsPlaying] = useState(false);
  const [speedMultiplier, setSpeedMultiplier] = useState(1);

  // Navigation Telemetry State
  const [pythonResults, setPythonResults] = useState(null);
  const [pythonDataLoaded, setPythonDataLoaded] = useState(false);
  const [pythonIndex, setPythonIndex] = useState(0);

  const [speedKmh, setSpeedKmh] = useState(0);
  const [headingDeg, setHeadingDeg] = useState(0);
  const [distanceTravelledMeters, setDistanceTravelledMeters] = useState(0);
  const [outageDuration, setOutageDuration] = useState(0);
  const [driftErrorMeters, setDriftErrorMeters] = useState(0);
  const [gpsState, setGpsState] = useState("AVAILABLE");
  const [navMode, setNavMode] = useState("GNSS NAVIGATION");

  const [sensorData, setSensorData] = useState({
    accel: { x: 0, y: 0, z: 9.81, totalG: 1 },
    gyro: { x: 0, y: 0, z: 0 },
    mag: { x: 0, y: 0, z: 0, fieldStrength: 49.8, heading: 0, cardinal: "N" },
  });

  // ESC key listener for Fullscreen Map
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && isFullscreenMap) {
        setIsFullscreenMap(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isFullscreenMap]);

  // Apply Theme Class to Document Body
  useEffect(() => {
    const root = document.documentElement;
    if (theme === "light") {
      root.classList.add("light");
    } else {
      root.classList.remove("light");
    }
  }, [theme]);

  // Load Python Results JSON
  useEffect(() => {
    fetch("/vehicle_dr_result.json")
      .then((response) => {
        if (!response.ok) throw new Error("Python result file not found");
        return response.json();
      })
      .then((data) => {
        setPythonResults(data);
        setPythonDataLoaded(true);
        setPythonIndex(0);
      })
      .catch(() => setPythonDataLoaded(false));
  }, []);

  // Telemetry Playback Loop with Play/Pause & Speed Multiplier
  useEffect(() => {
    if (!pythonDataLoaded || !pythonResults?.t?.length || !isPlaying) return;
    const intervalTime = Math.max(20, Math.floor(100 / speedMultiplier));
    const interval = setInterval(() => {
      setPythonIndex((prev) => (prev + 10 >= pythonResults.t.length ? 0 : prev + 10));
    }, intervalTime);
    return () => clearInterval(interval);
  }, [pythonDataLoaded, pythonResults, isPlaying, speedMultiplier]);

  // Update Telemetry & Outage State from Python Data
  useEffect(() => {
    if (!pythonResults || !pythonDataLoaded) return;
    const index = pythonIndex;

    const predictedSpeedMs = pythonResults.predicted_speed?.[index] ?? 0;
    setSpeedKmh(Math.max(0, predictedSpeedMs * 3.6));

    const currentHeading = pythonResults.heading_deg?.[index] ?? 0;
    setHeadingDeg(currentHeading);

    const currentPositionError = pythonResults.position_error?.[index] ?? 0;
    setDriftErrorMeters(Math.max(0, currentPositionError));

    const currentTime = pythonResults.t?.[index] ?? 0;
    const blackoutActive = pythonResults.blackout_mask?.[index] === true;

    // Respect override or dataset blackout state
    if (gpsState === "LOST" || (blackoutActive && gpsState !== "RESTORED")) {
      if (gpsState !== "LOST") setGpsState("LOST");
      setNavMode("GNSS-DENIED DEAD RECKONING");
      const tunnelStart = Number(pythonResults.tunnel_start ?? 25);
      setOutageDuration(Math.max(0, currentTime - tunnelStart));
    } else {
      if (gpsState !== "AVAILABLE" && gpsState !== "RESTORED") setGpsState("AVAILABLE");
      setNavMode("GNSS NAVIGATION");
      setOutageDuration(0);
    }

    // Distance calculation
    if (Array.isArray(pythonResults.gt_pos)) {
      let totalDistance = 0;
      const maxIndex = Math.min(index, pythonResults.gt_pos.length - 1);
      for (let i = 1; i <= maxIndex; i++) {
        const prev = pythonResults.gt_pos[i - 1];
        const curr = pythonResults.gt_pos[i];
        if (Array.isArray(prev) && Array.isArray(curr)) {
          const dx = Number(curr[0]) - Number(prev[0]);
          const dy = Number(curr[1]) - Number(prev[1]);
          if (Number.isFinite(dx) && Number.isFinite(dy)) {
            totalDistance += Math.sqrt(dx * dx + dy * dy);
          }
        }
      }
      setDistanceTravelledMeters(totalDistance);
    }

    // Sensor telemetry
    const imuAcc = pythonResults.imu_acc?.[index] || [0, 0, 9.81];
    const imuGyro = pythonResults.imu_gyro?.[index] || [0, 0, 0];
    const imuMag = pythonResults.imu_mag?.[index] || [0, 0, 0];

    const accMag = Math.sqrt(imuAcc[0] ** 2 + imuAcc[1] ** 2 + imuAcc[2] ** 2);
    const magStr = Math.sqrt(imuMag[0] ** 2 + imuMag[1] ** 2 + imuMag[2] ** 2);

    setSensorData({
      accel: { x: imuAcc[0], y: imuAcc[1], z: imuAcc[2], totalG: accMag / 9.81 },
      gyro: { x: imuGyro[0], y: imuGyro[1], z: imuGyro[2] },
      mag: { x: imuMag[0], y: imuMag[1], z: imuMag[2], fieldStrength: magStr, heading: currentHeading },
    });
  }, [pythonIndex, pythonResults, pythonDataLoaded]);

  // Simulation Controls Handlers
  const handleSimulateGpsLoss = useCallback(() => {
    setGpsState("LOST");
    setNavMode("GNSS-DENIED DEAD RECKONING");
    // Jump index to outage region if not already in outage
    if (pythonResults?.blackout_mask && !pythonResults.blackout_mask[pythonIndex]) {
      const outageIndex = pythonResults.blackout_mask.findIndex((mask) => mask === true);
      if (outageIndex !== -1) {
        setPythonIndex(outageIndex);
      }
    }
  }, [pythonResults, pythonIndex]);

  const handleRestoreGps = useCallback(() => {
    setGpsState("RESTORED");
    setNavMode("GNSS RESTORED RE-FUSION");
    setTimeout(() => {
      setGpsState("AVAILABLE");
      setNavMode("GNSS NAVIGATION");
    }, 3000);
  }, []);

  const handleResetSim = useCallback(() => {
    setPythonIndex(0);
    setGpsState("AVAILABLE");
    setNavMode("GNSS NAVIGATION");
    setIsPlaying(true);
    setOutageDuration(0);
  }, []);

  // Tab Title
  const getTabTitle = () => {
    switch (activeTab) {
      case 'benchmark': return 'Benchmark & Ablation Evaluation';
      case 'sensors': return 'Sensors Telemetry Stream';
      case 'analytics': return 'Performance Analytics';
      case 'architecture': return 'System Architecture & Math';
      case 'navigation':
      default: return 'Tactical Navigation Workspace';
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-950 light:bg-slate-50 transition-colors">
      {/* App Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={(tab) => {
          if (tab === 'architecture') {
            setIsArchitectureModalOpen(true);
          } else {
            setActiveTab(tab);
          }
        }}
        isCollapsed={isSidebarCollapsed}
        setIsCollapsed={setIsSidebarCollapsed}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onOpenProfile={() => setIsProfileOpen(true)}
        mobileOpen={mobileMenuOpen}
        setMobileOpen={setMobileMenuOpen}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Top Header */}
        <Header
          gpsState={gpsState}
          navMode={navMode}
          dataSource={dataSource}
          theme={theme}
          setTheme={setTheme}
          onOpenMobileMenu={() => setMobileMenuOpen(true)}
          onOpenSettings={() => setIsSettingsOpen(true)}
          onOpenProfile={() => setIsProfileOpen(true)}
          activeTabTitle={getTabTitle()}
        />

        {/* View Router Workspace */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
          {activeTab === 'navigation' && (
            <NavigationPage
              gpsState={gpsState}
              navMode={navMode}
              speedKmh={speedKmh}
              headingDeg={headingDeg}
              driftErrorMeters={driftErrorMeters}
              outageDuration={outageDuration}
              distanceTravelledMeters={distanceTravelledMeters}
              sensorData={sensorData}
              pythonResults={pythonResults}
              pythonIndex={pythonIndex}
              autoPan={autoPan}
              setAutoPan={setAutoPan}
              isFullscreenMap={isFullscreenMap}
              setIsFullscreenMap={setIsFullscreenMap}
              mapStyle={mapStyle}
              isPlaying={isPlaying}
              setIsPlaying={setIsPlaying}
              onSimulateGpsLoss={handleSimulateGpsLoss}
              onRestoreGps={handleRestoreGps}
              onResetSim={handleResetSim}
              speedMultiplier={speedMultiplier}
              setSpeedMultiplier={setSpeedMultiplier}
            />
          )}

          {activeTab === 'benchmark' && (
            <BenchmarkPage pythonResults={pythonResults} />
          )}

          {activeTab === 'sensors' && (
            <SensorsPage sensorData={sensorData} pythonResults={pythonResults} />
          )}

          {activeTab === 'analytics' && (
            <AnalyticsPage
              pythonResults={pythonResults}
              speedKmh={speedKmh}
              driftErrorMeters={driftErrorMeters}
            />
          )}
        </main>
      </div>

      {/* FULLSCREEN MAP OVERLAY WORKSPACE (Mounted at Root Level z-[9999]) */}
      {isFullscreenMap && (
        <div className="fixed inset-0 z-[9999] bg-slate-950 flex flex-col">
          {/* Top Floating Glass HUD */}
          <div className="absolute top-4 left-4 right-4 z-[10000] flex items-center justify-between pointer-events-none">
            <div className="glass-hud-overlay px-4 py-2.5 rounded-2xl flex items-center gap-3 pointer-events-auto">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white font-bold">
                <Shield size={18} />
              </div>
              <div>
                <h3 className="font-bold text-sm text-slate-100 font-tech">NAVAURA Tactical Fullscreen Map</h3>
                <span className="text-[10px] text-slate-400 font-mono">Press ESC or click exit to collapse</span>
              </div>
            </div>

            {/* Compact Simulation Toolbar + Exit Button */}
            <div className="flex items-center gap-2 pointer-events-auto">
              <SimulationControls
                isPlaying={isPlaying}
                setIsPlaying={setIsPlaying}
                gpsState={gpsState}
                onSimulateGpsLoss={handleSimulateGpsLoss}
                onRestoreGps={handleRestoreGps}
                onResetSim={handleResetSim}
                speedMultiplier={speedMultiplier}
                setSpeedMultiplier={setSpeedMultiplier}
                compact={true}
              />

              <button
                onClick={() => setIsFullscreenMap(false)}
                className="px-3 py-2 rounded-xl bg-slate-900/90 hover:bg-slate-800 text-slate-200 border border-slate-700 text-xs font-mono font-bold flex items-center gap-1.5 shadow-lg active:scale-95 transition-all"
              >
                <Minimize2 size={16} />
                <span>EXIT FULLSCREEN</span>
              </button>
            </div>
          </div>

          {/* Map Component Container */}
          <div className="w-full h-full flex-1">
            <MapView
              gpsState={gpsState}
              driftErrorMeters={driftErrorMeters}
              speedKmh={speedKmh}
              headingDeg={headingDeg}
              outageDuration={outageDuration}
              autoPan={autoPan}
              setAutoPan={setAutoPan}
              isFullscreen={true}
              onToggleFullscreen={() => setIsFullscreenMap(false)}
              mapStyle={mapStyle}
              pythonResults={pythonResults}
              pythonIndex={pythonIndex}
            />
          </div>
        </div>
      )}

      {/* Modals & Drawers */}
      <ArchitectureModal
        isOpen={isArchitectureModalOpen}
        onClose={() => setIsArchitectureModalOpen(false)}
      />

      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        theme={theme}
        setTheme={setTheme}
        mapStyle={mapStyle}
        setMapStyle={setMapStyle}
        dataSource={dataSource}
        setDataSource={setDataSource}
      />

      <ProfileDrawer
        isOpen={isProfileOpen}
        onClose={() => setIsProfileOpen(false)}
      />
    </div>
  );
}