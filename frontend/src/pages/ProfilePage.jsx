import { useEffect, useState } from "react";
import { Save, UserCircle } from "lucide-react";
import { api } from "../api/client.js";
import { useI18n } from "../i18n/i18n.jsx";

export default function ProfilePage() {
  const { t } = useI18n();
  const [form, setForm] = useState({ full_name: "", position: "", department: "", phone: "" });
  const [meta, setMeta] = useState(null);
  const [msg, setMsg] = useState(""); const [err, setErr] = useState("");

  const load = async () => {
    setErr("");
    try {
      const { data } = await api.get("/users/me");
      setMeta(data);
      setForm({
        full_name: data.full_name || "",
        position: data.position || "",
        department: data.department || "",
        phone: data.phone || "",
      });
    } catch (e) { setErr(e?.response?.data?.detail || String(e)); }
  };
  useEffect(() => { load(); }, []);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const save = async () => {
    setErr(""); setMsg("");
    try { await api.put("/users/me", form); setMsg(t("saved")); load(); }
    catch (e) { setErr(e?.response?.data?.detail || String(e)); }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 max-w-3xl mx-auto">
      {err && <div className="badge badge-bad px-3 py-2">{err}</div>}
      {msg && <div className="badge badge-ok px-3 py-2">{msg}</div>}

      <div className="card p-6">
        <div className="flex items-center gap-4 pb-5 border-b border-slate-100 dark:border-slate-800">
          <div className="w-14 h-14 rounded-full bg-slate-900 dark:bg-white text-white dark:text-slate-900 flex items-center justify-center text-xl font-semibold">
            {meta?.username?.[0]?.toUpperCase() || <UserCircle className="w-6 h-6" />}
          </div>
          <div>
            <div className="text-lg font-semibold text-slate-900 dark:text-white">{meta?.username || "—"}</div>
            <div className="text-sm text-slate-500 dark:text-slate-400">{meta?.email}</div>
            <div className="mt-1"><span className="badge badge-mute">{t(`role_${meta?.role}`) || meta?.role}</span></div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-5">
          <div><label className="label">{t("fullName")}</label><input className="input" value={form.full_name} onChange={set("full_name")} /></div>
          <div><label className="label">{t("position")}</label><input className="input" value={form.position} onChange={set("position")} /></div>
          <div><label className="label">{t("department")}</label><input className="input" value={form.department} onChange={set("department")} /></div>
          <div><label className="label">{t("phone")}</label><input className="input" value={form.phone} onChange={set("phone")} /></div>
        </div>
        <div className="mt-5">
          <button className="btn" onClick={save}><Save className="w-4 h-4" /> {t("save")}</button>
        </div>
      </div>
    </div>
  );
}
