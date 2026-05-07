import { useState } from "react";
import { Link, useNavigate, Navigate } from "react-router-dom";
import { Wind, Loader2 } from "lucide-react";
import { useAuth } from "../api/auth.jsx";
import { useI18n } from "../i18n/i18n.jsx";

export default function LoginPage() {
  const { login, user, ready } = useAuth();
  const { t } = useI18n();
  const nav = useNavigate();
  const [u, setU] = useState("");
  const [p, setP] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  if (ready && user) return <Navigate to="/" replace />;

  const submit = async (e) => {
    e.preventDefault();
    setErr(""); setBusy(true);
    try { await login(u, p); nav("/"); }
    catch (e) { setErr(e?.response?.data?.detail || t("loginFailed")); }
    finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-100 via-slate-50 to-slate-200 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 p-6">
      <div className="w-full max-w-md card p-8">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-11 h-11 rounded-xl bg-slate-900 dark:bg-white flex items-center justify-center">
            <Wind className="w-6 h-6 text-white dark:text-slate-900" />
          </div>
          <div>
            <div className="text-base font-semibold text-slate-900 dark:text-white">{t("appShort")}</div>
            <div className="text-xs text-slate-500 dark:text-slate-400">{t("appTagline")}</div>
          </div>
        </div>

        <h1 className="text-xl font-semibold text-slate-900 dark:text-white mb-1">{t("signIn")}</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
          {t("noAccount")}{" "}
          <Link to="/register" className="text-slate-900 dark:text-white font-medium hover:underline">
            {t("signUp")}
          </Link>
        </p>

        {err && <div className="badge badge-bad mb-4 px-3 py-2 w-full justify-start">{err}</div>}

        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="label">{t("username")}</label>
            <input className="input" value={u} onChange={(e) => setU(e.target.value)} autoFocus />
          </div>
          <div>
            <label className="label">{t("password")}</label>
            <input type="password" className="input" value={p} onChange={(e) => setP(e.target.value)} />
          </div>
          <button className="btn w-full" disabled={busy}>
            {busy && <Loader2 className="w-4 h-4 animate-spin" />}
            {t("signIn")}
          </button>
        </form>
      </div>
    </div>
  );
}
