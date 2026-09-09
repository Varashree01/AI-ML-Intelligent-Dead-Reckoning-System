/**
 * AI-ML Intelligent Dead Reckoning System - Core Simulation Engine
 * Problem Statement: SIH26168
 */

// Generate realistic route waypoints along a curve representing a road entering a tunnel
export const generateRouteWaypoints = () => {
  const waypoints = [];
  const startLat = 18.9920;
  const startLng = 73.1180;
  const totalPoints = 120;
  
  for (let i = 0; i < totalPoints; i++) {
    // Generate curved highway route with tunnel section between index 35 and 85
    const progress = i / totalPoints;
    const curveOffset = Math.sin(progress * Math.PI * 2.5) * 0.0035;
    
    const lat = startLat + progress * 0.012 + curveOffset * 0.2;
    const lng = startLng + progress * 0.016 + curveOffset * 0.8;
    
    // Mark tunnel zone coordinates (indices 35 to 85)
    const isTunnelZone = i >= 35 && i <= 85;
    
    waypoints.push({
      index: i,
      lat,
      lng,
      isTunnelZone
    });
  }
  
  return waypoints;
};

// Map center initial bounds
export const INITIAL_MAP_CENTER = [18.9950, 73.1230];

// Tunnel Polygon coordinates for Map Overlay
export const TUNNEL_POLYGON = [
  [18.9950, 73.1215],
  [18.9958, 73.1228],
  [18.9995, 73.1278],
  [18.9985, 73.1288],
  [18.9945, 73.1225],
];

export const TUNNEL_ENTRANCE = [18.9955, 73.1222];
export const TUNNEL_EXIT = [18.9990, 73.1283];

// Helper to convert heading degrees into Cardinal Direction
export const getCardinalDirection = (deg) => {
  const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
  const index = Math.round(((deg % 360) + 360) % 360 / 45) % 8;
  return directions[index];
};

// Calculate Haversine distance in meters between two lat/lng points
export const calculateDistanceMeters = (lat1, lon1, lat2, lon2) => {
  const R = 6371000; // Radius of earth in meters
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = 
    Math.sin(dLat/2) * Math.sin(dLat/2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
    Math.sin(dLon/2) * Math.sin(dLon/2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  return R * c;
};

// Dead Reckoning Step update calculation
export const stepDeadReckoning = (prevPos, speedKmh, headingDeg, dtSeconds, imuNoiseFactor = 1.0) => {
  const speedMs = (speedKmh * 1000) / 3600;
  const distance = speedMs * dtSeconds;
  
  // Add realistic IMU accelerometer/gyroscope integration drift noise
  // Drift grows with noise factor
  const angleRad = (headingDeg + (Math.random() - 0.45) * 1.5 * imuNoiseFactor) * (Math.PI / 180);
  
  // 1 degree lat approx 111,000 meters; 1 degree lng approx 111,000 * cos(lat) meters
  const deltaLat = (distance * Math.cos(angleRad)) / 111000;
  const deltaLng = (distance * Math.sin(angleRad)) / (111000 * Math.cos(prevPos.lat * Math.PI / 180));
  
  // Cumulative bias factor to simulate gyro drift
  const biasLat = (Math.random() - 0.4) * 0.000008 * imuNoiseFactor;
  const biasLng = (Math.random() - 0.3) * 0.000010 * imuNoiseFactor;

  return {
    lat: prevPos.lat + deltaLat + biasLat,
    lng: prevPos.lng + deltaLng + biasLng,
  };
};

// AI Error Correction Step calculation
// Uses simulated LSTM model prediction to subtract estimated drift vector from DR position
export const stepAICorrectedPosition = (actualGps, drPos, outageDuration) => {
  // If outage duration is zero, AI position equals actual GPS
  if (outageDuration <= 0) return { ...actualGps };
  
  // AI predicts 85-92% of the cumulative drift vector and corrects it
  const latError = drPos.lat - actualGps.lat;
  const lngError = drPos.lng - actualGps.lng;
  
  // LSTM residual error predictor reduces drift significantly
  const aiCorrectionEfficiency = 0.88 + Math.min(0.08, outageDuration * 0.002);
  
  return {
    lat: drPos.lat - latError * aiCorrectionEfficiency,
    lng: drPos.lng - lngError * aiCorrectionEfficiency,
  };
};

// Generate realistic simulated IMU sensor telemetry
export const generateSensorTelemetry = (speedKmh, isGpsLost, isMoving) => {
  const baseAccelX = isMoving ? (Math.random() - 0.5) * 0.8 + 0.15 : 0.02;
  const baseAccelY = isMoving ? (Math.sin(Date.now() / 300) * 0.6) + (speedKmh / 50) : 0.05;
  const baseAccelZ = 9.81 + (isMoving ? (Math.random() - 0.5) * 0.4 : 0.01);

  const gyroRoll = isMoving ? (Math.sin(Date.now() / 500) * 2.4).toFixed(2) : '0.02';
  const gyroPitch = isMoving ? (Math.cos(Date.now() / 600) * 1.8).toFixed(2) : '0.01';
  const gyroYaw = isMoving ? (Math.sin(Date.now() / 400) * 3.5).toFixed(2) : '0.00';

  const heading = Math.round((42 + Math.sin(Date.now() / 2000) * 15 + 360) % 360);

  return {
    accel: {
      x: baseAccelX.toFixed(2),
      y: baseAccelY.toFixed(2),
      z: baseAccelZ.toFixed(2),
      totalG: (Math.sqrt(baseAccelX**2 + baseAccelY**2 + baseAccelZ**2) / 9.81).toFixed(2)
    },
    gyro: {
      roll: gyroRoll,
      pitch: gyroPitch,
      yaw: gyroYaw
    },
    mag: {
      heading: heading,
      cardinal: getCardinalDirection(heading),
      fieldStrength: (42.5 + Math.random() * 1.2).toFixed(1)
    }
  };
};
