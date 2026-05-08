import { useEffect, useState } from "react";
import {
  Activity,
  ShieldCheck,
  AlertOctagon,
  Wind,
  Gauge,
  TrendingUp,
  Minus,
  List,
  BrainCircuit,
  ChevronDown,
  ChevronUp,
  Compass,
} from "lucide-react";
import { api } from "../api/client.js";
import { useI18n } from "../i18n/i18n.jsx";
import VentilationScheme from "../components/VentilationScheme.jsx";
import TrendChart from "../components/TrendChart.jsx";

// All channels the prediction endpoint understands — backend ignores
// the ones it doesn't weight, so we just pass everything we have.
const PREDICT_CHANNELS = [
  "pressure_kp", "pressure_oo",
  "dp_kp_oo", "dp_kp_os", "dp_oo_os_8", "dp_oo_os_9",
  "dp_kp_oo_by", "dp_kp_oo_bz", "dp_kp_oo_ca",
  "flow_kp_in", "flow_oo_out", "flow_oo_in",
  "wind_speed",
  "gu_pressure_west_wall", "gu_pressure_east_wall", "gu_pressure_cyl_wall",
  "gu_pressure_west_gap",  "gu_pressure_east_gap",  "gu_pressure_vsro",
  "gu_sigma_008", "gu_sigma_009", "gu_sigma_kp_os",
];

