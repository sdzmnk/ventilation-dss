/**
 * Tests for OptimizationPage component (new KP/OO/Δp optimizer).
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("../../api/client.js", () => ({
  api: { get: vi.fn(), post: vi.fn() },
}));

vi.mock("../../i18n/i18n.jsx", () => ({
  useI18n: () => ({ t: (k) => k }),
}));

vi.mock("lucide-react", () => ({
  Sliders: () => <span />,
  Play: () => <span />,
  Loader2: () => <span />,
  Wind: () => <span />,
  Gauge: () => <span />,
  AlertOctagon: () => <span />,
  Activity: () => <span />,
  Zap: () => <span />,
  CircleDollarSign: () => <span />,
  ShieldCheck: () => <span />,
}));

import { api } from "../../api/client.js";
import OptimizationPage from "../OptimizationPage.jsx";

const FAKE_RESULT = {
  id: 1,
  method: "scipy",
  optimal_flow_kp: 18.5,
  optimal_flow_oo: 32.0,
  optimal_fan_load: 0.55,
  expected_pressure_kp: -12.0,
  expected_pressure_oo: -19.0,
  expected_dp_kp_oo: 7.0,
  energy_kw: 8.9,
  energy_cost_per_hour: 1.07,
  safety_margin: 5.0,
  status: "ok",
  iterations: 12,
};

const FAKE_HISTORY = [
  {
    id: 1,
    method: "scipy",
    inputs: { current_wind_speed: 2 },
    result: FAKE_RESULT,
    status: "ok",
    created_at: "2024-01-01T12:00:00Z",
    finished_at: "2024-01-01T12:00:01Z",
  },
];

beforeEach(() => {
  vi.clearAllMocks();
  api.get.mockResolvedValue({ data: [] });
  api.post.mockResolvedValue({ data: FAKE_RESULT });
});

describe("OptimizationPage — initial load", () => {
  it("renders without crashing", async () => {
    await act(async () => { render(<OptimizationPage />); });
  });

  it("fetches run history on mount", async () => {
    await act(async () => { render(<OptimizationPage />); });
    expect(api.get).toHaveBeenCalledWith(
      "/analytic/runs",
      expect.objectContaining({ params: { limit: 15 } }),
    );
  });

  it("shows history rows when history loads", async () => {
    api.get.mockResolvedValue({ data: FAKE_HISTORY });
    await act(async () => { render(<OptimizationPage />); });
    await waitFor(() => {
      expect(screen.getByText("scipy")).toBeInTheDocument();
    });
  });
});

describe("OptimizationPage — running optimization", () => {
  it("shows result after successful run", async () => {
    const user = userEvent.setup();
    await act(async () => { render(<OptimizationPage />); });
    const runButton = screen.getByRole("button", { name: /run|запуст|оптим/i });
    await user.click(runButton);
    await waitFor(() => {
      // optimal_flow_kp = 18.5 should appear in the result panel
      expect(screen.getByText(/18\.5/)).toBeInTheDocument();
    });
  });

  it("calls /analytic/optimize with form data", async () => {
    const user = userEvent.setup();
    await act(async () => { render(<OptimizationPage />); });
    const runButton = screen.getByRole("button", { name: /run|запуст|оптим/i });
    await user.click(runButton);
    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        "/analytic/optimize",
        expect.objectContaining({
          method: "scipy",
          dp_kp_oo_min: 2,
          flow_kp_min: 10,
          flow_kp_max: 28,
          flow_oo_min: 15,
          flow_oo_max: 40,
        }),
      );
    });
  });

  it("reloads history after successful run", async () => {
    const user = userEvent.setup();
    await act(async () => { render(<OptimizationPage />); });
    const callsBefore = api.get.mock.calls.length;
    const runButton = screen.getByRole("button", { name: /run|запуст|оптим/i });
    await user.click(runButton);
    await waitFor(() => {
      expect(api.get.mock.calls.length).toBeGreaterThan(callsBefore);
    });
  });

  it("shows error message on API failure", async () => {
    api.post.mockRejectedValue({
      response: { data: { detail: "flow_kp_max має бути більшим за flow_kp_min" } },
    });
    const user = userEvent.setup();
    await act(async () => { render(<OptimizationPage />); });
    const runButton = screen.getByRole("button", { name: /run|запуст|оптим/i });
    await user.click(runButton);
    await waitFor(() => {
      expect(screen.getByText(/flow_kp_max має бути більшим/)).toBeInTheDocument();
    });
  });
});
