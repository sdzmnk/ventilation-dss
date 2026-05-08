import { Fragment, useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronRight, Pencil, Plus, Save, Trash2, X } from "lucide-react";
import { api } from "../api/client.js";
import { useI18n } from "../i18n/i18n.jsx";
import { useAuth } from "../api/auth.jsx";

// All sensor types known to the system, derived from the 2020-2024 dataset.
const SENSOR_TYPES = [
  "wind_speed", "wind_direction", "air_density",
  "pressure_kp", "pressure_oo",
  "flow_kp_in", "flow_oo_out", "flow_oo_in",
  "dp_kp_os", "dp_oo_os_8", "dp_oo_os_9",
  "dp_kp_oo", "dp_kp_oo_by", "dp_kp_oo_bz", "dp_kp_oo_ca",
  "gu_pressure_west_wall", "gu_pressure_east_wall", "gu_pressure_cyl_wall",
  "gu_pressure_west_gap", "gu_pressure_east_gap", "gu_pressure_vsro",
  "gu_sigma_008", "gu_sigma_009", "gu_sigma_kp_os",
];

export default function SensorsPage() {
  const { t } = useI18n();
  const { user } = useAuth();
  const canEdit = user?.role === "admin" || user?.role === "engineer";
  const isAdmin = user?.role === "admin";

  const [zones, setZones] = useState([]);
  const [sensors, setSensors] = useState([]);
  const [latest, setLatest] = useState([]);
  const [zoneForm, setZoneForm] = useState({ code: "", name: "", description: "" });
  const [sensorForm, setSensorForm] = useState({ zone_id: "", code: "", sensor_type: "pressure_kp", unit: "Па" });
  const [editZone, setEditZone] = useState(null);   // {id, code, name, description}
  const [editSensor, setEditSensor] = useState(null); // {id, zone_id, code, sensor_type, unit}
  const [expanded, setExpanded] = useState(null);   // sensor_id
  const [history, setHistory] = useState({});       // { [sensorId]: [{value, measured_at}] }
  const [err, setErr] = useState("");

  const load = async () => {
    setErr("");
    try {
      const [z, s, l] = await Promise.all([
        api.get("/zones"),
        api.get("/sensors"),
        api.get("/readings/latest"),
      ]);
      setZones(z.data || []);
      setSensors(s.data || []);
      setLatest(l.data || []);
    } catch (e) { setErr(e?.response?.data?.detail || String(e)); }
  };
  useEffect(() => {
    load();
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, []);

  const latestBySensor = useMemo(() => {
    const m = {};
    for (const r of latest) m[r.sensor_id] = r;
    return m;
  }, [latest]);

  // ---- zones ----
  const addZone = async () => {
    if (!zoneForm.code || !zoneForm.name) return;
    try { await api.post("/zones", zoneForm); setZoneForm({ code: "", name: "", description: "" }); load(); }
    catch (e) { setErr(e?.response?.data?.detail || String(e)); }
  };
  const saveZone = async () => {
    if (!editZone) return;
    try {
      await api.put(`/zones/${editZone.id}`, {
        code: editZone.code, name: editZone.name, description: editZone.description || null,
      });
      setEditZone(null);
      load();
    } catch (e) { setErr(e?.response?.data?.detail || String(e)); }
  };
  const delZone = async (id) => {
    try { await api.delete(`/zones/${id}`); load(); }
    catch (e) { setErr(e?.response?.data?.detail || String(e)); }
  };

  // ---- sensors ----
  const addSensor = async () => {
    if (!sensorForm.code || !sensorForm.unit) return;
    try {
      await api.post("/sensors", { ...sensorForm, zone_id: sensorForm.zone_id ? Number(sensorForm.zone_id) : null });
      setSensorForm({ zone_id: "", code: "", sensor_type: "pressure_kp", unit: "Па" });
      load();
    } catch (e) { setErr(e?.response?.data?.detail || String(e)); }
  };
  const saveSensor = async () => {
    if (!editSensor) return;
    try {
      await api.put(`/sensors/${editSensor.id}`, {
        zone_id: editSensor.zone_id ? Number(editSensor.zone_id) : null,
        code: editSensor.code,
        sensor_type: editSensor.sensor_type,
        unit: editSensor.unit,
      });
      setEditSensor(null);
      load();
    } catch (e) { setErr(e?.response?.data?.detail || String(e)); }
  };
  const delSensor = async (id) => {
    try { await api.delete(`/sensors/${id}`); load(); }
    catch (e) { setErr(e?.response?.data?.detail || String(e)); }
  };

  const toggleHistory = async (sensorId) => {
    if (expanded === sensorId) { setExpanded(null); return; }
    setExpanded(sensorId);
    if (!history[sensorId]) {
      try {
        const { data } = await api.get(`/readings?sensor_id=${sensorId}&hours=24&limit=288`);
        setHistory((h) => ({ ...h, [sensorId]: data || [] }));
      } catch (e) { setErr(e?.response?.data?.detail || String(e)); }
    }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      {err && <div className="badge badge-bad px-3 py-2">{err}</div>}

      {/* ============ ZONES ============ */}
      <SectionCard title={t("zones")}>
        {canEdit && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-4">
            <div><label className="label">{t("code")}</label><input className="input" value={zoneForm.code} onChange={(e) => setZoneForm({ ...zoneForm, code: e.target.value })} /></div>
            <div><label className="label">{t("name")}</label><input className="input" value={zoneForm.name} onChange={(e) => setZoneForm({ ...zoneForm, name: e.target.value })} /></div>
            <div><label className="label">{t("description")}</label><input className="input" value={zoneForm.description} onChange={(e) => setZoneForm({ ...zoneForm, description: e.target.value })} /></div>
            <div className="flex items-end"><button className="btn w-full" onClick={addZone}><Plus className="w-4 h-4" />{t("add")}</button></div>
          </div>
        )}
        <DataTable headers={["#", t("code"), t("zone"), t("description"), ""]}>
          {zones.map((z) => {
            const isEditing = editZone?.id === z.id;
            return (
              <tr key={z.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                <Td>{z.id}</Td>
                <Td>{isEditing
                  ? <input className="input py-1" value={editZone.code} onChange={(e) => setEditZone({ ...editZone, code: e.target.value })} />
                  : <code>{z.code}</code>}</Td>
                <Td>{isEditing
                  ? <input className="input py-1" value={editZone.name} onChange={(e) => setEditZone({ ...editZone, name: e.target.value })} />
                  : z.name}</Td>
                <Td>{isEditing
                  ? <input className="input py-1" value={editZone.description || ""} onChange={(e) => setEditZone({ ...editZone, description: e.target.value })} />
                  : (z.description || "—")}</Td>
                <Td>
                  <div className="flex gap-1.5 justify-end">
                    {isEditing ? (
                      <>
                        <button className="btn px-2.5 py-1.5" onClick={saveZone} title={t("save")}><Save className="w-3.5 h-3.5" /></button>
                        <button className="btn-ghost px-2.5 py-1.5" onClick={() => setEditZone(null)} title={t("cancel")}><X className="w-3.5 h-3.5" /></button>
                      </>
                    ) : (
                      <>
                        {canEdit && <button className="btn-ghost px-2.5 py-1.5" onClick={() => setEditZone({ ...z })} title={t("edit")}><Pencil className="w-3.5 h-3.5" /></button>}
                        {isAdmin && <button className="btn-danger px-2.5 py-1.5" onClick={() => delZone(z.id)} title={t("delete")}><Trash2 className="w-3.5 h-3.5" /></button>}
                      </>
                    )}
                  </div>
                </Td>
              </tr>
            );
          })}
        </DataTable>
      </SectionCard>

      {/* ============ SENSORS ============ */}
      <SectionCard title={t("sensors")}>
        {canEdit && (
          <div className="grid grid-cols-1 md:grid-cols-5 gap-3 mb-4">
            <div><label className="label">{t("zone")}</label>
              <select className="input" value={sensorForm.zone_id} onChange={(e) => setSensorForm({ ...sensorForm, zone_id: e.target.value })}>
                <option value="">—</option>
                {zones.map((z) => <option key={z.id} value={z.id}>{z.code} · {z.name}</option>)}
              </select>
            </div>
            <div><label className="label">{t("code")}</label><input className="input" value={sensorForm.code} onChange={(e) => setSensorForm({ ...sensorForm, code: e.target.value })} /></div>
            <div><label className="label">{t("type")}</label>
              <select className="input" value={sensorForm.sensor_type} onChange={(e) => setSensorForm({ ...sensorForm, sensor_type: e.target.value })}>
                {SENSOR_TYPES.map((s) => <option key={s} value={s}>{t(s)}</option>)}
              </select>
            </div>
            <div><label className="label">{t("unit")}</label><input className="input" value={sensorForm.unit} onChange={(e) => setSensorForm({ ...sensorForm, unit: e.target.value })} /></div>
            <div className="flex items-end"><button className="btn w-full" onClick={addSensor}><Plus className="w-4 h-4" />{t("add")}</button></div>
          </div>
        )}

        <DataTable headers={["", "#", t("zone"), t("code"), t("type"), t("unit"), t("lastValue"), t("lastSeen"), ""]}>
          {sensors.map((s) => {
            const isEditing = editSensor?.id === s.id;
            const isOpen = expanded === s.id;
            const last = latestBySensor[s.id];
            const zoneCode = zones.find((z) => z.id === s.zone_id)?.code;
            return (
              <Fragment key={s.id}>
                <tr className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                  <Td>
                    <button className="btn-ghost px-1.5 py-1" onClick={() => toggleHistory(s.id)} title={isOpen ? t("hideHistory") : t("showHistory")}>
                      {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                    </button>
                  </Td>
                  <Td>{s.id}</Td>
                  <Td>
                    {isEditing ? (
                      <select className="input py-1" value={editSensor.zone_id || ""} onChange={(e) => setEditSensor({ ...editSensor, zone_id: e.target.value })}>
                        <option value="">{t("notAssigned")}</option>
                        {zones.map((z) => <option key={z.id} value={z.id}>{z.code} · {z.name}</option>)}
                      </select>
                    ) : (zoneCode || <span className="text-slate-400">{t("notAssigned")}</span>)}
                  </Td>
                  <Td>{isEditing
                    ? <input className="input py-1" value={editSensor.code} onChange={(e) => setEditSensor({ ...editSensor, code: e.target.value })} />
                    : <code className="text-xs text-slate-500 dark:text-slate-400">{s.code}</code>}</Td>
                  <Td>
                    {isEditing ? (
                      <select className="input py-1" value={editSensor.sensor_type} onChange={(e) => setEditSensor({ ...editSensor, sensor_type: e.target.value })}>
                        {SENSOR_TYPES.map((x) => <option key={x} value={x}>{t(x)}</option>)}
                      </select>
                    ) : (
                      <span className="font-medium text-slate-800 dark:text-slate-100">{t(s.sensor_type)}</span>
                    )}
                  </Td>
                  <Td>{isEditing
                    ? <input className="input py-1" value={editSensor.unit} onChange={(e) => setEditSensor({ ...editSensor, unit: e.target.value })} />
                    : s.unit}</Td>
                  <Td>
                    {last && typeof last.value === "number"
                      ? <span className="font-semibold text-slate-900 dark:text-white">{last.value.toFixed(2)} <span className="text-slate-400 font-normal">{s.unit}</span></span>
                      : <span className="text-slate-400">{t("noData")}</span>}
                  </Td>
                  <Td>
                    <span className="text-xs text-slate-500">{last?.measured_at ? formatTime(last.measured_at) : "—"}</span>
                  </Td>
                  <Td>
                    <div className="flex gap-1.5 justify-end">
                      {isEditing ? (
                        <>
                          <button className="btn px-2.5 py-1.5" onClick={saveSensor} title={t("save")}><Save className="w-3.5 h-3.5" /></button>
                          <button className="btn-ghost px-2.5 py-1.5" onClick={() => setEditSensor(null)} title={t("cancel")}><X className="w-3.5 h-3.5" /></button>
                        </>
                      ) : (
                        <>
                          {canEdit && <button className="btn-ghost px-2.5 py-1.5" onClick={() => setEditSensor({ ...s })} title={t("edit")}><Pencil className="w-3.5 h-3.5" /></button>}
                          {isAdmin && <button className="btn-danger px-2.5 py-1.5" onClick={() => delSensor(s.id)} title={t("delete")}><Trash2 className="w-3.5 h-3.5" /></button>}
                        </>
                      )}
                    </div>
                  </Td>
                </tr>
                {isOpen && (
                  <tr className="bg-slate-50/60 dark:bg-slate-900/40">
                    <td colSpan={9} className="px-4 py-4">
                      <HistoryView readings={history[s.id]} unit={s.unit} t={t} />
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </DataTable>
      </SectionCard>
    </div>
  );
}

function formatTime(iso) {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "—";
  const now = new Date();
  const diffSec = Math.round((now - d) / 1000);
  if (diffSec < 60) return `${diffSec}s`;
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h`;
  return d.toLocaleString();
}

function SectionCard({ title, children }) {
  return (
    <div className="card overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-800">
        <h3 className="font-semibold text-slate-900 dark:text-white">{title}</h3>
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
}

function DataTable({ headers, children }) {
  return (
    <div className="overflow-x-auto -mx-5 px-5">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
            {headers.map((h, i) => <th key={i} className="px-3 py-2">{h}</th>)}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
          {children}
        </tbody>
      </table>
    </div>
  );
}

function Td({ children }) {
  return <td className="px-3 py-2.5 text-slate-700 dark:text-slate-200 align-middle">{children}</td>;
}

function HistoryView({ readings, unit, t }) {
  if (!readings) return <div className="text-sm text-slate-400">…</div>;
  if (readings.length === 0) return <div className="text-sm text-slate-400">{t("noHistory")}</div>;

  // readings come ordered DESC; reverse for chronological plot
  const points = [...readings].reverse();
  const values = points.map((p) => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const W = 720, H = 90, PAD = 4;
  const xStep = points.length > 1 ? (W - 2 * PAD) / (points.length - 1) : 0;
  const path = points.map((p, i) => {
    const x = PAD + i * xStep;
    const y = H - PAD - ((p.value - min) / span) * (H - 2 * PAD);
    return `${i === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(" ");
  const last = points[points.length - 1];
  const first = points[0];

  return (
    <div className="space-y-2">
      <div className="flex items-baseline gap-4 text-xs text-slate-500">
        <span>min <span className="font-semibold text-slate-700 dark:text-slate-200">{min.toFixed(2)} {unit}</span></span>
        <span>max <span className="font-semibold text-slate-700 dark:text-slate-200">{max.toFixed(2)} {unit}</span></span>
        <span>n = <span className="font-semibold text-slate-700 dark:text-slate-200">{points.length}</span></span>
        <span className="ml-auto">
          {new Date(first.measured_at).toLocaleString()} → {new Date(last.measured_at).toLocaleString()}
        </span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-24" preserveAspectRatio="none">
        <path d={path} fill="none" className="stroke-emerald-500" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
      </svg>
    </div>
  );
}
