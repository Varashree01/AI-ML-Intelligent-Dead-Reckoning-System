import React from "react";

import {
  Activity,
  Gauge,
  Compass,
  Cpu,
} from "lucide-react";

export default function SensorDashboard({
  sensorData,
  isGpsLost,
}) {
  // ============================================================
  // SAFE SENSOR DATA
  // ============================================================

  const accel = sensorData?.accel || {
    x: 0,
    y: 0,
    z: 9.81,
    totalG: 1,
  };

  const gyro = sensorData?.gyro || {
    x: 0,
    y: 0,
    z: 0,
  };

  const mag = sensorData?.mag || {
    x: 0,
    y: 0,
    z: 0,
    fieldStrength: 0,
    heading: 0,
    cardinal: "N",
  };

  // ============================================================
  // SAFE FORMATTING
  // ============================================================

  const formatValue = (value, decimals = 2) => {
    const number = Number(value);

    if (!Number.isFinite(number)) {
      return "0.00";
    }

    return number.toFixed(decimals);
  };

  // ============================================================
  // ACCELEROMETER
  // ============================================================

  const accelX = Number(accel.x) || 0;
  const accelY = Number(accel.y) || 0;
  const accelZ = Number(accel.z) || 0;

  const totalG = Number(accel.totalG) || 0;

  // ============================================================
  // GYROSCOPE
  // ============================================================

  const gyroX = Number(gyro.x) || 0;
  const gyroY = Number(gyro.y) || 0;
  const gyroZ = Number(gyro.z) || 0;

  // ============================================================
  // MAGNETOMETER
  // ============================================================

  const magX = Number(mag.x) || 0;
  const magY = Number(mag.y) || 0;
  const magZ = Number(mag.z) || 0;

  const fieldStrength = Number(mag.fieldStrength) || 0;

  const heading = Number(mag.heading) || 0;

  const cardinal = mag.cardinal || "N";

  // ============================================================
  // G-FORCE INDICATOR
  // ============================================================

  const gForceWidth = Math.min(
    100,
    Math.max(5, totalG * 90)
  );

  // ============================================================
  // JSX
  // ============================================================

  return (
    <div className="space-y-4">

      {/* ======================================================
          SECTION HEADER
      ====================================================== */}

      <div className="flex items-center justify-between">

        <h3
          className="
            font-tech
            text-lg
            font-bold
            text-slate-100
            uppercase
            tracking-wider
            flex
            items-center
            gap-2
          "
        >
          <Activity
            className="
              w-5
              h-5
              text-cyan-400
              animate-pulse
            "
          />

          Real-Time IMU Telemetry Stream
        </h3>

        <span
          className={`
            text-xs
            font-mono
            px-2.5
            py-1
            rounded-full
            border
            ${
              isGpsLost
                ? "bg-amber-500/20 text-amber-300 border-amber-500/40 animate-pulse"
                : "bg-cyan-500/20 text-cyan-300 border-cyan-500/40"
            }
          `}
        >
          {isGpsLost
            ? "PRIMARY NAVIGATION SOURCE: IMU"
            : "IMU ACTIVE - CALIBRATED"}
        </span>

      </div>

      {/* ======================================================
          SENSOR CARDS
      ====================================================== */}

      <div
        className="
          grid
          grid-cols-1
          md:grid-cols-3
          gap-4
        "
      >

        {/* ====================================================
            ACCELEROMETER
        ==================================================== */}

        <div
          className="
            glass-panel
            p-4
            rounded-xl
            border
            border-cyan-500/20
            hover:border-cyan-400/40
            transition-all
            space-y-3
            relative
            overflow-hidden
            group
          "
        >

          {/* Header */}

          <div
            className="
              flex
              items-center
              justify-between
              border-b
              border-slate-800
              pb-2
            "
          >

            <div className="flex items-center gap-2">

              <div
                className="
                  p-1.5
                  rounded-lg
                  bg-cyan-950/80
                  border
                  border-cyan-500/30
                  text-cyan-400
                "
              >
                <Gauge className="w-4 h-4" />
              </div>

              <h4
                className="
                  font-tech
                  text-sm
                  font-bold
                  text-slate-200
                  uppercase
                  tracking-wider
                "
              >
                3-Axis Accelerometer
              </h4>

            </div>

            <span
              className="
                text-[10px]
                font-mono
                text-cyan-400
                bg-cyan-950/60
                px-2
                py-0.5
                rounded
              "
            >
              m/s²
            </span>

          </div>

          {/* Acceleration values */}

          <div className="grid grid-cols-3 gap-2 text-center">

            {/* X */}

            <div
              className="
                p-2
                rounded-lg
                bg-slate-900/80
                border
                border-slate-800
              "
            >
              <span
                className="
                  text-[10px]
                  text-slate-400
                  font-mono
                  block
                "
              >
                X-AXIS
              </span>

              <span
                className="
                  font-mono
                  text-base
                  font-bold
                  text-cyan-300
                "
              >
                {accelX >= 0 ? "+" : ""}
                {formatValue(accelX)}
              </span>
            </div>

            {/* Y */}

            <div
              className="
                p-2
                rounded-lg
                bg-slate-900/80
                border
                border-slate-800
              "
            >
              <span
                className="
                  text-[10px]
                  text-slate-400
                  font-mono
                  block
                "
              >
                Y-AXIS
              </span>

              <span
                className="
                  font-mono
                  text-base
                  font-bold
                  text-blue-300
                "
              >
                {accelY >= 0 ? "+" : ""}
                {formatValue(accelY)}
              </span>
            </div>

            {/* Z */}

            <div
              className="
                p-2
                rounded-lg
                bg-slate-900/80
                border
                border-slate-800
              "
            >
              <span
                className="
                  text-[10px]
                  text-slate-400
                  font-mono
                  block
                "
              >
                Z-AXIS
              </span>

              <span
                className="
                  font-mono
                  text-base
                  font-bold
                  text-indigo-300
                "
              >
                {accelZ >= 0 ? "+" : ""}
                {formatValue(accelZ)}
              </span>
            </div>

          </div>

          {/* G-force */}

          <div className="space-y-1">

            <div
              className="
                flex
                justify-between
                text-[11px]
                font-mono
                text-slate-400
              "
            >
              <span>
                Total Acceleration
              </span>

              <span
                className="
                  text-cyan-400
                  font-bold
                "
              >
                {formatValue(totalG)} G
              </span>
            </div>

            <div
              className="
                w-full
                bg-slate-900
                h-2
                rounded-full
                overflow-hidden
                p-0.5
                border
                border-slate-800
              "
            >
              <div
                className="
                  bg-gradient-to-r
                  from-cyan-500
                  to-blue-500
                  h-full
                  rounded-full
                  transition-all
                  duration-200
                "
                style={{
                  width: `${gForceWidth}%`,
                }}
              />
            </div>

          </div>

        </div>

        {/* ====================================================
            GYROSCOPE
        ==================================================== */}

        <div
          className="
            glass-panel
            p-4
            rounded-xl
            border
            border-purple-500/20
            hover:border-purple-400/40
            transition-all
            space-y-3
            relative
            overflow-hidden
            group
          "
        >

          {/* Header */}

          <div
            className="
              flex
              items-center
              justify-between
              border-b
              border-slate-800
              pb-2
            "
          >

            <div className="flex items-center gap-2">

              <div
                className="
                  p-1.5
                  rounded-lg
                  bg-purple-950/80
                  border
                  border-purple-500/30
                  text-purple-400
                "
              >
                <Cpu className="w-4 h-4" />
              </div>

              <h4
                className="
                  font-tech
                  text-sm
                  font-bold
                  text-slate-200
                  uppercase
                  tracking-wider
                "
              >
                Digital Gyroscope
              </h4>

            </div>

            <span
              className="
                text-[10px]
                font-mono
                text-purple-400
                bg-purple-950/60
                px-2
                py-0.5
                rounded
              "
            >
              rad/s
            </span>

          </div>

          {/* Angular velocity */}

          <div
            className="
              grid
              grid-cols-3
              gap-2
              text-center
            "
          >

            {/* X */}

            <div
              className="
                p-2
                rounded-lg
                bg-slate-900/80
                border
                border-slate-800
              "
            >

              <span
                className="
                  text-[10px]
                  text-slate-400
                  font-mono
                  block
                "
              >
                X-AXIS
              </span>

              <span
                className="
                  font-mono
                  text-base
                  font-bold
                  text-purple-300
                "
              >
                {gyroX >= 0 ? "+" : ""}
                {formatValue(gyroX)}
              </span>

            </div>

            {/* Y */}

            <div
              className="
                p-2
                rounded-lg
                bg-slate-900/80
                border
                border-slate-800
              "
            >

              <span
                className="
                  text-[10px]
                  text-slate-400
                  font-mono
                  block
                "
              >
                Y-AXIS
              </span>

              <span
                className="
                  font-mono
                  text-base
                  font-bold
                  text-pink-300
                "
              >
                {gyroY >= 0 ? "+" : ""}
                {formatValue(gyroY)}
              </span>

            </div>

            {/* Z */}

            <div
              className="
                p-2
                rounded-lg
                bg-slate-900/80
                border
                border-slate-800
              "
            >

              <span
                className="
                  text-[10px]
                  text-slate-400
                  font-mono
                  block
                "
              >
                Z-AXIS
              </span>

              <span
                className="
                  font-mono
                  text-base
                  font-bold
                  text-fuchsia-300
                "
              >
                {gyroZ >= 0 ? "+" : ""}
                {formatValue(gyroZ)}
              </span>

            </div>

          </div>

          {/* Status */}

          <div
            className="
              flex
              items-center
              justify-between
              p-2
              rounded-lg
              bg-purple-950/30
              border
              border-purple-500/20
              text-xs
              font-mono
            "
          >

            <span className="text-purple-300">
              Angular Velocity
            </span>

            <span
              className="
                text-fuchsia-400
                font-bold
                animate-pulse
              "
            >
              ACTIVE
            </span>

          </div>

        </div>

        {/* ====================================================
            MAGNETOMETER
        ==================================================== */}

        <div
          className="
            glass-panel
            p-4
            rounded-xl
            border
            border-amber-500/20
            hover:border-amber-400/40
            transition-all
            space-y-3
            relative
            overflow-hidden
            group
          "
        >

          {/* Header */}

          <div
            className="
              flex
              items-center
              justify-between
              border-b
              border-slate-800
              pb-2
            "
          >

            <div className="flex items-center gap-2">

              <div
                className="
                  p-1.5
                  rounded-lg
                  bg-amber-950/80
                  border
                  border-amber-500/30
                  text-amber-400
                "
              >
                <Compass className="w-4 h-4" />
              </div>

              <h4
                className="
                  font-tech
                  text-sm
                  font-bold
                  text-slate-200
                  uppercase
                  tracking-wider
                "
              >
                Magnetometer / Compass
              </h4>

            </div>

            <span
              className="
                text-[10px]
                font-mono
                text-amber-400
                bg-amber-950/60
                px-2
                py-0.5
                rounded
              "
            >
              {formatValue(fieldStrength)} µT
            </span>

          </div>

          {/* Compass */}

          <div
            className="
              flex
              items-center
              justify-between
              gap-3
            "
          >

            {/* Compass visual */}

            <div
              className="
                relative
                w-16
                h-16
                flex
                items-center
                justify-center
                rounded-full
                bg-slate-900
                border-2
                border-amber-500/40
                shadow-[0_0_15px_rgba(245,158,11,0.2)]
              "
            >

              <div
                className="
                  absolute
                  w-full
                  h-full
                  flex
                  items-center
                  justify-center
                  transition-transform
                  duration-300
                  ease-out
                "
                style={{
                  transform: `rotate(${heading}deg)`,
                }}
              >

                <div
                  className="
                    w-1
                    h-12
                    bg-gradient-to-t
                    from-slate-600
                    via-amber-400
                    to-red-500
                    rounded-full
                    relative
                  "
                >

                  <div
                    className="
                      absolute
                      top-0
                      left-1/2
                      -translate-x-1/2
                      w-0
                      h-0
                      border-l-[4px]
                      border-r-[4px]
                      border-b-[8px]
                      border-l-transparent
                      border-r-transparent
                      border-b-red-500
                    "
                  />

                </div>

              </div>

              <span
                className="
                  z-10
                  text-[10px]
                  font-mono
                  font-bold
                  text-amber-300
                  bg-slate-950/90
                  px-1
                  rounded
                "
              >
                N
              </span>

            </div>

            {/* Heading information */}

            <div
              className="
                flex-1
                space-y-1
                text-right
              "
            >

              <div
                className="
                  text-[10px]
                  text-slate-400
                  font-mono
                  uppercase
                "
              >
                Fused Navigation Heading
              </div>

              <div
                className="
                  font-tech
                  text-2xl
                  font-bold
                  text-amber-300
                  tracking-wider
                "
              >
                {String(
                  Math.round(heading)
                ).padStart(3, "0")}
                °{" "}
                {cardinal}
              </div>

              <div
                className="
                  text-[11px]
                  text-slate-400
                  font-mono
                "
              >
                Magnetic field:
                <span className="text-amber-400 ml-1">
                  {formatValue(fieldStrength)} µT
                </span>
              </div>

            </div>

          </div>

          {/* Magnetometer raw vector */}

          <div
            className="
              grid
              grid-cols-3
              gap-2
              text-center
            "
          >

            <div
              className="
                p-1.5
                rounded
                bg-slate-900/60
                border
                border-slate-800
              "
            >
              <span className="block text-[9px] text-slate-500 font-mono">
                MAG X
              </span>

              <span className="text-[11px] text-amber-300 font-mono">
                {formatValue(magX)}
              </span>
            </div>

            <div
              className="
                p-1.5
                rounded
                bg-slate-900/60
                border
                border-slate-800
              "
            >
              <span className="block text-[9px] text-slate-500 font-mono">
                MAG Y
              </span>

              <span className="text-[11px] text-amber-300 font-mono">
                {formatValue(magY)}
              </span>
            </div>

            <div
              className="
                p-1.5
                rounded
                bg-slate-900/60
                border
                border-slate-800
              "
            >
              <span className="block text-[9px] text-slate-500 font-mono">
                MAG Z
              </span>

              <span className="text-[11px] text-amber-300 font-mono">
                {formatValue(magZ)}
              </span>
            </div>

          </div>

        </div>

      </div>

    </div>
  );
}