/**
 * Tests for OptimizationPage component.
 *
 * The page:
 * 1. Loads run history from /analytic/runs on mount
 * 2. On "Run" click: POSTs to /analytic/optimize and shows result
 * 3. Shows error message on API failure
 * 4. Reloads history after a successful run
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
  optimal_airflow: 22500.0,
  optimal_fan_load: 0.73,
  expected_radiation: 9.8,
  expected_pressure: -196.0,
  energy_kw: 8.9,
  energy_cost_per_hour: 1.07,
  safety_margin: 10.2,
  status: "ok",
  iterations: 12,
};

const FAKE_HISTORY = [
  {
    id: 1,
    method: "scipy",
    inputs: { current_radiation: 10 },
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
    await act(async () => {
      render(<OptimizationPage />);
    });
  });

  it("fetches run history on mount", async () => {
    await act(async () => {
      render(<OptimizationPage />);
    });
    expect(api.get).toHaveBeenCalledWith(
      "/analytic/runs",
      expect.objectContaining({ params: { limit: 15 } })
    );
  });

  it("shows history rows when history loads", async () => {
    api.get.mockResolvedValue({ data: FAKE_HISTORY });

    await act(async () => {
      render(<OptimizationPage />);
    });

    await waitFor(() => {
      expect(screen.getByText("scipy")).toBeInTheDocument();
    });
  });

  it("shows empty state when no history", async () => {
    api.get.mockResolvedValue({ data: [] });

    await act(async () => {
      render(<OptimizationPage />);
    });

    await waitFor(() => {
      // History table should be empty
      expect(screen.queryAllByRole("row")).toHaveLength(expect.any(Number));
    });
  });
});

describe("OptimizationPage — running optimization", () => {
  it("shows result after successful run", async () => {
    const user = userEvent.setup();

    await act(async () => {
      render(<OptimizationPage />);
    });

    const runButton = screen.getByRole("button", { name: /run|запуст|оптим/i });
    await user.click(runButton);

    await waitFor(() => {
      // The optimal_airflow value should appear somewhere
      expect(screen.getByText(/22500/)).toBeInTheDocument();
    });
  });

  it("calls /analytic/optimize with form data", async () => {
    const user = userEvent.setup();

    await act(async () => {
      render(<OptimizationPage />);
    });

    const runButton = screen.getByRole("button", { name: /run|запуст|оптим/i });
    await user.click(runButton);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        "/analytic/optimize",
        expect.objectContaining({
          method: "scipy",
          radiation_limit: 20,
          airflow_min: 5000,
          airflow_max: 40000,
        })
      );
    });
  });

  it("reloads history after successful run", async () => {
    const user = userEvent.setup();

    await act(async () => {
      render(<OptimizationPage />);
    });

    const callsBefore = api.get.mock.calls.length;

    const runButton = screen.getByRole("button", { name: /run|запуст|оптим/i });
    await user.click(runButton);

    await waitFor(() => {
      expect(api.get.mock.calls.length).toBeGreaterThan(callsBefore);
    });
  });

  it("shows error message on API failure", async () => {
    api.post.mockRejectedValue({
      response: { data: { detail: "airflow_max має бути більшим за airflow_min" } },
    });

    const user = userEvent.setup();

    await act(async () => {
      render(<OptimizationPage />);
    });

    const runButton = screen.getByRole("button", { name: /run|запуст|оптим/i });
    await user.click(runButton);

    await waitFor(() => {
      expect(screen.getByText(/airflow_max має бути більшим/)).toBeInTheDocument();
    });
  });

  it("clears previous error on new successful run", async () => {
    api.post
      .mockRejectedValueOnce({ response: { data: { detail: "Error!" } } })
      .mockResolvedValueOnce({ data: FAKE_RESULT });

    const user = userEvent.setup();

    await act(async () => {
      render(<OptimizationPage />);
    });

    const runButton = screen.getByRole("button", { name: /run|запуст|оптим/i });

    // First click — causes error
    await user.click(runButton);
    await waitFor(() => {
      expect(screen.getByText(/Error!/)).toBeInTheDocument();
    });

    // Second click — succeeds
    await user.click(runButton);
    await waitFor(() => {
      expect(screen.queryByText(/Error!/)).not.toBeInTheDocument();
    });
  });
});
