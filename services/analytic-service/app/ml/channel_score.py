import pandas as pd

from ml.weight_service import WeightService


class ChannelScoreService:
    """Per-channel 0..1 danger score derived from dataset baselines.

    Vectorised port of the rule-based scoring from the legacy
    /analytic/predict — used here to produce the `danger_score` feature
    and the training labels for XGBoost.
    """

    NOISE_FLOOR = 0.06

    THRESHOLD_OVERRIDES: dict[str, tuple[float, float, float, float]] = {
        "dp_kp_oo":   (0.0, 22.0, -15.0, 35.0),
        "wind_speed": (0.0, 7.0, 0.0, 14.0),
    }

    def __init__(self, baselines: dict[str, dict]):
        self.baselines = baselines
        self.weights = WeightService.CHANNEL_WEIGHTS
        self.thresholds = self._derive_thresholds()

    def _derive_thresholds(self) -> dict[str, tuple[float, float, float, float]]:
        out: dict[str, tuple[float, float, float, float]] = {}
        for k in self.weights:
            if k in self.THRESHOLD_OVERRIDES:
                out[k] = self.THRESHOLD_OVERRIDES[k]
                continue
            b = self.baselines.get(k)
            if not b:
                continue
            std = max(0.5, float(b.get("std", 1.0)))
            p05 = float(b.get("p05", b.get("min", 0.0)))
            p95 = float(b.get("p95", b.get("max", 0.0)))
            warn_lo = p05 - 0.25 * std
            warn_hi = p95 + 0.25 * std
            crit_lo = p05 - 3.0 * std
            crit_hi = p95 + 3.0 * std
            out[k] = (warn_lo, warn_hi, crit_lo, crit_hi)
        return out

    @staticmethod
    def _scalar_score(
        value: float,
        t: tuple[float, float, float, float],
        nominal: float | None = None,
    ) -> float:
        warn_lo, warn_hi, crit_lo, crit_hi = t
        if nominal is None:
            nominal = (warn_lo + warn_hi) / 2.0
        nominal = max(warn_lo, min(warn_hi, nominal))

        if warn_lo <= value <= warn_hi:
            if value >= nominal:
                half = max(1e-6, warn_hi - nominal)
            else:
                half = max(1e-6, nominal - warn_lo)
            return 0.20 * ((abs(value - nominal) / half) ** 2)
        if value < warn_lo:
            if value <= crit_lo:
                return 1.0
            return 0.20 + 0.80 * (warn_lo - value) / max(1e-6, warn_lo - crit_lo)
        if value >= crit_hi:
            return 1.0
        return 0.20 + 0.80 * (value - warn_hi) / max(1e-6, crit_hi - warn_hi)

    def channel_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return DataFrame of 0..1 danger scores, one column per channel."""
        scores = pd.DataFrame(index=df.index)
        for k in self.weights:
            if k not in df.columns or k not in self.thresholds:
                continue
            t = self.thresholds[k]
            nominal = float(self.baselines.get(k, {}).get("p50", (t[0] + t[1]) / 2.0))
            scores[k] = df[k].apply(lambda v: self._scalar_score(float(v), t, nominal))
        return scores

    def composite(self, scores_row: pd.Series) -> float:
        """Combine per-channel scores into a single 0..1 severity value."""
        weighted = sum(scores_row[k] * self.weights[k] for k in scores_row.index)
        max_score = float(scores_row.max()) if len(scores_row) else 0.0
        severity = max(weighted, 0.7 * max_score)
        return min(1.0, max(self.NOISE_FLOOR, severity))

    def danger_score(self, df: pd.DataFrame) -> pd.Series:
        """0..100 composite danger score, one per row. High = bad."""
        scores = self.channel_scores(df)
        return scores.apply(self.composite, axis=1) * 100.0

    def scores_for_sample(self, sample: dict) -> dict[str, float]:
        """Per-channel 0..1 score for a single sample (for explainability)."""
        out: dict[str, float] = {}
        for k in self.weights:
            if k not in sample or k not in self.thresholds:
                continue
            t = self.thresholds[k]
            nominal = float(self.baselines.get(k, {}).get("p50", (t[0] + t[1]) / 2.0))
            out[k] = self._scalar_score(float(sample[k]), t, nominal)
        return out
