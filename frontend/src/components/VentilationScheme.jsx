import { useEffect, useState } from "react";
import { api } from "../api/client.js";

function pickStatus(rad) {
  if (rad == null) return "mute";
  if (rad > 18) return "bad";
  if (rad > 12) return "warn";
  return "ok";
}

const STATUS_FILL = {
  ok:   "#10b981",
  warn: "#f59e0b",
  bad:  "#ef4444",
  mute: "#94a3b8",
};

const fmt = (v, digits = 1) => (typeof v === "number" ? v.toFixed(digits) : "—");

export default function VentilationScheme() {
  const [latest, setLatest] = useState([]);

  useEffect(() => {
    let cancel = false;
    const load = async () => {
      try {
        const { data } = await api.get("/readings/latest");
        if (!cancel) setLatest(data || []);
      } catch { /* silent */ }
    };
    load();
    const id = setInterval(load, 5000);
    return () => { cancel = true; clearInterval(id); };
  }, []);

  // Group readings by zone -> { sensor_type: value }
  const zones = {};
  for (const r of latest) {
    const z = r.zone_code || "—";
    zones[z] ||= { name: r.zone_name || z, code: z, types: {}, units: {} };
    zones[z].types[r.sensor_type] = r.value;
    zones[z].units[r.sensor_type] = r.unit;
  }
  const primary = Object.values(zones)[0] || { name: "Зона персоналу", code: "Блок 1", types: {}, units: {} };
  const status = pickStatus(primary.types.radiation);

  return (
    <div className="w-full h-full min-h-[500px] bg-slate-50 dark:bg-[#0b1120] rounded-xl flex items-center justify-center p-4 relative overflow-hidden">
      <style>{`
        @keyframes airflow {
          0% { stroke-dashoffset: 24; }
          100% { stroke-dashoffset: 0; }
        }
        .animate-airflow { animation: airflow 1s linear infinite; }
      `}</style>

      {/* Legend */}
      <div className="absolute top-4 left-4 bg-white/90 dark:bg-slate-900/90 backdrop-blur-md border border-slate-200 dark:border-slate-800 p-3.5 rounded-xl text-xs font-medium space-y-2.5 z-10 shadow-sm">
        <h4 className="text-slate-500 font-bold mb-1 uppercase tracking-wider text-[10px]">Стан елементів</h4>
        <div className="flex items-center gap-2.5">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div>
          <span className="text-slate-700 dark:text-slate-300">У роботі / Норма</span>
        </div>
        <div className="flex items-center gap-2.5">
          <div className="w-2.5 h-2.5 rounded-full bg-slate-400"></div>
          <span className="text-slate-700 dark:text-slate-300">Резерв / Вимкнено</span>
        </div>
        <div className="flex items-center gap-2.5">
          <div className="w-2.5 h-2.5 rounded-full bg-amber-500 animate-pulse shadow-[0_0_8px_rgba(245,158,11,0.5)]"></div>
          <span className="text-slate-700 dark:text-slate-300">Увага / Відхилення</span>
        </div>
        <div className="flex items-center gap-2.5 mt-2 pt-2 border-t border-slate-200 dark:border-slate-700">
          <div className="w-4 h-1 bg-blue-400"></div>
          <span className="text-slate-500 dark:text-slate-400">Свіже повітря</span>
        </div>
        <div className="flex items-center gap-2.5">
          <div className="w-4 h-1 bg-slate-400"></div>
          <span className="text-slate-500 dark:text-slate-400">Відпрацьоване</span>
        </div>
      </div>

      <svg
        viewBox="0 0 1100 500"
        className="w-full h-full max-h-[600px] select-none drop-shadow-sm"
        preserveAspectRatio="xMidYMid meet"
      >
        {/* ======= DUCT BACKBONE ======= */}
        <g className="ducts text-slate-200 dark:text-slate-800/80" stroke="currentColor" strokeWidth="16" strokeLinecap="round" strokeLinejoin="round" fill="none">
          {/* Supply line (top) */}
          <path d="M 60 150 L 650 150" />
          {/* Branch to two fans */}
          <path d="M 650 150 L 680 90 L 780 90" />
          <path d="M 650 150 L 680 210 L 780 210" />
          <path d="M 780 90 L 810 150 L 960 150" />

          {/* Exhaust line (bottom) */}
          <path d="M 960 380 L 60 380" />
        </g>

        {/* ======= ANIMATED AIRFLOW ======= */}
        <g strokeWidth="4" strokeLinecap="round" fill="none" strokeDasharray="8 16" className="animate-airflow pointer-events-none">
          {/* Supply (fresh air) */}
          <g className="stroke-blue-500/70 dark:stroke-blue-400/70">
            <path d="M 70 150 L 645 150" />
            <path d="M 650 150 L 680 90 L 775 90" />
            <path d="M 650 150 L 680 210 L 775 210" />
            <path d="M 785 90 L 810 150 L 950 150" />
          </g>
          {/* Exhaust */}
          <g className="stroke-slate-400/80 dark:stroke-slate-500/80">
            <path d="M 950 380 L 70 380" />
          </g>
        </g>

        {/* ======= COMPONENTS ======= */}

        {/* 1. Intake louvers + valve K-1 */}
        <g transform="translate(40, 130)">
          <path d="M -10 -10 L 20 20 L -10 50" fill="none" stroke="currentColor" className="text-blue-500/50" strokeWidth="6" strokeLinejoin="round" />
          <text x="5" y="70" fontSize="11" textAnchor="middle" className="fill-slate-500 font-bold">ЗАБІР</text>
        </g>
        <g transform="translate(100, 150)">
          <circle cx="0" cy="0" r="16" className="fill-white dark:fill-slate-900 stroke-slate-400" strokeWidth="3" />
          <line x1="-10" y1="10" x2="10" y2="-10" className="stroke-emerald-500" strokeWidth="4" strokeLinecap="round" />
          <text x="0" y="-25" textAnchor="middle" fontSize="10" className="fill-slate-500 font-bold">К-1</text>
        </g>

        {/* 2. Coarse filter F-101 */}
        <g transform="translate(180, 120)">
          <rect x="0" y="0" width="40" height="60" rx="4" className="fill-white dark:fill-slate-900 stroke-emerald-500" strokeWidth="3" />
          <path d="M 10 0 L 30 60 M 20 0 L 40 60 M 0 0 L 20 60" className="stroke-emerald-500/30" strokeWidth="2" />
          <text x="20" y="-12" textAnchor="middle" fontSize="14" className="fill-slate-700 dark:fill-slate-200 font-bold">Ф-101</text>
          <text x="20" y="80" textAnchor="middle" fontSize="11" className="fill-slate-500 font-medium">120 Pa</text>
        </g>

        {/* 3. Recuperator (cross-flow heat exchanger) */}
        <g transform="translate(300, 265)">
          <rect x="-40" y="-135" width="80" height="270" rx="8" className="fill-slate-100 dark:fill-slate-800 stroke-slate-300 dark:stroke-slate-600" strokeWidth="3" />
          <path d="M -40 -110 L 40 110 M -40 110 L 40 -110" className="stroke-slate-300 dark:stroke-slate-600" strokeWidth="2" />
          <text x="0" y="0" textAnchor="middle" className="fill-slate-400 dark:fill-slate-500 font-bold tracking-widest" fontSize="14" transform="rotate(-90)">РЕКУПЕРАТОР</text>
        </g>

        {/* 4. Heater */}
        <g transform="translate(420, 150)">
          <rect x="-25" y="-35" width="50" height="70" rx="6" className="fill-red-50 dark:fill-red-900/10 stroke-red-500" strokeWidth="3" />
          <path d="M -12 -20 L 12 -5 L -12 10 L 12 25" className="stroke-red-500" strokeWidth="3" strokeLinejoin="round" fill="none" />
          <text x="0" y="-45" textAnchor="middle" fontSize="12" className="fill-red-600 dark:fill-red-400 font-bold">КАЛОРИФЕР</text>
        </g>

        {/* 5. HEPA filter F-102 (warning) */}
        <g transform="translate(520, 120)">
          <rect x="0" y="0" width="40" height="60" rx="4" className="fill-amber-50 dark:fill-amber-900/20 stroke-amber-500" strokeWidth="3" />
          <path d="M 5 0 L 5 60 M 15 0 L 15 60 M 25 0 L 25 60 M 35 0 L 35 60" className="stroke-amber-500/50" strokeWidth="2" strokeDasharray="4 2" />
          <text x="20" y="-12" textAnchor="middle" fontSize="14" className="fill-amber-600 dark:fill-amber-400 font-bold">Ф-102</text>
          <text x="20" y="80" textAnchor="middle" fontSize="12" className="fill-amber-600 dark:fill-amber-400 font-bold">480 Pa!</text>
          <circle cx="48" cy="-18" r="5" className="fill-amber-500 animate-pulse" />
        </g>

        {/* 6. Fan M-1 (working) */}
        <g transform="translate(730, 90)">
          <circle cx="0" cy="0" r="26" className="fill-white dark:fill-slate-900 stroke-emerald-500" strokeWidth="3" />
          <g>
            <animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="1.5s" repeatCount="indefinite" />
            <path d="M 0 -14 L 0 14 M -12.1 -7 L 12.1 7 M -12.1 7 L 12.1 -7" className="stroke-emerald-500" strokeWidth="4" strokeLinecap="round" />
            <circle cx="0" cy="0" r="4" className="fill-emerald-500" />
          </g>
          <text x="0" y="-38" textAnchor="middle" fontSize="14" className="fill-slate-700 dark:fill-slate-200 font-bold">М-1</text>
          <text x="0" y="42" textAnchor="middle" fontSize="11" className="fill-slate-500">1450 RPM</text>
        </g>

        {/* 7. Fan M-2 (working) */}
        <g transform="translate(730, 210)">
          <circle cx="0" cy="0" r="26" className="fill-white dark:fill-slate-900 stroke-emerald-500" strokeWidth="3" />
          <g>
            <animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="1.6s" repeatCount="indefinite" />
            <path d="M 0 -14 L 0 14 M -12.1 -7 L 12.1 7 M -12.1 7 L 12.1 -7" className="stroke-emerald-500" strokeWidth="4" strokeLinecap="round" />
            <circle cx="0" cy="0" r="4" className="fill-emerald-500" />
          </g>
          <text x="0" y="-38" textAnchor="middle" fontSize="14" className="fill-slate-700 dark:fill-slate-200 font-bold">М-2</text>
          <text x="0" y="42" textAnchor="middle" fontSize="11" className="fill-slate-500">1420 RPM</text>
        </g>

        {/* 8. T/H sensor */}
        <g transform="translate(880, 150)">
          <rect x="-18" y="-40" width="36" height="22" rx="3" className="fill-white dark:fill-slate-800 stroke-blue-500" strokeWidth="2" />
          <text x="0" y="-25" textAnchor="middle" fontSize="9" className="fill-blue-600 dark:fill-blue-400 font-bold">
            {fmt(primary.types.temperature, 1)}°
          </text>
          <path d="M 0 -18 L 0 0" className="stroke-blue-500" strokeWidth="2" />
        </g>

        {/* 9. Target zone (Block 1) */}
        <g transform="translate(960, 110)">
          <rect x="0" y="0" width="120" height="300" rx="12" className="fill-slate-200/50 dark:fill-slate-800/30 stroke-slate-300 dark:stroke-slate-700" strokeWidth="3" strokeDasharray="8 6" />
          <text x="60" y="40" textAnchor="middle" fontSize="16" className="fill-slate-700 dark:fill-slate-300 font-bold">{primary.code || "Блок 1"}</text>
          <text x="60" y="58" textAnchor="middle" fontSize="11" className="fill-slate-500 dark:fill-slate-400 font-medium">{primary.name || "Зона персоналу"}</text>

          {/* Status dot */}
          <circle cx="60" cy="90" r="9" fill={STATUS_FILL[status]}>
            {status !== "mute" && <animate attributeName="opacity" values="1;0.4;1" dur="1.6s" repeatCount="indefinite" />}
          </circle>

          {/* Live readings */}
          {[
            ["radiation", "Рад", "μSv/h"],
            ["pressure", "Тиск", "Pa"],
            ["airflow", "Витр", "m³/h"],
            ["temperature", "Темп", "°C"],
          ].map(([k, label, defaultUnit], idx) => {
            const v = primary.types[k];
            const u = primary.units[k] || defaultUnit;
            return (
              <g key={k} transform={`translate(12, ${130 + idx * 38})`}>
                <text x="0" y="0" fontSize="10" className="fill-slate-500 dark:fill-slate-400 font-medium">{label}</text>
                <text x="0" y="16" fontSize="13" className="fill-slate-900 dark:fill-white font-semibold">
                  {fmt(v)}
                  <tspan fontSize="9" className="fill-slate-400"> {u}</tspan>
                </text>
              </g>
            );
          })}
        </g>

        {/* ======= EXHAUST LINE ======= */}

        {/* 10. Filter F-201 */}
        <g transform="translate(760, 350)">
          <rect x="0" y="0" width="60" height="60" rx="4" className="fill-white dark:fill-slate-900 stroke-slate-400 dark:stroke-slate-500" strokeWidth="3" />
          <path d="M 10 15 L 50 15 M 10 30 L 50 30 M 10 45 L 50 45" className="stroke-slate-400/50" strokeWidth="4" strokeLinecap="round" />
          <text x="30" y="-12" textAnchor="middle" fontSize="14" className="fill-slate-700 dark:fill-slate-200 font-bold">Ф-201</text>
          <text x="30" y="80" textAnchor="middle" fontSize="11" className="fill-slate-500">190 Pa</text>
        </g>

        {/* 11. Fan M-3 (reserve, stopped) */}
        <g transform="translate(560, 380)">
          <circle cx="0" cy="0" r="26" className="fill-slate-100 dark:fill-slate-800 stroke-slate-400 dark:stroke-slate-600" strokeWidth="3" />
          <g>
            <path d="M 0 -14 L 0 14 M -12.1 -7 L 12.1 7 M -12.1 7 L 12.1 -7" className="stroke-slate-400 dark:stroke-slate-600" strokeWidth="4" strokeLinecap="round" />
            <circle cx="0" cy="0" r="4" className="fill-slate-400" />
          </g>
          <text x="0" y="-38" textAnchor="middle" fontSize="14" className="fill-slate-500 dark:fill-slate-400 font-bold">М-3 (Резерв)</text>
          <text x="0" y="42" textAnchor="middle" fontSize="11" className="fill-slate-400">0 RPM</text>
        </g>

        {/* 12. Exhaust valve K-2 */}
        <g transform="translate(140, 380)">
          <circle cx="0" cy="0" r="16" className="fill-white dark:fill-slate-900 stroke-slate-400" strokeWidth="3" />
          <line x1="-10" y1="10" x2="10" y2="-10" className="stroke-emerald-500" strokeWidth="4" strokeLinecap="round" />
          <text x="0" y="-25" textAnchor="middle" fontSize="10" className="fill-slate-500 font-bold">К-2</text>
        </g>

        {/* 13. Exhaust louvers */}
        <g transform="translate(40, 360)">
          <path d="M 20 -10 L -10 20 L 20 50" fill="none" stroke="currentColor" className="text-slate-400/50" strokeWidth="6" strokeLinejoin="round" />
          <text x="5" y="75" fontSize="11" textAnchor="middle" className="fill-slate-500 font-bold">ВИКИД</text>
        </g>
      </svg>
    </div>
  );
}
