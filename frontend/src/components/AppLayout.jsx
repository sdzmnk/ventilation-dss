import { useState } from "react";
import { NavLink, useNavigate, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  Activity,
  Sliders,
  Settings,
  Users,
  ShieldCheck,
  MessageSquare,
  UserCircle,
  LogOut,
  Sun,
  Moon,
  Globe,
  Wind,
  Menu,
  X,
} from "lucide-react";
import { useAuth } from "../api/auth.jsx";
import { useI18n } from "../i18n/i18n.jsx";
import { useTheme } from "../theme.jsx";

function buildNav(role, t) {
  const items = [
    { to: "/", label: t("dashboard"), icon: LayoutDashboard, end: true },
    { to: "/sensors", label: t("sensors"), icon: Activity },
    { to: "/optimization", label: t("optimization"), icon: Sliders },
    { to: "/config", label: t("config"), icon: Settings },
    { to: "/chat", label: t("chat"), icon: MessageSquare },
  ];
  if (role === "admin") {
    items.push({ to: "/users", label: t("users"), icon: Users });
    items.push({ to: "/roles", label: t("roles"), icon: ShieldCheck });
  }
  items.push({ to: "/profile", label: t("profile"), icon: UserCircle });
  return items;
}

export default function AppLayout({ children }) {
  const { user, logout } = useAuth();
  const { t, lang, setLang } = useI18n();
  const { theme, toggle } = useTheme();
  const nav = useNavigate();
  const loc = useLocation();
  const [open, setOpen] = useState(false);
  const items = buildNav(user?.role, t);
  const current = items.find((i) =>
    i.end ? loc.pathname === i.to : loc.pathname.startsWith(i.to)
  ) || items[0];

  const sidebar = (
    <div className="flex flex-col h-screen bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800">
      <div className="px-5 py-5 flex items-center gap-3 border-b border-slate-100 dark:border-slate-800 flex-shrink-0">
        <div className="w-9 h-9 rounded-lg bg-slate-900 dark:bg-white flex items-center justify-center">
          <Wind className="w-5 h-5 text-white dark:text-slate-900" />
        </div>
        <div>
          <div className="text-sm font-semibold text-slate-900 dark:text-white leading-tight">{t("appShort")}</div>
          <div className="text-xs text-slate-500 dark:text-slate-400">{t("appTagline")}</div>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto py-3 px-3 space-y-1">
        {items.map((it) => (
          <NavLink
            key={it.to}
            to={it.to}
            end={it.end}
            onClick={() => setOpen(false)}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? "bg-slate-900 text-white dark:bg-white dark:text-slate-900"
                  : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
              }`
            }
          >
            <it.icon className="w-4 h-4" />
            {it.label}
          </NavLink>
        ))}
      </nav>

      <div className="px-3 py-3 border-t border-slate-100 dark:border-slate-800 space-y-2 flex-shrink-0">
        <div className="flex items-center justify-between px-1">
          <button onClick={toggle} className="btn-ghost" title="Theme">
            {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            <span>{theme === "dark" ? t("light") : t("dark")}</span>
          </button>
          <button onClick={() => setLang(lang === "uk" ? "en" : "uk")} className="btn-ghost" title="Language">
            <Globe className="w-4 h-4" />
            <span className="uppercase">{lang}</span>
          </button>
        </div>
        <div className="flex items-center gap-3 p-2 rounded-lg bg-slate-50 dark:bg-slate-800/60">
          <div className="w-8 h-8 rounded-full bg-slate-900 dark:bg-white text-white dark:text-slate-900 flex items-center justify-center text-sm font-semibold flex-shrink-0">
            {user?.username?.[0]?.toUpperCase() || "?"}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-slate-900 dark:text-white truncate">{user?.username}</div>
            <div className="text-xs text-slate-500 dark:text-slate-400 truncate">{t(`role_${user?.role}`) || user?.role}</div>
          </div>
          <button
            onClick={() => { logout(); nav("/login"); }}
            className="text-slate-400 hover:text-red-500 transition-colors flex-shrink-0"
            title={t("logout")}
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="h-screen flex bg-slate-50 dark:bg-slate-950">
      <aside className="hidden lg:flex w-64 flex-shrink-0">{sidebar}</aside>

      {open && (
        <div className="lg:hidden fixed inset-0 z-40 flex">
          <div className="w-64 h-screen overflow-y-auto">{sidebar}</div>
          <div className="flex-1 bg-black/40" onClick={() => setOpen(false)} />
        </div>
      )}

      <div className="flex-1 flex flex-col overflow-hidden">
        <button className="btn-ghost lg:hidden m-2 self-start" onClick={() => setOpen((o) => !o)}>
          {open ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
        </button>
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
