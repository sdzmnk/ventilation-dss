import { useEffect, useState } from "react";
import {
  Sliders,
  Play,
  Loader2,
  Wind,
  Gauge,
  AlertOctagon,
  Activity,
  Zap,
  CircleDollarSign,
  ShieldCheck,
} from "lucide-react";
import { api } from "../api/client.js";
import { useI18n } from "../i18n/i18n.jsx";

const DEFAULT = {
  method: "scipy",
  fan_power_kw: 15,
  energy_cost_kwh: 0.12,
  pressure_kp_target: -10,
  pressure_oo_target: -17,
  dp_kp_oo_min: 2,
  flow_kp_min: 10,
  flow_kp_max: 28,
  flow_oo_min: 15,
  flow_oo_max: 40,
  filter_efficiency: 0.999,
  current_wind_speed: 2.0,
};

export default function OptimizationPage() {
  const { t } = useI18n();
  const [form, setForm] = useState(DEFAULT);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === "number" ? Number(e.target.value) : e.target.value });

  const loadHistory = async () => {
    try { const { data } = await api.get("/analytic/runs", { params: { limit: 15 } }); setHistory(data || []); }
    catch { /* ignore */ }
  };
  useEffect(() => { loadHistory(); }, []);

  const run = async () => {
    setErr(""); setBusy(true);
    try { const { data } = await api.post("/analytic/optimize", form); setResult(data); loadHistory(); }
    catch (e) { setErr(e?.response?.data?.detail || String(e)); }
    finally { setBusy(false); }
  };

  const num = (v, d = 2) => (typeof v === "number" ? v.toFixed(d) : "—");

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      {err && <div className="badge badge-bad px-3 py-2">{err}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 card">
          <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center gap-2">
            <Sliders className="w-4 h-4 text-slate-400" />
            <h3 className="font-semibold text-slate-900 dark:text-white">{t("inputs")}</h3>
          </div>
          <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label={t("method")}>
              <select className="input" value={form.method} onChange={set("method")}>
                <option value="scipy">SciPy (L-BFGS-B)</option>
                <option value="grid">Grid search</option>
              </select>
            </Field>
            <Num label="Цільовий тиск КП (Па)"   value={form.pressure_kp_target} step="1" onChange={set("pressure_kp_target")} />
            <Num label="Цільовий тиск ОО (Па)"   value={form.pressure_oo_target} step="1" onChange={set("pressure_oo_target")} />
            <Num label="Мін. перепад КП-ОО (Па)" value={form.dp_kp_oo_min} step="0.5" onChange={set("dp_kp_oo_min")} />
            <Num label="Швидкість вітру (м/с)"   value={form.current_wind_speed} step="0.1" onChange={set("current_wind_speed")} />
            <Num label="Мін. витрата КП+ (тис. м³/год)" value={form.flow_kp_min} step="0.5" onChange={set("flow_kp_min")} />
            <Num label="Макс. витрата КП+ (тис. м³/год)" value={form.flow_kp_max} step="0.5" onChange={set("flow_kp_max")} />
            <Num label="Мін. витрата ОО− (тис. м³/год)" value={form.flow_oo_min} step="0.5" onChange={set("flow_oo_min")} />
            <Num label="Макс. витрата ОО− (тис. м³/год)" value={form.flow_oo_max} step="0.5" onChange={set("flow_oo_max")} />
            <Num label="Потужність вентилятора (кВт)" value={form.fan_power_kw} step="0.1" onChange={set("fan_power_kw")} />
            <Num label="Вартість 1 кВт·год" value={form.energy_cost_kwh} step="0.01" onChange={set("energy_cost_kwh")} />
            <Num label="Ефективність HEPA фільтру" value={form.filter_efficiency} step="0.001" onChange={set("filter_efficiency")} />
          </div>
          <div className="px-5 pb-5">
            <button className="btn" onClick={run} disabled={busy}>
              {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              {t("runOptimization")}
            </button>
          </div>
        </div>

        <div className="card flex flex-col">
          <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-800">
            <h3 className="font-semibold text-slate-900 dark:text-white">{t("result")}</h3>
          </div>
          <div className="p-5 grid grid-cols-2 gap-3 flex-1">
            <Kpi icon={Wind} label={t("optimalFlowKp")} value={result ? num(result.optimal_flow_kp, 2) : "—"} unit="тис. м³/год" />
            <Kpi icon={Wind} label={t("optimalFlowOo")} value={result ? num(result.optimal_flow_oo, 2) : "—"} unit="тис. м³/год" />
            <Kpi icon={Gauge} label={t("optimalLoad")} value={result ? `${(result.optimal_fan_load * 100).toFixed(0)}%` : "—"} />
            <Kpi icon={AlertOctagon} label={t("expectedDpKpOo")} value={result ? num(result.expected_dp_kp_oo) : "—"} unit="Па" />
            <Kpi icon={Activity} label={t("expectedPressureKp")} value={result ? num(result.expected_pressure_kp) : "—"} unit="Па" />
            <Kpi icon={Activity} label={t("expectedPressureOo")} value={result ? num(result.expected_pressure_oo) : "—"} unit="Па" />
            <Kpi icon={Zap} label={t("energyKw")} value={result ? num(result.energy_kw) : "—"} unit="кВт" />
            <Kpi icon={CircleDollarSign} label={t("costPerHour")} value={result ? num(result.energy_cost_per_hour, 2) : "—"} />
            <Kpi icon={ShieldCheck} label={t("safetyMargin")} value={result ? num(result.safety_margin) : "—"} unit="Па" />
            <Kpi icon={Sliders} label={t("iterations")} value={result ? result.iterations : "—"} />
          </div>
        </div>
      </div>

      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-800">
          <h3 className="font-semibold text-slate-900 dark:text-white">{t("history")}</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                <th className="px-5 py-3">#</th>
                <th className="px-5 py-3">{t("method")}</th>
                <th className="px-5 py-3">{t("optimalFlowKp")}</th>
                <th className="px-5 py-3">{t("expectedDpKpOo")}</th>
                <th className="px-5 py-3">{t("costPerHour")}</th>
                <th className="px-5 py-3">{t("measuredAt")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {history.map((h) => (
                <tr key={h.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                  <td className="px-5 py-3 text-slate-500">{h.id}</td>
                  <td className="px-5 py-3"><span className="badge badge-mute">{h.method}</span></td>
                  <td className="px-5 py-3">{num(h.result?.optimal_flow_kp, 2)} тис. м³/год</td>
                  <td className="px-5 py-3">{num(h.result?.expected_dp_kp_oo)}</td>
                  <td className="px-5 py-3">{num(h.result?.energy_cost_per_hour)}</td>
                  <td className="px-5 py-3 text-slate-500">{h.created_at && new Date(h.created_at).toLocaleString()}</td>
                </tr>
              ))}
              {history.length === 0 && (
                <tr><td colSpan={6} className="px-5 py-8 text-center text-slate-400">—</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }) {
  return <div><label className="label">{label}</label>{children}</div>;
}
function Num({ label, value, step = "1", onChange }) {
  return (
    <Field label={label}>
      <input type="number" step={step} className="input" value={value} onChange={onChange} />
    </Field>
  );
}
function Kpi({ icon: Icon, label, value, unit }) {
  return (
    <div className="rounded-lg border border-slate-100 dark:border-slate-800 p-3 bg-slate-50 dark:bg-slate-800/40">
      <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400">
        <Icon className="w-4 h-4" />
        <span className="text-xs font-medium">{label}</span>
      </div>
      <div className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">
        {value} {unit && <span className="text-xs font-medium text-slate-400">{unit}</span>}
      </div>
    </div>
  );
}
