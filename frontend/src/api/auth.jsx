import { createContext, useContext, useEffect, useState } from "react";
import { api } from "./client.js";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("vdss.token");
    const cached = localStorage.getItem("vdss.user");
    if (token && cached) {
      try { setUser(JSON.parse(cached)); } catch { /* ignore */ }
    }
    setReady(true);
  }, []);

  const login = async (username, password) => {
    const { data } = await api.post("/auth/login", { username, password });
    persist(data);
    setUser(data.user);
    return data.user;
  };

  const register = async (payload) => {
    const { data } = await api.post("/auth/register", payload);
    persist(data);
    setUser(data.user);
    return data.user;
  };

  const logout = () => {
    localStorage.removeItem("vdss.token");
    localStorage.removeItem("vdss.refresh");
    localStorage.removeItem("vdss.user");
    setUser(null);
  };

  const persist = (data) => {
    localStorage.setItem("vdss.token", data.access_token);
    localStorage.setItem("vdss.refresh", data.refresh_token);
    localStorage.setItem("vdss.user", JSON.stringify(data.user));
  };

  return (
    <AuthCtx.Provider value={{ user, ready, login, register, logout }}>
      {children}
    </AuthCtx.Provider>
  );
}

export function useAuth() {
  return useContext(AuthCtx);
}
