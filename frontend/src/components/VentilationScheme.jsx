import React from 'react';

const STATUS_FILL = {
  ok:   "#10b981",
  warn: "#f59e0b",
  bad:  "#ef4444",
  mute: "#94a3b8",
};

function dpStatus(dp) {
  if (dp == null) return "mute";
  if (dp < 0)  return "bad";
  if (dp < 2)  return "warn";
  return "ok";
}

const fmt = (v, digits = 1) => (typeof v === "number" ? v.toFixed(digits) : "—");

export default function VentilationScheme({ stats = [] }) {
  const m = Object.fromEntries(stats.map((r) => [r.sensor_type, r]));

  const dp        = m.dp_kp_oo?.mean;
  const pKp       = m.pressure_kp?.mean;
  const pOo       = m.pressure_oo?.mean;
  const flowKpIn  = m.flow_kp_in?.mean;
  const flowOoOut = m.flow_oo_out?.mean;
  const wind      = m.wind_speed?.mean;
  const windDir   = m.wind_direction?.mean;
  const guW       = m.gu_pressure_west_wall?.mean;
  const guE       = m.gu_pressure_east_wall?.mean;
  const guC       = m.gu_pressure_cyl_wall?.mean;

  const overall = dpStatus(dp);

  return (
    <div className="w-full h-full min-h-[500px] bg-slate-50 dark:bg-[#0b1120] rounded-xl flex items-center justify-center p-4 relative overflow-hidden">
      <style>{`
        @keyframes airflow {
          0% { stroke-dashoffset: 24; }
          100% { stroke-dashoffset: 0; }
        }
        .animate-airflow { animation: airflow 1s linear infinite; }
      `}</style>

      <div className="absolute top-4 left-4 bg-white/90 dark:bg-slate-900/90 backdrop-blur-md border border-slate-200 dark:border-slate-800 p-3.5 rounded-xl text-xs font-medium space-y-2.5 z-10 shadow-sm">
        <h4 className="text-slate-500 font-bold mb-1 uppercase tracking-wider text-[10px]">Стан зон</h4>
        <div className="flex items-center gap-2.5">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div>
          <span className="text-slate-700 dark:text-slate-300">КП під розрідженням (норма)</span>
        </div>
        <div className="flex items-center gap-2.5">
          <div className="w-2.5 h-2.5 rounded-full bg-amber-500 animate-pulse"></div>
          <span className="text-slate-700 dark:text-slate-300">Перепад КП-ОО {"<"}2 Па</span>
        </div>
        <div className="flex items-center gap-2.5">
          <div className="w-2.5 h-2.5 rounded-full bg-red-500"></div>
          <span className="text-slate-700 dark:text-slate-300">Зворотній потік (Δp{"<"}0)</span>
        </div>
        <div className="flex items-center gap-2.5 mt-2 pt-2 border-t border-slate-200 dark:border-slate-700">
          <div className="w-4 h-1 bg-blue-400"></div>
          <span className="text-slate-500 dark:text-slate-400">КП+ Приплив</span>
        </div>
        <div className="flex items-center gap-2.5">
          <div className="w-4 h-1 bg-slate-400"></div>
          <span className="text-slate-500 dark:text-slate-400">ОО− Витяжка</span>
        </div>
      </div>

      <div className="absolute top-4 right-4 bg-white/90 dark:bg-slate-900/90 backdrop-blur-md border border-slate-200 dark:border-slate-800 p-3 rounded-xl text-xs font-medium z-10 shadow-sm">
        <div className="text-slate-500 uppercase tracking-wider text-[10px] mb-1">Зовнішній вітер</div>
        <div className="text-slate-900 dark:text-white text-base font-bold">
          {fmt(wind, 2)} <span className="text-xs font-normal text-slate-400">м/с</span>
        </div>
        <div className="text-slate-500 text-xs mt-0.5">
          напрям {fmt(windDir, 0)}°
        </div>
      </div>

      <svg
        viewBox="0 0 1100 500"
        className="w-full h-full max-h-[600px] select-none drop-shadow-sm"
        preserveAspectRatio="xMidYMid meet"
      >
        <g className="ducts text-slate-200 dark:text-slate-800/80" stroke="currentColor" strokeWidth="16" strokeLinecap="round" strokeLinejoin="round" fill="none">
          <path d="M 60 150 L 650 150 L 680 90 L 780 90 L 810 150 L 960 150" />
          <path d="M 960 310 L 850 310 L 800 210 L 780 210" />
          <path d="M 680 210 L 675 210 L 590 380 L 60 380" />
        </g>

        <g strokeWidth="4" strokeLinecap="round" fill="none" strokeDasharray="8 16" className="animate-airflow pointer-events-none">
          <g className="stroke-blue-500/70 dark:stroke-blue-400/70">
            <path d="M 70 150 L 645 150 L 680 90 L 775 90" />
            <path d="M 785 90 L 810 150 L 950 150" />
          </g>
          <g className="stroke-slate-400/80 dark:stroke-slate-500/80">
            <path d="M 950 310 L 850 310 L 800 210 L 785 210" />
            <path d="M 675 210 L 590 380 L 70 380" />
          </g>
        </g>

        <g transform="translate(40, 130)">
          <path d="M -10 -10 L 20 20 L -10 50" fill="none" stroke="currentColor" className="text-blue-500/50" strokeWidth="6" strokeLinejoin="round" />
          <text x="5" y="70" fontSize="11" textAnchor="middle" className="fill-slate-500 font-bold">ЗАБІР</text>
        </g>
        <g transform="translate(100, 150)">
          <circle cx="0" cy="0" r="16" className="fill-white dark:fill-slate-900 stroke-slate-400" strokeWidth="3" />
          <line x1="-10" y1="10" x2="10" y2="-10" className="stroke-emerald-500" strokeWidth="4" strokeLinecap="round" />
          <text x="0" y="-25" textAnchor="middle" fontSize="10" className="fill-slate-500 font-bold">К-1</text>
        </g>

        <g transform="translate(180, 120)">
          <rect x="0" y="0" width="40" height="60" rx="4" className="fill-white dark:fill-slate-900 stroke-emerald-500" strokeWidth="3" />
          <path d="M 10 0 L 30 60 M 20 0 L 40 60 M 0 0 L 20 60" className="stroke-emerald-500/30" strokeWidth="2" />
          <text x="20" y="-12" textAnchor="middle" fontSize="14" className="fill-slate-700 dark:fill-slate-200 font-bold">Ф-101</text>
          <text x="20" y="80" textAnchor="middle" fontSize="11" className="fill-slate-500 font-medium">120 Pa</text>
        </g>

        <g transform="translate(300, 265)">
          <rect x="-40" y="-135" width="80" height="270" rx="8" className="fill-slate-100 dark:fill-slate-800 stroke-slate-300 dark:stroke-slate-600" strokeWidth="3" />
          <path d="M -40 -110 L 40 110 M -40 110 L 40 -110" className="stroke-slate-300 dark:stroke-slate-600" strokeWidth="2" />
          <text x="0" y="0" textAnchor="middle" className="fill-slate-400 dark:fill-slate-500 font-bold tracking-widest" fontSize="14" transform="rotate(-90)">РЕКУПЕРАТОР</text>
        </g>

        <g transform="translate(420, 150)">
          <rect x="-25" y="-35" width="50" height="70" rx="6" className="fill-red-50 dark:fill-red-900/10 stroke-red-500" strokeWidth="3" />
          <path d="M -12 -20 L 12 -5 L -12 10 L 12 25" className="stroke-red-500" strokeWidth="3" strokeLinejoin="round" fill="none" />
          <text x="0" y="-45" textAnchor="middle" fontSize="12" className="fill-red-600 dark:fill-red-400 font-bold">КАЛОРИФЕР</text>
        </g>

        <g transform="translate(520, 120)">
          <rect x="0" y="0" width="40" height="60" rx="4" className="fill-amber-50 dark:fill-amber-900/20 stroke-amber-500" strokeWidth="3" />
          <path d="M 5 0 L 5 60 M 15 0 L 15 60 M 25 0 L 25 60 M 35 0 L 35 60" className="stroke-amber-500/50" strokeWidth="2" strokeDasharray="4 2" />
          <text x="20" y="-12" textAnchor="middle" fontSize="14" className="fill-amber-600 dark:fill-amber-400 font-bold">Ф-102</text>
          <text x="20" y="80" textAnchor="middle" fontSize="12" className="fill-amber-600 dark:fill-amber-400 font-bold">HEPA</text>
        </g>

        <g transform="translate(730, 90)">
          <circle cx="0" cy="0" r="26" className="fill-white dark:fill-slate-900 stroke-emerald-500" strokeWidth="3" />
          <g>
            <animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="1.5s" repeatCount="indefinite" />
            <path d="M 0 -14 L 0 14 M -12.1 -7 L 12.1 7 M -12.1 7 L 12.1 -7" className="stroke-emerald-500" strokeWidth="4" strokeLinecap="round" />
            <circle cx="0" cy="0" r="4" className="fill-emerald-500" />
          </g>
          <text x="0" y="-38" textAnchor="middle" fontSize="14" className="fill-slate-700 dark:fill-slate-200 font-bold">М-1 КП+</text>
          <text x="0" y="42" textAnchor="middle" fontSize="11" className="fill-slate-500">{fmt(flowKpIn, 1)} тис.м³/год</text>
        </g>

        <g transform="translate(730, 210)">
          <circle cx="0" cy="0" r="26" className="fill-white dark:fill-slate-900 stroke-emerald-500" strokeWidth="3" />
          <g>
            <animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="1.6s" repeatCount="indefinite" />
            <path d="M 0 -14 L 0 14 M -12.1 -7 L 12.1 7 M -12.1 7 L 12.1 -7" className="stroke-emerald-500" strokeWidth="4" strokeLinecap="round" />
            <circle cx="0" cy="0" r="4" className="fill-emerald-500" />
          </g>
          <text x="0" y="-38" textAnchor="middle" fontSize="14" className="fill-slate-700 dark:fill-slate-200 font-bold">М-2 ОО−</text>
          <text x="0" y="42" textAnchor="middle" fontSize="11" className="fill-slate-500">{fmt(flowOoOut, 1)} тис.м³/год</text>
        </g>

        <g transform="translate(960, 110)">
          <rect x="0" y="0" width="120" height="170" rx="12" className="fill-slate-200/50 dark:fill-slate-800/30 stroke-slate-300 dark:stroke-slate-700" strokeWidth="3" strokeDasharray="8 6" />
          <text x="60" y="28" textAnchor="middle" fontSize="14" className="fill-slate-700 dark:fill-slate-300 font-bold">КП</text>
          <text x="60" y="44" textAnchor="middle" fontSize="9" className="fill-slate-500 dark:fill-slate-400">Герм. зона</text>
          <circle cx="60" cy="68" r="9" fill={STATUS_FILL[overall]}>
            {overall !== "mute" && <animate attributeName="opacity" values="1;0.4;1" dur="1.6s" repeatCount="indefinite" />}
          </circle>
          <g transform="translate(12, 92)">
            <text x="0" y="0" fontSize="9" className="fill-slate-500 dark:fill-slate-400 font-medium">Тиск КП</text>
            <text x="0" y="14" fontSize="12" className="fill-slate-900 dark:fill-white font-semibold">{fmt(pKp, 1)} <tspan fontSize="9" className="fill-slate-400">Pa</tspan></text>
          </g>
          <g transform="translate(12, 130)">
            <text x="0" y="0" fontSize="9" className="fill-slate-500 dark:fill-slate-400 font-medium">Δp КП-ОО</text>
            <text x="0" y="14" fontSize="12" className="fill-slate-900 dark:fill-white font-semibold">{fmt(dp, 2)} <tspan fontSize="9" className="fill-slate-400">Pa</tspan></text>
          </g>
        </g>

        <g transform="translate(960, 290)">
          <rect x="0" y="0" width="120" height="120" rx="12" className="fill-slate-200/50 dark:fill-slate-800/30 stroke-slate-300 dark:stroke-slate-700" strokeWidth="3" strokeDasharray="8 6" />
          <text x="60" y="22" textAnchor="middle" fontSize="14" className="fill-slate-700 dark:fill-slate-300 font-bold">ОО</text>
          <text x="60" y="38" textAnchor="middle" fontSize="9" className="fill-slate-500 dark:fill-slate-400">Обстеж. зона</text>
          <g transform="translate(12, 60)">
            <text x="0" y="0" fontSize="9" className="fill-slate-500 dark:fill-slate-400 font-medium">Тиск ОО</text>
            <text x="0" y="14" fontSize="12" className="fill-slate-900 dark:fill-white font-semibold">{fmt(pOo, 1)} <tspan fontSize="9" className="fill-slate-400">Pa</tspan></text>
          </g>
          <g transform="translate(12, 92)">
            <text x="0" y="0" fontSize="9" className="fill-slate-500 dark:fill-slate-400 font-medium">Витяжка</text>
            <text x="0" y="14" fontSize="12" className="fill-slate-900 dark:fill-white font-semibold">{fmt(flowOoOut, 1)} <tspan fontSize="9" className="fill-slate-400">тис.м³/год</tspan></text>
          </g>
        </g>

        <g transform="translate(620, 350)">
          <rect x="-10" y="0" width="220" height="90" rx="10" className="fill-slate-100/70 dark:fill-slate-800/40 stroke-slate-300 dark:stroke-slate-700" strokeWidth="2" strokeDasharray="4 4" />
          <text x="100" y="20" textAnchor="middle" fontSize="12" className="fill-slate-600 dark:fill-slate-300 font-bold">ГУ ТИСК НА СТІНКАХ</text>
          <g transform="translate(0, 36)">
            <text x="0"  y="0" fontSize="9"  className="fill-slate-500 font-medium">Зах.</text>
            <text x="0"  y="14" fontSize="11" className="fill-slate-900 dark:fill-white font-semibold">{fmt(guW, 1)}</text>
          </g>
          <g transform="translate(70, 36)">
            <text x="0"  y="0" fontSize="9"  className="fill-slate-500 font-medium">Сх.</text>
            <text x="0"  y="14" fontSize="11" className="fill-slate-900 dark:fill-white font-semibold">{fmt(guE, 1)}</text>
          </g>
          <g transform="translate(140, 36)">
            <text x="0"  y="0" fontSize="9"  className="fill-slate-500 font-medium">Цил.</text>
            <text x="0"  y="14" fontSize="11" className="fill-slate-900 dark:fill-white font-semibold">{fmt(guC, 1)}</text>
          </g>
        </g>

        <g transform="translate(360, 350)">
          <rect x="0" y="0" width="60" height="60" rx="4" className="fill-white dark:fill-slate-900 stroke-slate-400 dark:stroke-slate-500" strokeWidth="3" />
          <path d="M 10 15 L 50 15 M 10 30 L 50 30 M 10 45 L 50 45" className="stroke-slate-400/50" strokeWidth="4" strokeLinecap="round" />
          <text x="30" y="-12" textAnchor="middle" fontSize="14" className="fill-slate-700 dark:fill-slate-200 font-bold">Ф-201</text>
          <text x="30" y="80" textAnchor="middle" fontSize="11" className="fill-slate-500">190 Pa</text>
        </g>

        <g transform="translate(140, 380)">
          <circle cx="0" cy="0" r="16" className="fill-white dark:fill-slate-900 stroke-slate-400" strokeWidth="3" />
          <line x1="-10" y1="10" x2="10" y2="-10" className="stroke-emerald-500" strokeWidth="4" strokeLinecap="round" />
          <text x="0" y="-25" textAnchor="middle" fontSize="10" className="fill-slate-500 font-bold">К-2</text>
        </g>

        <g transform="translate(40, 360)">
          <path d="M 20 -10 L -10 20 L 20 50" fill="none" stroke="currentColor" className="text-slate-400/50" strokeWidth="6" strokeLinejoin="round" />
          <text x="5" y="75" fontSize="11" textAnchor="middle" className="fill-slate-500 font-bold">ВИКИД</text>
        </g>
      </svg>
    </div>
  );
}