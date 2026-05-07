/**
 * Tests for DashboardPage component.
 *
 * We mock:
 * - api client (axios) to control what data the dashboard receives
 * - AuthProvider / useAuth to simulate a logged-in user
 * - i18n to avoid loading dictionaries
 * - Chart.js components to avoid canvas errors in jsdom
 * - VentilationScheme SVG component
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";

// ===== Mock dependencies =====

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

// Mock lucide-react icons to avoid SVG issues
vi.mock("lucide-react", () => ({
  Activity: () => <span />,
  ShieldCheck: () => <span />,
  AlertOctagon: () => <span />,
  Wind: () => <span />,
  Thermometer: () => <span />,
  TrendingUp: () => <span />,
  Minus: () => <span />,
  List: () => <span />,
  BrainCircuit: () => <span />,
  ChevronDown: () => <span />,
  ChevronUp: () => <span />,
}));

import { api } from "../../api/client.js";
import DashboardPage from "../DashboardPage.jsx";

const LATEST_DATA = [
  { sensor_id: 1, sensor_type: "radiation", sensor_code: "S-RAD-01", value: 8.5, unit: "мкЗв/год", zone_name: "Зона 1", measured_at: "2024-01-01T12:00:00Z" },
  { sensor_id: 2, sensor_type: "pressure",  sensor_code: "S-PRE-01", value: -120.0, unit: "Па", zone_name: "Зона 1", measured_at: "2024-01-01T12:00:00Z" },
  { sensor_id: 3, sensor_type: "airflow",   sensor_code: "S-AIR-01", value: 18000.0, unit: "м³/год", zone_name: "Зона 2", measured_at: "2024-01-01T12:00:00Z" },
  { sensor_id: 4, sensor_type: "temperature", sensor_code: "S-TEM-01", value: 22.0, unit: "°C", zone_name: "Зона 2", measured_at: "2024-01-01T12:00:00Z" },
];

const STATS_DATA = [
  { sensor_type: "radiation", count: 96, mean: 8.5, min: 5.0, max: 12.0, p95: 11.5 },
  { sensor_type: "pressure",  count: 96, mean: -120.0, min: -145.0, max: -95.0, p95: -97.0 },
  { sensor_type: "airflow",   count: 96, mean: 18000.0, min: 15000.0, max: 21000.0, p95: 20500.0 },
  { sensor_type: "temperature", count: 96, mean: 22.0, min: 20.5, max: 23.5, p95: 23.0 },
];

const PREDICTION_DATA = {
  prediction_data: {
    status: "OK",
    risk_score: 96.5,
    confidence: 0.9,
    probabilities: { OK: 0.9, WARNING: 0.05, CRITICAL: 0.05 },
  },
  recommendation: "Система працює нормально.",
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.useFakeTimers();

  api.get.mockImplementation((url) => {
    if (url === "/readings/latest") return Promise.resolve({ data: LATEST_DATA });
    if (url === "/analytic/stats")  return Promise.resolve({ data: STATS_DATA });
    if (url === "/analytic/predict") return Promise.resolve({ data: PREDICTION_DATA });
    return Promise.resolve({ data: [] });
  });
});

afterEach(() => {
  vi.useRealTimers();
});

describe("DashboardPage — rendering", () => {
  it("renders without crashing", async () => {
    await act(async () => {
      render(<DashboardPage />);
    });
    // If we get here without errors, the component rendered successfully
  });

  it("renders the ventilation scheme placeholder", async () => {
    await act(async () => {
      render(<DashboardPage />);
    });
    expect(screen.getByTestId("ventilation-scheme")).toBeInTheDocument();
  });

  it("shows OK status chip after data loads", async () => {
    await act(async () => {
      render(<DashboardPage />);
    });
    await waitFor(() => {
      expect(screen.getByText("OK")).toBeInTheDocument();
    });
  });

  it("displays risk score after prediction loads", async () => {
    await act(async () => {
      render(<DashboardPage />);
    });
    await waitFor(() => {
      expect(screen.getByText(/96\.5/)).toBeInTheDocument();
    });
  });
});

describe("DashboardPage — data fetching", () => {
  it("calls /readings/latest on mount", async () => {
    await act(async () => {
      render(<DashboardPage />);
    });
    expect(api.get).toHaveBeenCalledWith("/readings/latest");
  });

  it("calls /analytic/stats on mount", async () => {
    await act(async () => {
      render(<DashboardPage />);
    });
    expect(api.get).toHaveBeenCalledWith(
      "/analytic/stats",
      expect.objectContaining({ params: { hours: 24 } })
    );
  });

  it("calls /analytic/predict after stats are loaded", async () => {
    await act(async () => {
      render(<DashboardPage />);
    });
    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith(
        "/analytic/predict",
        expect.any(Object)
      );
    });
  });

  it("passes mean sensor values as params to /analytic/predict", async () => {
    await act(async () => {
      render(<DashboardPage />);
    });
    await waitFor(() => {
      const predictCall = api.get.mock.calls.find((c) => c[0] === "/analytic/predict");
      expect(predictCall).toBeTruthy();
      const params = predictCall[1]?.params ?? {};
      expect(params.radiation).toBe(8.5);
      expect(params.pressure).toBe(-120.0);
    });
  });

  it("handles API errors gracefully without crashing", async () => {
    api.get.mockRejectedValue(new Error("Network error"));
    await act(async () => {
      render(<DashboardPage />);
    });
    // Should not throw
  });
});

describe("DashboardPage — polling", () => {
  it("re-fetches data after 10 seconds", async () => {
    await act(async () => {
      render(<DashboardPage />);
    });

    const initialCallCount = api.get.mock.calls.length;

    await act(async () => {
      vi.advanceTimersByTime(10000);
    });

    expect(api.get.mock.calls.length).toBeGreaterThan(initialCallCount);
  });
});
