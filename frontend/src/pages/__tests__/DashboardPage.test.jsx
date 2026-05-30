
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";

vi.mock("../../api/client.js", () => ({
  api: { get: vi.fn() },
}));

vi.mock("../../api/auth.jsx", () => ({
  useAuth: () => ({ user: { id: 1, username: "alice", role: "operator" }, ready: true }),
}));

vi.mock("../../i18n/i18n.jsx", () => ({
  useI18n: () => ({ t: (k) => k, lang: "uk" }),
}));

vi.mock("../../components/VentilationScheme.jsx", () => ({
  default: () => <div data-testid="ventilation-scheme" />,
}));

vi.mock("../../components/TrendChart.jsx", () => ({
  default: ({ label }) => <div data-testid={`trend-chart-${label}`} />,
}));

vi.mock("lucide-react", () => ({
  Activity: () => <span />,
  ShieldCheck: () => <span />,
  AlertOctagon: () => <span />,
  Wind: () => <span />,
  Gauge: () => <span />,
  Compass: () => <span />,
  TrendingUp: () => <span />,
  Minus: () => <span />,
  BrainCircuit: () => <span />,
  ChevronDown: () => <span />,
  ChevronUp: () => <span />,
}));

import { api } from "../../api/client.js";
import DashboardPage from "../DashboardPage.jsx";

const STATS_DATA = [
  { sensor_type: "pressure_kp", count: 96, mean: -10.0, min: -50.0, max: 14.0, p95: 6.0 },
  { sensor_type: "pressure_oo", count: 96, mean: -17.0, min: -60.0, max: 10.0, p95: 5.0 },
  { sensor_type: "dp_kp_oo",    count: 96, mean: 7.0,   min: -10.0, max: 26.0, p95: 18.0 },
  { sensor_type: "flow_kp_in",  count: 96, mean: 14.0,  min: 8.0,   max: 27.0, p95: 22.0 },
  { sensor_type: "flow_oo_out", count: 96, mean: 30.0,  min: 18.0,  max: 40.0, p95: 38.0 },
  { sensor_type: "wind_speed",  count: 96, mean: 2.0,   min: 0.1,   max: 9.0,  p95: 5.0 },
];

const PREDICTION_DATA = {
  prediction_data: {
    status: "OK",
    risk_score: 96.5,
    confidence: 0.9,
    probabilities: { OK: 0.9, WARNING: 0.05, CRITICAL: 0.05 },
    top_channels: ["dp_kp_oo_by", "flow_oo_in"],
  },
  recommendation: "Система працює нормально.",
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.useFakeTimers();

  api.get.mockImplementation((url) => {
    if (url === "/analytic/stats")   return Promise.resolve({ data: STATS_DATA });
    if (url === "/analytic/predict") return Promise.resolve({ data: PREDICTION_DATA });
    return Promise.resolve({ data: [] });
  });
});

afterEach(() => { vi.useRealTimers(); });

describe("DashboardPage — rendering", () => {
  it("renders without crashing", async () => {
    await act(async () => { render(<DashboardPage />); });
  });

  it("renders the ventilation scheme placeholder", async () => {
    await act(async () => { render(<DashboardPage />); });
    expect(screen.getByTestId("ventilation-scheme")).toBeInTheDocument();
  });

  it("displays risk score after prediction loads", async () => {
    await act(async () => { render(<DashboardPage />); });
    await waitFor(() => {
      expect(screen.getByText(/96\.5/)).toBeInTheDocument();
    });
  });
});

describe("DashboardPage — data fetching", () => {
  it("calls /analytic/stats on mount", async () => {
    await act(async () => { render(<DashboardPage />); });
    expect(api.get).toHaveBeenCalledWith(
      "/analytic/stats",
      expect.objectContaining({ params: { hours: 24 } }),
    );
  });

  it("calls /analytic/predict after stats are loaded", async () => {
    await act(async () => { render(<DashboardPage />); });
    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith("/analytic/predict", expect.any(Object));
    });
  });

  it("passes mean sensor values as params to /analytic/predict", async () => {
    await act(async () => { render(<DashboardPage />); });
    await waitFor(() => {
      const predictCall = api.get.mock.calls.find((c) => c[0] === "/analytic/predict");
      expect(predictCall).toBeTruthy();
      const params = predictCall[1]?.params ?? {};
      expect(params.pressure_kp).toBe(-10.0);
      expect(params.dp_kp_oo).toBe(7.0);
      expect(params.wind_speed).toBe(2.0);
    });
  });

  it("handles API errors gracefully without crashing", async () => {
    api.get.mockRejectedValue(new Error("Network error"));
    await act(async () => { render(<DashboardPage />); });
  });
});

describe("DashboardPage — polling", () => {
  it("re-fetches data after 10 seconds", async () => {
    await act(async () => { render(<DashboardPage />); });
    const initialCallCount = api.get.mock.calls.length;
    await act(async () => { vi.advanceTimersByTime(10000); });
    expect(api.get.mock.calls.length).toBeGreaterThan(initialCallCount);
  });
});
