import { useEffect, useState } from "react";
import { Save, RotateCcw } from "lucide-react";
import { api } from "../api/client.js";
import { useI18n } from "../i18n/i18n.jsx";
import { useAuth } from "../api/auth.jsx";

// Keys mirror configuration.parameters seeded in db/init.sql
const FRIENDLY_LABELS = {
  pressure_kp_min_pa:    "Мін. тиск КП",
  pressure_kp_max_pa:    "Макс. тиск КП",
  pressure_oo_min_pa:    "Мін. тиск ОО",
  pressure_oo_max_pa:    "Макс. тиск ОО",
  dp_kp_oo_min_pa:       "Мін. перепад КП-ОО",
  dp_kp_oo_max_pa:       "Макс. перепад КП-ОО",
  flow_kp_min_km3h:      "Мін. витрата КП+",
  flow_kp_max_km3h:      "Макс. витрата КП+",
  flow_oo_min_km3h:      "Мін. витрата ОО−",
  flow_oo_max_km3h:      "Макс. витрата ОО−",
  wind_speed_alarm_ms:   "Поріг швидкості вітру",
  gu_pressure_alarm_pa:  "Поріг тиску ГУ на стінках",
  energy_cost_kwh:       "Вартість 1 кВт·год",
  fan_power_kw:          "Потужність вентилятора",
  filter_efficiency:     "Ефективність HEPA фільтру",
};
const UNITS = {
  pressure_kp_min_pa:    "Па",
  pressure_kp_max_pa:    "Па",
  pressure_oo_min_pa:    "Па",
  pressure_oo_max_pa:    "Па",
  dp_kp_oo_min_pa:       "Па",
  dp_kp_oo_max_pa:       "Па",
  flow_kp_min_km3h:      "тис. м³/год",
  flow_kp_max_km3h:      "тис. м³/год",
  flow_oo_min_km3h:      "тис. м³/год",
  flow_oo_max_km3h:      "тис. м³/год",
  wind_speed_alarm_ms:   "м/с",
  gu_pressure_alarm_pa:  "Па",
  energy_cost_kwh:       "за кВт·год",
  fan_power_kw:          "кВт",
  filter_efficiency:     "0–1",
};

export default function ConfigPage() {
  const { t } = useI18n();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [items, setItems] = useState([]);
  const [draft, setDraft] = useState({});
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  const load = async () => {
    setErr("");
    try {
      const { data } = await api.get("/config");
      setItems(data || []);
      const d = {};
      for (const it of data || []) {
        const v = it.value;
        d[it.key] = typeof v === "string" ? v : JSON.stringify(v);
      }
      setDraft(d);
    } catch (e) { setErr(e?.response?.data?.detail || String(e)); }
  };
  useEffect(() => { load(); }, []);

  const save = async (it) => {
    setMsg(""); setErr("");
    let value;
    try { value = JSON.parse(draft[it.key]); } catch { value = draft[it.key]; }
    try {
      await api.put(`/config/${encodeURIComponent(it.key)}`, { key: it.key, value, description: it.description });
      setMsg(`${t("saved")}: ${friendly(it.key)}`);
      load();
    } catch (e) { setErr(e?.response?.data?.detail || String(e)); }
  };

  const reset = (it) => {
    const v = it.value;
    setDraft((d) => ({ ...d, [it.key]: typeof v === "string" ? v : JSON.stringify(v) }));
  };

  const friendly = (key) => FRIENDLY_LABELS[key] || key;

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 max-w-5xl mx-auto">
      {err && <div className="badge badge-bad px-3 py-2">{err}</div>}
      {msg && <div className="badge badge-ok px-3 py-2">{msg}</div>}

      <div className="card">
        <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-800">
          <h3 className="font-semibold text-slate-900 dark:text-white">{t("config")}</h3>
          <p className="text-xs text-slate-500 mt-1">
            {isAdmin
              ? "Налаштовуйте граничні значення та параметри роботи системи."
              : "Поточні параметри системи (доступ адміністратора для редагування)."}
          </p>
        </div>
        <div className="divide-y divide-slate-100 dark:divide-slate-800">
          {items.map((it) => (
            <div key={it.key} className="px-5 py-4 flex flex-col md:flex-row md:items-center gap-4">
              <div className="md:w-1/2">
                <div className="text-sm font-medium text-slate-900 dark:text-white">{friendly(it.key)}</div>
                <div className="text-xs text-slate-500 mt-0.5">{it.description || it.key}</div>
              </div>
              <div className="flex-1 flex items-center gap-2">
                <input
                  className="input"
                  value={draft[it.key] ?? ""}
                  disabled={!isAdmin}
                  onChange={(e) => setDraft({ ...draft, [it.key]: e.target.value })}
                />
                <span className="text-xs text-slate-400 whitespace-nowrap">{UNITS[it.key] || ""}</span>
              </div>
              {isAdmin && (
                <div className="flex items-center gap-2">
                  <button className="btn-secondary" onClick={() => reset(it)} title={t("reset")}>
                    <RotateCcw className="w-4 h-4" />
                  </button>
                  <button className="btn" onClick={() => save(it)}>
                    <Save className="w-4 h-4" /> {t("save")}
                  </button>
                </div>
              )}
            </div>
          ))}
          {items.length === 0 && (
            <div className="px-5 py-8 text-center text-slate-400 text-sm">—</div>
          )}
        </div>
      </div>
    </div>
  );
}
