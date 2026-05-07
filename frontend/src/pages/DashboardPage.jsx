import { useEffect, useState } from "react";
import {
  Activity,
  ShieldCheck,
  AlertOctagon,
  Wind,
  Thermometer,
  TrendingUp,
  Minus,
  List,
  BrainCircuit,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { api } from "../api/client.js";
import { useI18n } from "../i18n/i18n.jsx";
import VentilationScheme from "../components/VentilationScheme.jsx";
import TrendChart from "../components/TrendChart.jsx";

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
      if (byT.radiation)   params.radiation   = byT.radiation.mean;
      if (byT.pressure)    params.pressure    = byT.pressure.mean;
      if (byT.airflow)     params.airflow     = byT.airflow.mean;
      if (byT.temperature) params.temperature = byT.temperature.mean;
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
  const radMax = byType.radiation?.max ?? 0;
  const overall = radMax > 18 ? "warn" : "ok";

  const cards = [
    {
      label: t("systemStatus"),
      value: overall === "warn" ? t("warning") : t("optimal"),
      icon: ShieldCheck,
      tone: overall === "warn" ? "warn" : "ok",
      hint: t("updatedNow"),
    },
    {
      label: t("radiation"),
      value: byType.radiation ? `${byType.radiation.mean.toFixed(1)} мкЗв/год` : "—",
      icon: AlertOctagon,
      tone: byType.radiation && byType.radiation.mean > 12 ? "warn" : "ok",
      hint: byType.radiation ? `max ${byType.radiation.max.toFixed(1)} · n=${byType.radiation.count}` : t("liveData"),
    },
    {
      label: t("airflow"),
      value: byType.airflow ? `${(byType.airflow.mean / 1000).toFixed(1)} тис. м³/год` : "—",
      icon: Wind,
      tone: "info",
      hint: t("liveData"),
    },
    {
      label: t("temperature"),
      value: byType.temperature ? `${byType.temperature.mean.toFixed(1)} °C` : "—",
      icon: Thermometer,
      tone: "neutral",
      hint: t("liveData"),
    },
  ];

  const events = buildEvents(latest);

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
          <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center gap-2">
            <List className="w-4 h-4 text-slate-400" />
            <h3 className="font-semibold text-slate-900 dark:text-white">{t("events")}</h3>
          </div>
          <div className="flex-1 p-4 overflow-y-auto space-y-2">
            {events.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center text-center py-10">
                <div className="w-12 h-12 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center mb-3 border border-slate-200 dark:border-slate-700">
                  <Activity className="w-5 h-5 text-slate-400" />
                </div>
                <p className="text-sm font-medium text-slate-700 dark:text-slate-300">{t("noEvents")}</p>
                <p className="text-xs text-slate-500 mt-1 max-w-[220px]">{t("awaitingData")}</p>
              </div>
            )}
            {events.map((e, i) => (
              <div key={i} className={`p-3 rounded-lg text-sm border ${
                e.tone === "warn"
                  ? "bg-amber-50 border-amber-200 dark:bg-amber-500/5 dark:border-amber-500/20"
                  : "bg-slate-50 border-slate-200 dark:bg-slate-800/50 dark:border-slate-700"
              }`}>
                <div className="flex items-center justify-between">
                  <div className="font-medium text-slate-800 dark:text-slate-100">{e.title}</div>
                  <div className="text-xs text-slate-500">{e.time}</div>
                </div>
                <div className="text-xs text-slate-500 mt-1">{e.text}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-800">
          <h3 className="font-semibold text-slate-900 dark:text-white">{t("trends")}</h3>
        </div>
        <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-5">
          <TrendChart sensorType="radiation" label={t("radiation")} color="#f59e0b" />
          <TrendChart sensorType="pressure" label={t("pressure")} color="#60a5fa" />
          <TrendChart sensorType="airflow" label={t("airflow")} color="#34d399" />
          <TrendChart sensorType="temperature" label={t("temperature")} color="#f472b6" />
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
        {/* Status + Risk */}
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

        {/* Probabilities */}
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

        {/* Recommendation */}
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

function buildEvents(latest) {
  const out = [];
  for (const r of latest) {
    if (r.sensor_type === "radiation" && typeof r.value === "number" && r.value > 16) {
      out.push({
        tone: "warn",
        title: `Підвищена радіація · ${r.zone_name || r.zone_code}`,
        text: `${r.sensor_code}: ${r.value.toFixed(1)} ${r.unit}`,
        time: new Date(r.measured_at).toLocaleTimeString(),
      });
    }
  }
  if (latest.length && out.length === 0) {
    const r = latest[0];
    out.push({
      tone: "info",
      title: "Оновлення сенсорів",
      text: `${r.zone_name || r.zone_code} · ${r.sensor_code}: ${
        typeof r.value === "number" ? r.value.toFixed(1) : "—"
      } ${r.unit || ""}`,
      time: r.measured_at ? new Date(r.measured_at).toLocaleTimeString() : "",
    });
  }
  return out.slice(0, 8);
}
