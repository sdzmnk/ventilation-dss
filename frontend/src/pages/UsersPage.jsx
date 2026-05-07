import { useEffect, useState } from "react";
import { Trash2 } from "lucide-react";
import { api } from "../api/client.js";
import { useI18n } from "../i18n/i18n.jsx";

const ROLE_BADGE = {
  admin:    "badge badge-bad",
  engineer: "badge badge-warn",
  operator: "badge badge-ok",
};

export default function UsersPage() {
  const { t } = useI18n();
  const [rows, setRows] = useState([]);
  const [err, setErr] = useState("");

  const load = async () => {
    setErr("");
    try { const { data } = await api.get("/users"); setRows(data || []); }
    catch (e) { setErr(e?.response?.data?.detail || String(e)); }
  };
  useEffect(() => { load(); }, []);

  const remove = async (id) => {
    if (!confirm(`Видалити користувача #${id}?`)) return;
    try { await api.delete(`/users/${id}`); load(); }
    catch (e) { setErr(e?.response?.data?.detail || String(e)); }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      {err && <div className="badge badge-bad px-3 py-2">{err}</div>}

      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-800">
          <h3 className="font-semibold text-slate-900 dark:text-white">{t("users")}</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                <th className="px-5 py-3">#</th>
                <th className="px-5 py-3">{t("username")}</th>
                <th className="px-5 py-3">{t("email")}</th>
                <th className="px-5 py-3">{t("role")}</th>
                <th className="px-5 py-3">{t("fullName")}</th>
                <th className="px-5 py-3">{t("position")}</th>
                <th className="px-5 py-3">{t("department")}</th>
                <th className="px-5 py-3">{t("phone")}</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {rows.map((u) => (
                <tr key={u.user_id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                  <td className="px-5 py-3 text-slate-500">{u.user_id}</td>
                  <td className="px-5 py-3 font-medium text-slate-900 dark:text-white">{u.username}</td>
                  <td className="px-5 py-3 text-slate-500">{u.email}</td>
                  <td className="px-5 py-3">
                    <span className={ROLE_BADGE[u.role] || "badge badge-mute"}>
                      {t(`role_${u.role}`) || u.role}
                    </span>
                  </td>
                  <td className="px-5 py-3">{u.full_name || "—"}</td>
                  <td className="px-5 py-3">{u.position || "—"}</td>
                  <td className="px-5 py-3">{u.department || "—"}</td>
                  <td className="px-5 py-3">{u.phone || "—"}</td>
                  <td className="px-5 py-3 text-right">
                    <button className="btn-danger px-2.5 py-1.5" onClick={() => remove(u.user_id)} title={t("delete")}>
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
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
