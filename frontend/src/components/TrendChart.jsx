import { useEffect, useState } from "react";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";
import { api } from "../api/client.js";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler);

export default function TrendChart({ sensorType, label, color = "#60a5fa" }) {
  const [points, setPoints] = useState([]);

  useEffect(() => {
    let ignore = false;
    const run = async () => {
      try {
        const { data } = await api.get("/analytic/trend", {
          params: { sensor_type: sensorType, hours: 24, bucket_minutes: 15 },
        });
        if (!ignore) setPoints(data || []);
      } catch { /* ignore */ }
    };
    run();
    const id = setInterval(run, 30000);
    return () => { ignore = true; clearInterval(id); };
  }, [sensorType]);

  const data = {
    labels: points.map((p) => new Date(p.t).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })),
    datasets: [
      {
        label,
        data: points.map((p) => p.value),
        borderColor: color,
        backgroundColor: `${color}22`,
        tension: 0.35,
        fill: true,
        pointRadius: 0,
        borderWidth: 2,
      },
    ],
  };
  const opts = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: { intersect: false, mode: "index" },
    },
    scales: {
      x: { ticks: { color: "#94a3b8", maxTicksLimit: 6, font: { size: 10 } }, grid: { color: "rgba(148,163,184,0.15)" } },
      y: { ticks: { color: "#94a3b8", font: { size: 10 } }, grid: { color: "rgba(148,163,184,0.15)" } },
    },
  };

  return (
    <div className="rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-100 dark:border-slate-800 p-3">
      <div className="flex items-center justify-between mb-2 px-1">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full" style={{ background: color }} />
          <span className="text-sm font-medium text-slate-700 dark:text-slate-200">{label}</span>
        </div>
        <span className="text-xs text-slate-400">24h</span>
      </div>
      <div className="h-44">
        <Line data={data} options={opts} />
      </div>
    </div>
  );
}
