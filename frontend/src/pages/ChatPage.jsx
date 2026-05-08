import { useEffect, useRef, useState } from "react";
import { Send, Plus, MessageSquare } from "lucide-react";
import { api, wsUrl } from "../api/client.js";
import { useI18n } from "../i18n/i18n.jsx";
import { useAuth } from "../api/auth.jsx";

export default function ChatPage() {
  const { t } = useI18n();
  const { user } = useAuth();
  const [rooms, setRooms] = useState([]);
  const [users, setUsers] = useState([]);
  const [active, setActive] = useState(null);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [newRoom, setNewRoom] = useState("");
  const [err, setErr] = useState("");
  const [showUsers, setShowUsers] = useState(false);
  const wsRef = useRef(null);
  const logRef = useRef(null);

  const loadRooms = async () => {
    try {
      const { data } = await api.get("/chat/rooms");
      setRooms(data || []);
      if (!active && data?.length) setActive(data[0]);
    } catch (e) { setErr(e?.response?.data?.detail || String(e)); }
  };

  const loadUsers = async () => {
    try {
      const { data } = await api.get("/chat/users");
      setUsers(data || []);
    } catch (e) { setErr(e?.response?.data?.detail || String(e)); }
  };

  useEffect(() => {
    loadRooms();
    loadUsers();
  }, []);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    const open = async () => {
      try {
        const { data } = await api.get(`/chat/rooms/${active.id}/messages`, { params: { limit: 100 } });
        if (cancelled) return;
        setMessages(data || []);
      } catch (e) { setErr(e?.response?.data?.detail || String(e)); }

      const token = localStorage.getItem("vdss.token") || "";
      const url = wsUrl(`/chat/ws/${active.id}?token=${encodeURIComponent(token)}`);
      const ws = new WebSocket(url);
      ws.onmessage = (ev) => {
        try { const m = JSON.parse(ev.data); setMessages((p) => [...p, m]); }
        catch { /* ignore */ }
      };
      wsRef.current = ws;
    };
    open();
    return () => {
      cancelled = true;
      try { wsRef.current?.close(); } catch { /* ignore */ }
      wsRef.current = null;
    };
  }, [active]);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [messages]);

  const send = async (e) => {
    e?.preventDefault();
    const body = text.trim();
    if (!body || !active) return;
    setText("");
    if (wsRef.current && wsRef.current.readyState === 1) {
      wsRef.current.send(JSON.stringify({ body }));
    } else {
      try {
        const { data } = await api.post(`/chat/rooms/${active.id}/messages`, { body });
        setMessages((p) => [...p, data]);
      } catch (e) { setErr(e?.response?.data?.detail || String(e)); }
    }
  };

  const createRoom = async () => {
    const name = newRoom.trim();
    if (!name) return;
    try {
      const { data } = await api.post("/chat/rooms", { name });
      setNewRoom(""); await loadRooms(); setActive(data);
    } catch (e) { setErr(e?.response?.data?.detail || String(e)); }
  };

  const startDM = async (userId) => {
    try {
      const { data } = await api.post(`/chat/dm/${userId}`);
      setShowUsers(false);
      await loadRooms();
      setActive(data);
    } catch (e) { setErr(e?.response?.data?.detail || String(e)); }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto h-[calc(100vh-3.5rem)]">
      {err && <div className="badge badge-bad mb-3 px-3 py-2">{err}</div>}
      <div className="grid grid-cols-1 md:grid-cols-[260px_1fr] gap-4 h-full">
        <div className="card flex flex-col">
          {!showUsers ? (
            <>
              <div className="px-4 py-3 border-b border-slate-100 dark:border-slate-800">
                <h3 className="font-semibold text-slate-900 dark:text-white text-sm">{t("channels")}</h3>
              </div>
              <div className="flex-1 overflow-y-auto p-2 space-y-1">
                {rooms.map((r) => (
                  <button
                    key={r.id}
                    onClick={() => setActive(r)}
                    className={`w-full text-left px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      active?.id === r.id
                        ? "bg-slate-900 text-white dark:bg-white dark:text-slate-900"
                        : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                    }`}
                  >
                    {r.is_dm ? `@${r.other_username}` : `# ${r.name}`}
                  </button>
                ))}
              </div>
              <div className="p-2 border-t border-slate-100 dark:border-slate-800 space-y-2">
                <div className="flex gap-2">
                  <input className="input" placeholder={t("newChannel")} value={newRoom} onChange={(e) => setNewRoom(e.target.value)} />
                  <button className="btn-secondary px-2.5" onClick={createRoom}><Plus className="w-4 h-4" /></button>
                </div>
                <button className="btn-secondary w-full text-xs" onClick={() => setShowUsers(true)}>
                   Написати
                </button>
              </div>
            </>
          ) : (
            <>
              <div className="px-4 py-3 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
                <h3 className="font-semibold text-slate-900 dark:text-white text-sm">Співробітники</h3>
                <button className="text-xl" onClick={() => setShowUsers(false)}>✕</button>
              </div>
              <div className="flex-1 overflow-y-auto p-2 space-y-1">
                {users.map((u) => (
                  <button
                    key={u.id}
                    onClick={() => startDM(u.id)}
                    className="w-full text-left px-3 py-2 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800 transition-colors"
                  >
                    @{u.username}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>

        <div className="card flex flex-col min-h-0">
          <div className="px-5 py-3 border-b border-slate-100 dark:border-slate-800 flex items-center gap-2">
            {active?.is_dm ? (
              <span className="w-2 h-2 bg-green-500 rounded-full"></span>
            ) : (
              <MessageSquare className="w-4 h-4 text-slate-400" />
            )}
            <h3 className="font-semibold text-slate-900 dark:text-white">
              {active ? (active.is_dm ? `${active.other_username}` : `# ${active.name}`) : t("pickRoom")}
            </h3>
          </div>
          <div ref={logRef} className="flex-1 overflow-y-auto p-5 space-y-3">
            {messages.map((m) => {
              const own = m.user_id === user?.id;
              return (
                <div key={m.id} className={`flex ${own ? "justify-end" : "justify-start"}`}>
                  <div className={`max-w-[70%] rounded-2xl px-3.5 py-2 text-sm ${
                    own
                      ? "bg-slate-900 text-white dark:bg-white dark:text-slate-900"
                      : "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-100"
                  }`}>
                    {!own && <div className="text-xs font-semibold mb-0.5 opacity-70">{m.username || `#${m.user_id}`}</div>}
                    <div>{m.body}</div>
                    <div className={`text-[10px] mt-1 ${own ? "opacity-70" : "text-slate-400"}`}>
                      {new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
          <form onSubmit={send} className="p-3 border-t border-slate-100 dark:border-slate-800 flex gap-2">
            <input className="input" placeholder={t("message")} value={text} onChange={(e) => setText(e.target.value)} disabled={!active} />
            <button className="btn" disabled={!active}><Send className="w-4 h-4" /> {t("send")}</button>
          </form>
        </div>
      </div>
    </div>
  );
}
