import axios from "axios";

const baseURL = import.meta.env.VITE_API_URL || "/api";

export const api = axios.create({ baseURL });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("vdss.token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err?.response?.status === 401) {
      localStorage.removeItem("vdss.token");
      localStorage.removeItem("vdss.refresh");
      localStorage.removeItem("vdss.user");
    }
    return Promise.reject(err);
  }
);

export function wsUrl(path) {
  const httpBase = baseURL.startsWith("http")
    ? baseURL
    : `${window.location.origin}${baseURL.startsWith("/") ? "" : "/"}${baseURL}`;
  const url = new URL(httpBase, window.location.origin);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return `${url.origin}${url.pathname.replace(/\/$/, "")}${path}`;
}
