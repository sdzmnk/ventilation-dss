import { useEffect, useState } from "react";
import { ShieldCheck, Check } from "lucide-react";
import { api } from "../api/client.js";
import { useI18n } from "../i18n/i18n.jsx";

const ROLES = ["operator", "engineer", "admin"];

export default function RolesPage() {
  const { t } = useI18n();
  const [users, setUsers] = useState([]);
  const [pickedId, setPickedId] = useState("");
  const [pickedRole, setPickedRole] = useState("operator");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(""); const [err, setErr] = useState("");

  const load = async () => {
    setErr("");
    try { const { data } = await api.get("/users"); setUsers(data || []); }
    catch (e) { setErr(e?.response?.data?.detail || String(e)); }
  };
  useEffect(() => { load(); }, []);

  const picked = users.find((u) => String(u.user_id) === String(pickedId));

  useEffect(() => {
    if (picked?.role) setPickedRole(picked.role);
  }, [picked?.user_id]);

  const apply = async () => {
    if (!picked) return;
    setBusy(true); setMsg(""); setErr("");
    try {
      await api.patch(`/users/${picked.user_id}/role`, { role: pickedRole });
      setMsg(t("roleUpdated"));
      load();
    } catch (e) { setErr(e?.response?.data?.detail || String(e)); }
    finally { setBusy(false); }
  };

  const setRoleQuick = async (user_id, role) => {
    setMsg(""); setErr("");
    try { await api.patch(`/users/${user_id}/role`, { role }); setMsg(t("roleUpdated")); load(); }
    catch (e) { setErr(e?.response?.data?.detail || String(e)); }
  };

  const ROLE_BADGE = {
    admin:    "badge badge-bad",
    engineer: "badge badge-warn",
    operator: "badge badge-ok",
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 max-w-5xl mx-auto">
      {err && <div className="badge badge-bad px-3 py-2">{err}</div>}
      {msg && <div className="badge badge-ok px-3 py-2">{msg}</div>}

      <div className="card p-5">
        <div className="flex items-start gap-4 mb-5">
          <div className="p-2.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-slate-900 dark:text-white">{t("rolesHeader")}</h3>
            <p className="text-xs text-slate-500 mt-0.5">{t("rolesHint")}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 items-end">
          <div>
            <label className="label">{t("pickUser")}</label>
            <select className="input" value={pickedId} onChange={(e) => setPickedId(e.target.value)}>
              <option value="">—</option>
              {users.map((u) => (
                <option key={u.user_id} value={u.user_id}>
                  {u.username} ({u.email})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">{t("role")}</label>
            <select className="input" value={pickedRole} onChange={(e) => setPickedRole(e.target.value)} disabled={!picked}>
              {ROLES.map((r) => <option key={r} value={r}>{t(`role_${r}`)}</option>)}
            </select>
          </div>
          <div>
            <button className="btn w-full" disabled={!picked || busy} onClick={apply}>
              <Check className="w-4 h-4" /> {t("apply")}
            </button>
          </div>
        </div>
      </div>

      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-800">
          <h3 className="font-semibold text-slate-900 dark:text-white">{t("users")}</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                <th className="px-5 py-3">{t("username")}</th>
                <th className="px-5 py-3">{t("email")}</th>
                <th className="px-5 py-3">{t("role")}</th>
                <th className="px-5 py-3">{t("changeRole")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {users.map((u) => (
                <tr key={u.user_id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                  <td className="px-5 py-3 font-medium text-slate-900 dark:text-white">{u.username}</td>
                  <td className="px-5 py-3 text-slate-500">{u.email}</td>
                  <td className="px-5 py-3">
                    <span className={ROLE_BADGE[u.role] || "badge badge-mute"}>{t(`role_${u.role}`) || u.role}</span>
                  </td>
                  <td className="px-5 py-3">
                    <select
                      className="input max-w-[180px]"
                      value={u.role}
                      onChange={(e) => setRoleQuick(u.user_id, e.target.value)}
                    >
                      {ROLES.map((r) => <option key={r} value={r}>{t(`role_${r}`)}</option>)}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
