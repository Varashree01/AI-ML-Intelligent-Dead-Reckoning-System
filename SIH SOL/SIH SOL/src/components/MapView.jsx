import React, { useEffect, useMemo, useState } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  Circle,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import { 
  Navigation, 
  Maximize2, 
  Minimize2, 
  Layers, 
  Compass, 
  AlertTriangle,
  Radio,
  Clock,
  Gauge,
  Activity
} from "lucide-react";
import "leaflet/dist/leaflet.css";

const ORIGIN_LAT = 12.9716;
const ORIGIN_LNG = 77.5946;

// Custom directional SVG vehicle icon generator
const createDirectionalIcon = (color, heading = 0, label = "NAV") => {
  return L.divIcon({
    className: "custom-vehicle-marker",
    html: `
      <div style="
        width: 32px;
        height: 32px;
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
      ">
        <div style="
          transform: rotate(${heading}deg);
          transition: transform 0.2s linear;
          width: 32px;
          height: 32px;
          border-radius: 50%;
          background: ${color};
          border: 2.5px solid #ffffff;
          box-shadow: 0 4px 12px rgba(0,0,0,0.35);
          display: flex;
          align-items: center;
          justify-content: center;
          color: #ffffff;
        ">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="12 2 19 21 12 17 5 21 12 2"/>
          </svg>
        </div>
      </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    popupAnchor: [0, -18],
  });
};

const gpsIcon = createDirectionalIcon("#2563eb", 0, "G");
const drIcon = createDirectionalIcon("#d97706", 0, "DR");

function MapController({ position, autoPan }) {
  const map = useMap();

  useEffect(() => {
    if (autoPan && position) {
      map.panTo(position, {
        animate: true,
        duration: 0.4,
      });
    }
  }, [position, autoPan, map]);

  return null;
}

function metersToLatLng(point) {
  if (!Array.isArray(point) || point.length < 2) return null;
  const x = Number(point[0]);
  const y = Number(point[1]);
  if (!Number.isFinite(x) || !Number.isFinite(y)) return null;

  const lat = ORIGIN_LAT + y / 111320;
  const lng = ORIGIN_LNG + x / (111320 * Math.cos((ORIGIN_LAT * Math.PI) / 180));
  return [lat, lng];
}

function convertTrajectory(data) {
  if (!Array.isArray(data)) return [];
  return data.map(metersToLatLng).filter(Boolean);
}

export default function MapView({
  gpsPos,
  drPos,
  aiPos,
  gpsState,
  routeHistory = [],
  drHistory = [],
  aiHistory = [],
  driftErrorMeters = 0,
  speedKmh = 0,
  headingDeg = 0,
  outageDuration = 0,
  autoPan = true,
  setAutoPan,
  isFullscreen = false,
  onToggleFullscreen,
  mapStyle = "dark",
  onStyleChange,
  pythonResults: propPythonData,
  pythonIndex: propPythonIndex
}) {
  const [internalPythonData, setInternalPythonData] = useState(null);
  const [selectedTileStyle, setSelectedTileStyle] = useState(mapStyle);
  const [showLayerMenu, setShowLayerMenu] = useState(false);

  useEffect(() => {
    if (propPythonData) return;
    fetch("/vehicle_dr_result.json")
      .then((res) => {
        if (!res.ok) throw new Error("Result file not found");
        return res.json();
      })
      .then((data) => {
        setInternalPythonData(data);
      })
      .catch(() => {});
  }, [propPythonData]);

  const pythonData = propPythonData || internalPythonData;
  const pythonIndex = propPythonIndex ?? 0;

  const pythonGpsPath = useMemo(() => convertTrajectory(pythonData?.gps_pos), [pythonData]);
  const pythonDrPath = useMemo(() => convertTrajectory(pythonData?.dr_prediction), [pythonData]);
  const pythonAiPath = useMemo(() => convertTrajectory(pythonData?.estimated_pos), [pythonData]);

  const pythonGpsPos = useMemo(() => metersToLatLng(pythonData?.gps_pos?.[pythonIndex]), [pythonData, pythonIndex]);
  const pythonDrPos = useMemo(() => metersToLatLng(pythonData?.dr_prediction?.[pythonIndex]), [pythonData, pythonIndex]);
  const pythonAiPos = useMemo(() => metersToLatLng(pythonData?.estimated_pos?.[pythonIndex]), [pythonData, pythonIndex]);

  const blackoutActive = pythonData?.blackout_mask?.[pythonIndex] === true;
  const currentHeading = pythonData?.heading_deg?.[pythonIndex] ?? headingDeg;
  const currentSpeed = pythonData?.predicted_speed?.[pythonIndex] 
    ? Math.max(0, pythonData.predicted_speed[pythonIndex] * 3.6) 
    : speedKmh;
  const currentError = pythonData?.position_error?.[pythonIndex] ?? driftErrorMeters;
  const currentTime = pythonData?.t?.[pythonIndex] ?? 0;

  const activeGps = pythonGpsPos || gpsPos || null;
  const activeDr = pythonDrPos || drPos || null;
  const activeAi = pythonAiPos || aiPos || null;

  const vehiclePosition = activeAi || activeDr || activeGps || [ORIGIN_LAT, ORIGIN_LNG];

  const aiVehicleIcon = useMemo(() => {
    return createDirectionalIcon("#10b981", currentHeading, "AI");
  }, [currentHeading]);

  // Keyless Public GIS Tile Layer URLs
  const getTileConfig = () => {
    switch (selectedTileStyle) {
      case 'light':
      case 'osm':
        return {
          url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        };
      case 'topo':
        return {
          url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
          attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ, TomTom, Intermap, iPC, USGS, FAO, NPS, NRCAN, GeoBase, Kadaster NL, Ordnance Survey, Esri Japan, METI, Esri China (Hong Kong), and the GIS User Community'
        };
      case 'satellite':
        return {
          url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
          attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
        };
      case 'dark':
      default:
        return {
          url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
          attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ'
        };
    }
  };

  const tileConfig = useMemo(() => getTileConfig(), [selectedTileStyle]);

  return (
    <div className={`relative w-full h-full min-h-[480px] rounded-2xl overflow-hidden ${isFullscreen ? 'fixed inset-0 z-50 rounded-none min-h-screen' : ''}`}>
      <MapContainer
        center={vehiclePosition}
        zoom={17}
        zoomControl={false}
        className="w-full h-full min-h-[480px]"
      >
        <TileLayer
          attribution={tileConfig.attribution}
          url={tileConfig.url}
          maxZoom={19}
        />

        <MapController position={vehiclePosition} autoPan={autoPan} />

        {/* Polylines */}
        {pythonGpsPath.length > 1 && (
          <Polyline
            positions={pythonGpsPath}
            pathOptions={{ color: "#2563eb", weight: 3.5, opacity: 0.7 }}
          />
        )}
        {pythonDrPath.length > 1 && (
          <Polyline
            positions={pythonDrPath}
            pathOptions={{ color: "#d97706", weight: 3.5, opacity: 0.85, dashArray: "8 6" }}
          />
        )}
        {pythonAiPath.length > 1 && (
          <Polyline
            positions={pythonAiPath}
            pathOptions={{ color: "#10b981", weight: 4.5, opacity: 0.95 }}
          />
        )}

        {/* Markers */}
        {activeGps && (
          <Marker position={activeGps} icon={gpsIcon}>
            <Popup>
              <div className="text-xs space-y-1">
                <strong className="text-blue-400">GNSS Reference</strong>
                <div>Status: {blackoutActive ? "Outage" : "Available"}</div>
              </div>
            </Popup>
          </Marker>
        )}

        {activeDr && (
          <Marker position={activeDr} icon={drIcon}>
            <Popup>
              <div className="text-xs space-y-1">
                <strong className="text-amber-400">Dead Reckoning (Unconstrained)</strong>
                <div>Predicted Pos</div>
              </div>
            </Popup>
          </Marker>
        )}

        {activeAi && (
          <Marker position={activeAi} icon={aiVehicleIcon}>
            <Popup>
              <div className="text-xs space-y-1">
                <strong className="text-emerald-400">NAVAURA Estimated Vehicle Position</strong>
                <div>Speed: {currentSpeed.toFixed(1)} km/h</div>
                <div>Heading: {currentHeading.toFixed(1)}°</div>
                <div>Error: {currentError.toFixed(2)} m</div>
              </div>
            </Popup>
          </Marker>
        )}

        {activeAi && currentError > 0 && (
          <Circle
            center={activeAi}
            radius={Math.max(currentError, 1.5)}
            pathOptions={{ color: blackoutActive ? "#f59e0b" : "#10b981", fillOpacity: 0.08, weight: 1.5 }}
          />
        )}
      </MapContainer>

      {/* Top Left Navigation Header Badge */}
      <div className="absolute top-4 left-4 z-[1000] glass-hud-overlay px-3 py-2 rounded-2xl flex items-center gap-3">
        <div className="flex items-center gap-2">
          <Navigation size={16} className="text-emerald-400 animate-pulse" />
          <span className="text-xs font-bold font-mono tracking-wider text-slate-100 uppercase">
            NAVAURA Tactical Map
          </span>
        </div>
        <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${blackoutActive ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'}`}>
          {blackoutActive ? 'AI DEAD RECKONING' : 'GNSS ACTIVE'}
        </span>
      </div>

      {/* Real-time Telemetry HUD Card (Top Left) */}
      <div className="absolute top-16 left-4 z-[1000] glass-hud-overlay p-3 rounded-2xl hidden md:flex items-center gap-4 text-xs font-mono">
        <div>
          <div className="text-[10px] text-slate-400">SPEED</div>
          <div className="font-bold text-slate-100">{currentSpeed.toFixed(1)} <span className="text-[10px] text-slate-400">km/h</span></div>
        </div>
        <div className="w-[1px] h-6 bg-slate-800" />
        <div>
          <div className="text-[10px] text-slate-400">HEADING</div>
          <div className="font-bold text-slate-100">{currentHeading.toFixed(0)}°</div>
        </div>
        <div className="w-[1px] h-6 bg-slate-800" />
        <div>
          <div className="text-[10px] text-slate-400">ERROR</div>
          <div className={`font-bold ${currentError < 3 ? 'text-emerald-400' : 'text-amber-400'}`}>
            {currentError.toFixed(2)}m
          </div>
        </div>
      </div>

      {/* Top Right Action Controls */}
      <div className="absolute top-4 right-4 z-[1000] flex items-center gap-2">
        {/* Layer Selector */}
        <div className="relative">
          <button
            onClick={() => setShowLayerMenu(!showLayerMenu)}
            className="p-2.5 rounded-xl glass-hud-overlay text-slate-300 hover:text-white transition-colors"
            title="Map Style"
          >
            <Layers size={17} />
          </button>

          {showLayerMenu && (
            <div className="absolute right-0 top-12 z-[1001] glass-hud-overlay p-2 rounded-xl space-y-1 min-w-[150px] text-xs">
              <button
                onClick={() => { setSelectedTileStyle('dark'); setShowLayerMenu(false); }}
                className={`w-full text-left px-3 py-1.5 rounded-lg ${selectedTileStyle === 'dark' ? 'bg-cyan-500/20 text-cyan-400 font-medium' : 'text-slate-300 hover:bg-slate-800/60'}`}
              >
                Dark Canvas
              </button>
              <button
                onClick={() => { setSelectedTileStyle('osm'); setShowLayerMenu(false); }}
                className={`w-full text-left px-3 py-1.5 rounded-lg ${selectedTileStyle === 'osm' ? 'bg-cyan-500/20 text-cyan-400 font-medium' : 'text-slate-300 hover:bg-slate-800/60'}`}
              >
                OpenStreetMap
              </button>
              <button
                onClick={() => { setSelectedTileStyle('topo'); setShowLayerMenu(false); }}
                className={`w-full text-left px-3 py-1.5 rounded-lg ${selectedTileStyle === 'topo' ? 'bg-cyan-500/20 text-cyan-400 font-medium' : 'text-slate-300 hover:bg-slate-800/60'}`}
              >
                Topographic Map
              </button>
              <button
                onClick={() => { setSelectedTileStyle('satellite'); setShowLayerMenu(false); }}
                className={`w-full text-left px-3 py-1.5 rounded-lg ${selectedTileStyle === 'satellite' ? 'bg-cyan-500/20 text-cyan-400 font-medium' : 'text-slate-300 hover:bg-slate-800/60'}`}
              >
                Satellite Imagery
              </button>
            </div>
          )}
        </div>

        {/* Auto Lock Button */}
        <button
          onClick={() => setAutoPan?.((prev) => !prev)}
          className={`p-2.5 rounded-xl glass-hud-overlay transition-colors ${autoPan ? 'text-cyan-400 border-cyan-500/40' : 'text-slate-400'}`}
          title={autoPan ? "Auto-lock vehicle ON" : "Auto-lock vehicle OFF"}
        >
          <Compass size={17} />
        </button>

        {/* Fullscreen Expand/Collapse Button */}
        <button
          onClick={onToggleFullscreen}
          className="p-2.5 rounded-xl glass-hud-overlay text-slate-300 hover:text-white transition-colors"
          title={isFullscreen ? "Collapse map" : "Expand map full view"}
        >
          {isFullscreen ? <Minimize2 size={17} /> : <Maximize2 size={17} />}
        </button>
      </div>

      {/* Legend Bottom Bar */}
      <div className="absolute bottom-4 left-4 right-4 z-[1000] glass-hud-overlay px-4 py-2.5 rounded-2xl flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-4 text-[11px] font-medium text-slate-300">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-1 rounded-full bg-blue-500" />
            <span>GNSS Trajectory</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-1 rounded-full bg-amber-500 border border-dashed" />
            <span>IMU DR</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-1 rounded-full bg-emerald-500" />
            <span className="font-semibold text-emerald-400">NAVAURA Estimate</span>
          </div>
        </div>

        <div className="text-[11px] font-mono text-slate-400">
          Time: {currentTime.toFixed(1)}s • Outage: {outageDuration.toFixed(1)}s
        </div>
      </div>
    </div>
  );
}