
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

vi.mock("axios", () => {
  const interceptors = {
    request: { use: vi.fn((fn) => { interceptors._reqFn = fn; }) },
    response: { use: vi.fn((ok, err) => { interceptors._resOk = ok; interceptors._resErr = err; }) },
  };
  const instance = { interceptors };
  return { default: { create: vi.fn(() => instance) } };
});

beforeEach(() => {
  vi.resetModules();
  localStorage.clear();
});

afterEach(() => {
  localStorage.clear();
});

describe("Request interceptor — injects Bearer token", () => {
  it("adds Authorization header when token is in localStorage", async () => {
    localStorage.setItem("vdss.token", "my.jwt.token");
    const { api } = await import("../client.js");
    const reqFn = api.interceptors._reqFn;

    const config = { headers: {} };
    const result = reqFn(config);
    expect(result.headers.Authorization).toBe("Bearer my.jwt.token");
  });

  it("does not add Authorization header when no token stored", async () => {
    const { api } = await import("../client.js");
    const reqFn = api.interceptors._reqFn;

    const config = { headers: {} };
    const result = reqFn(config);
    expect(result.headers.Authorization).toBeUndefined();
  });
});

describe("Response interceptor — clears storage on 401", () => {
  it("clears all vdss.* keys on 401", async () => {
    localStorage.setItem("vdss.token", "tok");
    localStorage.setItem("vdss.refresh", "ref");
    localStorage.setItem("vdss.user", '{"id":1}');

    const { api } = await import("../client.js");
    const errFn = api.interceptors._resErr;

    const error = { response: { status: 401 } };
    await expect(errFn(error)).rejects.toEqual(error);

    expect(localStorage.getItem("vdss.token")).toBeNull();
    expect(localStorage.getItem("vdss.refresh")).toBeNull();
    expect(localStorage.getItem("vdss.user")).toBeNull();
  });

  it("does not clear storage on 403", async () => {
    localStorage.setItem("vdss.token", "tok");

    const { api } = await import("../client.js");
    const errFn = api.interceptors._resErr;

    const error = { response: { status: 403 } };
    await expect(errFn(error)).rejects.toEqual(error);

    expect(localStorage.getItem("vdss.token")).toBe("tok");
  });

  it("does not clear storage on network error (no response)", async () => {
    localStorage.setItem("vdss.token", "tok");

    const { api } = await import("../client.js");
    const errFn = api.interceptors._resErr;

    const error = { message: "Network Error" };
    await expect(errFn(error)).rejects.toEqual(error);

    expect(localStorage.getItem("vdss.token")).toBe("tok");
  });

  it("passes through successful responses unchanged", async () => {
    const { api } = await import("../client.js");
    const okFn = api.interceptors._resOk;

    const response = { status: 200, data: { result: "ok" } };
    expect(okFn(response)).toEqual(response);
  });
});

describe("wsUrl — WebSocket URL builder", () => {
  it("converts http: to ws:", async () => {
    const { wsUrl } = await import("../client.js");

    Object.defineProperty(window, "location", {
      value: { origin: "http://localhost:5173", protocol: "http:" },
      writable: true,
    });

    const url = wsUrl("/chat/ws/1");
    expect(url).toMatch(/^ws:\/\//);
  });

  it("converts https: to wss:", async () => {
    const { wsUrl } = await import("../client.js");

    Object.defineProperty(window, "location", {
      value: { origin: "https://example.com", protocol: "https:" },
      writable: true,
    });

    const url = wsUrl("/chat/ws/1");
    expect(url).toMatch(/^wss:\/\//);
  });

  it("includes the path suffix in the URL", async () => {
    const { wsUrl } = await import("../client.js");

    Object.defineProperty(window, "location", {
      value: { origin: "http://localhost:5173", protocol: "http:" },
      writable: true,
    });

    const url = wsUrl("/chat/ws/42");
    expect(url).toContain("/chat/ws/42");
  });
});