export default function DashboardPage() {
  const { t } = useI18n();
  const [latest, setLatest] = useState([]);
  const [stats, setStats] = useState([]);
  const [prediction, setPrediction] = useState(null);

  const refresh = async () => {
    try {
      const [a, b] = await Promise.all([
        api.get("/readings/latest"),
        api.get("/analytic/stats", { params: { hours: 24 } }),
      ]);
      setLatest(a.data || []);
      const s = b.data || [];
      setStats(s);
      return s;
    } catch { return null; }
  };

  const refreshPredict = async (currentStats) => {
    try {
      const src = currentStats ?? stats;
      const byT = Object.fromEntries(src.map((s) => [s.sensor_type, s]));
      const params = {};
      for (const k of PREDICT_CHANNELS) {
        if (byT[k]) params[k] = byT[k].mean;
      }
      const r = await api.get("/analytic/predict", { params });
      setPrediction(r.data);
    } catch { /* silent */ }
  };

  useEffect(() => {
    refresh().then((s) => { if (s) refreshPredict(s); });
    const id1 = setInterval(async () => {
      const s = await refresh();
      if (s) refreshPredict(s);
    }, 10000);
    return () => clearInterval(id1);
  }, []);

  const byType = Object.fromEntries(stats.map((s) => [s.sensor_type, s]));
  const dpKpOo = byType.dp_kp_oo?.mean ?? null;
  const overall = (dpKpOo !== null && dpKpOo < 0) ? "warn" : "ok";

  const cards = [
    {
      label: t("systemStatus"),
      value: overall === "warn" ? t("warning") : t("optimal"),
      icon: ShieldCheck,
      tone: overall === "warn" ? "warn" : "ok",
      hint: t("updatedNow"),
    },
    {
      label: t("dp_kp_oo"),
      value: byType.dp_kp_oo ? `${byType.dp_kp_oo.mean.toFixed(2)} Па` : "—",
      icon: AlertOctagon,
      tone: byType.dp_kp_oo && byType.dp_kp_oo.mean < 0 ? "warn" : "ok",
      hint: byType.dp_kp_oo
        ? `min ${byType.dp_kp_oo.min.toFixed(1)} · max ${byType.dp_kp_oo.max.toFixed(1)}`
        : t("liveData"),
    },
    {
      label: t("pressure_kp"),
      value: byType.pressure_kp ? `${byType.pressure_kp.mean.toFixed(1)} Па` : "—",
      icon: Gauge,
      tone: byType.pressure_kp && Math.abs(byType.pressure_kp.mean) > 50 ? "warn" : "info",
      hint: byType.pressure_kp ? `n=${byType.pressure_kp.count}` : t("liveData"),
    },
    {
      label: t("flow_kp_in"),
      value: byType.flow_kp_in ? `${byType.flow_kp_in.mean.toFixed(1)} тис. м³/год` : "—",
      icon: Wind,
      tone: "info",
      hint: t("liveData"),
    },
  ];

  const meteoCards = [
    {
      label: t("wind_speed"),
      value: byType.wind_speed ? `${byType.wind_speed.mean.toFixed(2)} м/с` : "—",
      icon: Wind,
      tone: byType.wind_speed && byType.wind_speed.mean > 8 ? "warn" : "neutral",
      hint: byType.wind_speed ? `max ${byType.wind_speed.max.toFixed(1)}` : "",
    },
    {
      label: t("wind_direction"),
      value: byType.wind_direction ? `${byType.wind_direction.mean.toFixed(0)}°` : "—",
      icon: Compass,
      tone: "neutral",
      hint: "",
    },
    {
      label: t("pressure_oo"),
      value: byType.pressure_oo ? `${byType.pressure_oo.mean.toFixed(1)} Па` : "—",
      icon: Gauge,
      tone: "info",
      hint: byType.pressure_oo ? `min ${byType.pressure_oo.min.toFixed(1)}` : "",
    },
    {
      label: t("flow_oo_out"),
      value: byType.flow_oo_out ? `${byType.flow_oo_out.mean.toFixed(1)} тис. м³/год` : "—",
      icon: Wind,
      tone: "info",
      hint: "",
    },
  ];

  const events = buildEvents(latest, t);

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      <div>
        <h2 className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-white tracking-tight">
          {t("dashboard")}
        </h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{t("liveData")}</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
        {cards.map((c) => <StatCard key={c.label} {...c} />)}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
        {meteoCards.map((c) => <StatCard key={c.label} {...c} />)}
      </div>

      {prediction && <PredictCard data={prediction} />}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 card overflow-hidden flex flex-col min-h-[420px]">
          <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-800">
            <h3 className="font-semibold text-slate-900 dark:text-white">{t("scheme")}</h3>
          </div>
          <div className="flex-1 bg-slate-50 dark:bg-[#0b1120]">
            <VentilationScheme />
          </div>
        </div>

        <div className="card flex flex-col min-h-[420px]">
          <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <List className="w-4 h-4 text-slate-400" />
              <h3 className="font-semibold text-slate-900 dark:text-white">{t("events")}</h3>
            </div>
            <span className="text-xs text-slate-400">{events.length}</span>
          </div>
          <div className="flex-1 p-4 overflow-y-auto space-y-2.5">
            {events.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center text-center py-10">
                <div className="w-12 h-12 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center mb-3 border border-slate-200 dark:border-slate-700">
                  <Activity className="w-5 h-5 text-slate-400" />
                </div>
                <p className="text-sm font-medium text-slate-700 dark:text-slate-300">{t("noEvents")}</p>
                <p className="text-xs text-slate-500 mt-1 max-w-[220px]">{t("awaitingData")}</p>
              </div>
            )}
            {events.map((e, i) => {
              const toneClass = {
                bad:  "bg-red-50 border-red-200 dark:bg-red-500/5 dark:border-red-500/20",
                warn: "bg-amber-50 border-amber-200 dark:bg-amber-500/5 dark:border-amber-500/20",
                info: "bg-blue-50 border-blue-200 dark:bg-blue-500/5 dark:border-blue-500/20",
                ok:   "bg-emerald-50 border-emerald-200 dark:bg-emerald-500/5 dark:border-emerald-500/20",
              }[e.tone] || "bg-slate-50 border-slate-200 dark:bg-slate-800/50 dark:border-slate-700";
              const dotClass = {
                bad:  "bg-red-500",
                warn: "bg-amber-500",
                info: "bg-blue-500",
                ok:   "bg-emerald-500",
              }[e.tone] || "bg-slate-400";
              return (
                <div key={i} className={`p-3 rounded-lg text-sm border ${toneClass}`}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-2 min-w-0">
                      <span className={`mt-1.5 w-2 h-2 rounded-full flex-shrink-0 ${dotClass}`} />
                      <div className="min-w-0">
                        <div className="font-medium text-slate-800 dark:text-slate-100 truncate">{e.title}</div>
                        <div className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">{e.text}</div>
                        {e.zone && (
                          <div className="text-[11px] text-slate-500 dark:text-slate-500 mt-0.5">
                            <span className="font-medium">{e.zone}</span>
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="text-xs text-slate-500 whitespace-nowrap">{e.time}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-800">
          <h3 className="font-semibold text-slate-900 dark:text-white">{t("trends")}</h3>
        </div>
        <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-5">
          <TrendChart sensorType="dp_kp_oo"    label={t("dp_kp_oo")}    color="#f59e0b" />
          <TrendChart sensorType="pressure_kp" label={t("pressure_kp")} color="#60a5fa" />
          <TrendChart sensorType="flow_kp_in"  label={t("flow_kp_in")}  color="#34d399" />
          <TrendChart sensorType="wind_speed"  label={t("wind_speed")}  color="#a78bfa" />
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, icon: Icon, tone, hint }) {
  const ring = {
    ok:      "bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400",
    warn:    "bg-amber-50  text-amber-600  dark:bg-amber-500/10  dark:text-amber-400",
    info:    "bg-blue-50   text-blue-600   dark:bg-blue-500/10   dark:text-blue-400",
    neutral: "bg-slate-100 text-slate-600  dark:bg-slate-800     dark:text-slate-300",
  }[tone || "neutral"];

  const trendColor = {
    ok: "text-emerald-600 dark:text-emerald-400",
    warn: "text-amber-600 dark:text-amber-400",
    info: "text-blue-600 dark:text-blue-400",
    neutral: "text-slate-500 dark:text-slate-400",
  }[tone || "neutral"];

  const TrendIcon = tone === "warn" ? TrendingUp : Minus;

  return (
    <div className="card p-5 hover:shadow-md transition-shadow">
      <div className={`p-2.5 inline-flex rounded-lg ${ring}`}>
        <Icon className="w-5 h-5" />
      </div>
      <p className="text-sm font-medium text-slate-500 dark:text-slate-400 mt-3">{label}</p>
      <h3 className="text-2xl font-bold text-slate-900 dark:text-white mt-1">{value}</h3>
      <div className={`flex items-center gap-1.5 text-xs font-medium mt-3 ${trendColor}`}>
        <TrendIcon className="w-3.5 h-3.5" />
        <span>{hint}</span>
      </div>
    </div>
  );
}

function PredictCard({ data }) {
  const [open, setOpen] = useState(false);
  const { t } = useI18n();
  const { prediction_data: pd, recommendation } = data;

  const STATUS_STYLE = {
    OK:       { bg: "bg-emerald-100 dark:bg-emerald-500/10", text: "text-emerald-700 dark:text-emerald-400", border: "border-emerald-200 dark:border-emerald-500/20" },
    WARNING:  { bg: "bg-amber-100  dark:bg-amber-500/10",   text: "text-amber-700  dark:text-amber-400",   border: "border-amber-200  dark:border-amber-500/20"  },
    CRITICAL: { bg: "bg-red-100    dark:bg-red-500/10",     text: "text-red-700    dark:text-red-400",     border: "border-red-200    dark:border-red-500/20"    },
  };
  const s = STATUS_STYLE[pd.status] || STATUS_STYLE.OK;

  const probs = [
    { key: "OK",       val: pd.probabilities?.OK       ?? 0, color: "bg-emerald-500" },
    { key: "WARNING",  val: pd.probabilities?.WARNING  ?? 0, color: "bg-amber-500"   },
    { key: "CRITICAL", val: pd.probabilities?.CRITICAL ?? 0, color: "bg-red-500"     },
  ];

  return (
    <div className="card overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center gap-2">
        <BrainCircuit className="w-4 h-4 text-slate-400" />
        <h3 className="font-semibold text-slate-900 dark:text-white">{t("stateAssessment")}</h3>
      </div>

      <div className="p-5 grid grid-cols-1 md:grid-cols-3 gap-5 items-start">
        <div className="flex flex-col gap-3">
          <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border font-semibold text-sm w-fit ${s.bg} ${s.text} ${s.border}`}>
            <span className={`w-2 h-2 rounded-full ${s.text.replace("text-", "bg-")}`} />
            {t(`status_${pd.status}`)}
          </div>
          <div>
            <p className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wider">{t("riskIndex")}</p>
            <p className="text-3xl font-bold text-slate-900 dark:text-white mt-0.5">{pd.risk_score}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wider">{t("confidence")}</p>
            <p className="text-xl font-semibold text-slate-700 dark:text-slate-200 mt-0.5">{(pd.confidence * 100).toFixed(2)}%</p>
          </div>
        </div>

        <div className="flex flex-col gap-3">
          <p className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wider">{t("probabilities")}</p>
          {probs.map(({ key, val, color }) => (
            <div key={key}>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="font-medium text-slate-600 dark:text-slate-300">{t(`status_${key}`)}</span>
                <span className="text-slate-500 dark:text-slate-400">{(val * 100).toFixed(2)}%</span>
              </div>
              <div className="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800">
                <div className={`h-full rounded-full ${color}`} style={{ width: `${val * 100}%` }} />
              </div>
            </div>
          ))}
        </div>

        <div className="md:col-span-1">
          <p className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">{t("recommendation")}</p>
          <div className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
            {open
              ? <span className="whitespace-pre-line">{recommendation}</span>
              : <span>{recommendation.split("\n")[0].slice(0, 180)}{recommendation.length > 180 ? "…" : ""}</span>
            }
          </div>
          {recommendation.length > 180 && (
            <button
              onClick={() => setOpen(v => !v)}
              className="mt-2 flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400 hover:underline"
            >
              {open ? <><ChevronUp className="w-3 h-3" /> {t("showLess")}</> : <><ChevronDown className="w-3 h-3" /> {t("showMore")}</>}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// Order matters: more severe events appear first.
const EVENT_RULES = [
  {
    type: "dp_kp_oo",
    test: (v) => v < 0,
    tone: "bad",
    title: "Зворотний перепад КП-ОО",
    fmt: (v, u) => `Δp = ${v.toFixed(2)} ${u} — ризик зворотного потоку повітря`,
  },
  {
    type: "dp_kp_oo",
    test: (v) => v >= 0 && v < 2,
    tone: "warn",
    title: "Низький перепад КП-ОО",
    fmt: (v, u) => `Δp = ${v.toFixed(2)} ${u} — менше резерву безпеки 2 ${u}`,
  },
  {
    type: "wind_speed",
    test: (v) => v > 8,
    tone: "warn",
    title: "Сильний вітер",
    fmt: (v) => `${v.toFixed(1)} м/с — можливий вплив на герметичність`,
  },
  {
    type: "pressure_kp",
    test: (v) => v < -50 || v > 15,
    tone: "warn",
    title: "Тиск КП поза робочим діапазоном",
    fmt: (v, u) => `${v.toFixed(1)} ${u} (норма −50…15 ${u})`,
  },
  {
    type: "pressure_oo",
    test: (v) => v < -60 || v > 15,
    tone: "warn",
    title: "Тиск ОО поза робочим діапазоном",
    fmt: (v, u) => `${v.toFixed(1)} ${u} (норма −60…15 ${u})`,
  },
  {
    type: "gu_pressure_west_wall",
    test: (v) => Math.abs(v) > 40,
    tone: "warn",
    title: "Перевищено тиск на західній стінці ГУ",
    fmt: (v, u) => `${v.toFixed(1)} ${u}`,
  },
  {
    type: "gu_pressure_east_wall",
    test: (v) => Math.abs(v) > 40,
    tone: "warn",
    title: "Перевищено тиск на східній стінці ГУ",
    fmt: (v, u) => `${v.toFixed(1)} ${u}`,
  },
  {
    type: "gu_pressure_cyl_wall",
    test: (v) => Math.abs(v) > 40,
    tone: "warn",
    title: "Перевищено тиск на циліндричній стінці ГУ",
    fmt: (v, u) => `${v.toFixed(1)} ${u}`,
  },
  {
    type: "flow_kp_in",
    test: (v) => v < 8,
    tone: "warn",
    title: "Низька витрата припливу КП+",
    fmt: (v) => `${v.toFixed(2)} тис. м³/год — нижче робочого мінімуму`,
  },
  {
    type: "flow_oo_out",
    test: (v) => v < 12,
    tone: "warn",
    title: "Низька витяжка ОО−",
    fmt: (v) => `${v.toFixed(2)} тис. м³/год — нижче робочого мінімуму`,
  },
];

function buildEvents(latest, t) {
  const fmtTime = (iso) => {
    if (!iso) return "";
    const d = new Date(iso);
    return d.toLocaleTimeString("uk-UA", { hour: "2-digit", minute: "2-digit" });
  };

  // Index latest by type so a single iteration of rules is enough
  const byType = Object.fromEntries(latest.map((r) => [r.sensor_type, r]));

  const out = [];
  for (const rule of EVENT_RULES) {
    const r = byType[rule.type];
    if (!r || typeof r.value !== "number") continue;
    if (!rule.test(r.value)) continue;
    out.push({
      tone: rule.tone,
      title: rule.title,
      text: rule.fmt(r.value, r.unit || ""),
      zone: r.zone_name || r.zone_code,
      time: fmtTime(r.measured_at),
    });
  }

  // Always lead with a positive heartbeat when nothing alarming is happening,
  // so the panel never looks "empty / broken".
  if (out.length === 0 && latest.length) {
    const dp = byType.dp_kp_oo;
    const wind = byType.wind_speed;
    if (dp && typeof dp.value === "number") {
      out.push({
        tone: "ok",
        title: "Система у нормі",
        text: `Перепад КП-ОО ${dp.value.toFixed(2)} ${dp.unit || "Па"} — у безпечному діапазоні`,
        zone: dp.zone_name || dp.zone_code,
        time: fmtTime(dp.measured_at),
      });
    }
    if (wind && typeof wind.value === "number") {
      out.push({
        tone: "info",
        title: "Метеоумови",
        text: `Вітер ${wind.value.toFixed(1)} м/с, напрям ${(byType.wind_direction?.value ?? 0).toFixed(0)}°`,
        zone: wind.zone_name || wind.zone_code,
        time: fmtTime(wind.measured_at),
      });
    }
  }

  return out.slice(0, 6);
}
