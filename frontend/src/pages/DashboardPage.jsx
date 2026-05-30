import { useEffect, useRef, useState } from "react";
import {
  Activity,
  ShieldCheck,
  AlertOctagon,
  Wind,
  Gauge,
  TrendingUp,
  Minus,
  BrainCircuit,
  ChevronDown,
  ChevronUp,
  Compass,
} from "lucide-react";
import { api } from "../api/client.js";
import { useI18n } from "../i18n/i18n.jsx";
import VentilationScheme from "../components/VentilationScheme.jsx";
import TrendChart from "../components/TrendChart.jsx";

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

const STATS_REFRESH_MS   = 10_000;
const PREDICT_REFRESH_MS = 18_000_000;

export default function DashboardPage() {
  const { t } = useI18n();
  const [stats, setStats] = useState([]);
  const [prediction, setPrediction] = useState(null);
  const statsRef = useRef([]);

  const refresh = async () => {
    try {
      const { data } = await api.get("/analytic/stats", { params: { hours: 24 } });
      const s = data || [];
      setStats(s);
      statsRef.current = s;
      return s;
    } catch { return null; }
  };

  const refreshPredict = async (currentStats) => {
    try {
      const src = currentStats ?? statsRef.current;
      const byT = Object.fromEntries(src.map((s) => [s.sensor_type, s]));
      const params = {};
      for (const k of PREDICT_CHANNELS) {
        if (byT[k]) params[k] = byT[k].mean;
      }
      const r = await api.get("/analytic/predict", { params });
      setPrediction(r.data);
    } catch {  }
  };

  useEffect(() => {
    refresh().then((s) => { if (s) refreshPredict(s); });
    const statsTimer = setInterval(refresh, STATS_REFRESH_MS);
    const predictTimer = setInterval(() => {
      if (statsRef.current.length) refreshPredict(statsRef.current);
    }, PREDICT_REFRESH_MS);
    return () => {
      clearInterval(statsTimer);
      clearInterval(predictTimer);
    };
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
        ? `${t("minLabel")} ${byType.dp_kp_oo.min.toFixed(1)} · ${t("maxLabel")} ${byType.dp_kp_oo.max.toFixed(1)}`
        : t("liveData"),
    },
    {
      label: t("pressure_kp"),
      value: byType.pressure_kp ? `${byType.pressure_kp.mean.toFixed(1)} Па` : "—",
      icon: Gauge,
      tone: byType.pressure_kp && Math.abs(byType.pressure_kp.mean) > 50 ? "warn" : "info",
      hint: byType.pressure_kp ? `${t("countLabel")}=${byType.pressure_kp.count}` : t("liveData"),
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
      hint: byType.wind_speed ? `${t("maxLabel")} ${byType.wind_speed.max.toFixed(1)}` : "",
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
      hint: byType.pressure_oo ? `${t("minLabel")} ${byType.pressure_oo.min.toFixed(1)}` : "",
    },
    {
      label: t("flow_oo_out"),
      value: byType.flow_oo_out ? `${byType.flow_oo_out.mean.toFixed(1)} тис. м³/год` : "—",
      icon: Wind,
      tone: "info",
      hint: "",
    },
  ];


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

      <div className="card overflow-hidden flex flex-col min-h-[420px]">
        <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-800">
          <h3 className="font-semibold text-slate-900 dark:text-white">{t("scheme")}</h3>
        </div>
        <div className="flex-1 bg-slate-50 dark:bg-[#0b1120]">
          <VentilationScheme stats={stats} />
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
          <p className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3">{t("recommendation")}</p>
          <RecommendationView text={recommendation} open={open} setOpen={setOpen} t={t} />
        </div>
      </div>
    </div>
  );
}

const stripMarkdown = (s) =>
  s
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/__(.+?)__/g, "$1")
    .replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, "$1")
    .replace(/`(.+?)`/g, "$1")
    .trim();

function finalizeSection(lines) {
  if (!lines || !lines.length) return null;
  const items = [];
  let para = [];
  for (const l of lines) {
    const li = l.match(/^\s*(?:\d+\s*[.):]|[-•*–—])\s+(.+)$/);
    if (li) {
      if (para.length) { items.push(para.join(" ").trim()); para = []; }
      items.push(li[1].trim());
    } else {
      para.push(l);
    }
  }
  if (para.length) items.push(para.join(" ").trim());
  const cleaned = items.map((s) => s.replace(/\s+/g, " ").trim()).filter(Boolean);
  if (!cleaned.length) return null;
  return cleaned.length === 1 ? cleaned[0] : cleaned;
}

function parseRecommendation(text) {
  if (!text) return null;
  const raw = { state: [], cause: [], action: [] };
  let current = null;

  for (const original of text.split(/\r?\n/)) {
    const line = stripMarkdown(original);
    if (!line) continue;
    const m = line.match(/^(Стан системи|Стан|Причина|Дія|Рекомендовано|Рекомендац\S*)\s*[:\-—]\s*(.*)$/i);
    if (m) {
      const label = m[1].toLowerCase();
      if (label.startsWith("причин")) current = "cause";
      else if (label.startsWith("стан")) current = "state";
      else current = "action";
      if (m[2]) raw[current].push(m[2]);
    } else if (current) {
      raw[current].push(line);
    }
  }

  const out = {
    state: finalizeSection(raw.state),
    cause: finalizeSection(raw.cause),
    action: finalizeSection(raw.action),
  };
  return out.state || out.cause || out.action ? out : null;
}

function RecSection({ icon: Icon, label, text, tone }) {
  const toneClass = {
    state:  "bg-blue-50 text-blue-600 dark:bg-blue-500/10 dark:text-blue-400",
    cause:  "bg-amber-50 text-amber-600 dark:bg-amber-500/10 dark:text-amber-400",
    action: "bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400",
  }[tone] || "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400";
  return (
    <div className="flex items-start gap-2.5">
      <div className={`p-1.5 rounded-md flex-shrink-0 ${toneClass}`}>
        <Icon className="w-3.5 h-3.5" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400 font-semibold mb-1">{label}</p>
        {Array.isArray(text) ? (
          <ol className="list-decimal list-outside ml-4 space-y-1 text-sm text-slate-700 dark:text-slate-300 leading-relaxed marker:text-slate-400">
            {text.map((it, i) => <li key={i}>{it}</li>)}
          </ol>
        ) : (
          <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">{text}</p>
        )}
      </div>
    </div>
  );
}

function RecommendationView({ text, open, setOpen, t }) {
  const sections = parseRecommendation(text);
  if (sections) {
    return (
      <div className="space-y-3">
        {sections.state  && <RecSection icon={Activity}     label="Стан"    text={sections.state}  tone="state"  />}
        {sections.cause  && <RecSection icon={AlertOctagon} label="Причина" text={sections.cause}  tone="cause"  />}
        {sections.action && <RecSection icon={ShieldCheck}  label="Дія"     text={sections.action} tone="action" />}
      </div>
    );
  }
  const safe = text || "";
  const firstLine = safe.split("\n")[0] || "";
  const truncated = firstLine.length > 180 ? firstLine.slice(0, 180) + "…" : firstLine;
  return (
    <>
      <div className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
        {open ? <span className="whitespace-pre-line">{safe}</span> : <span>{truncated}</span>}
      </div>
      {safe.length > 180 && (
        <button
          onClick={() => setOpen((v) => !v)}
          className="mt-2 flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400 hover:underline"
        >
          {open ? <><ChevronUp className="w-3 h-3" /> {t("showLess")}</> : <><ChevronDown className="w-3 h-3" /> {t("showMore")}</>}
        </button>
      )}
    </>
  );
}

