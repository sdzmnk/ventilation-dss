import pandas as pd

from ml.channel_score import ChannelScoreService


class VentilationFeatureEngineeringService:
    """Engineered features built on top of the raw 22 ventilation channels."""

    ENGINEERED_FEATURES = [
        "danger_score",
        "weighted_index",
        "total_deviation",
        "flow_balance",
        "gu_max_abs_dev",
    ]

    GU_PRESSURE_COLUMNS = (
        "gu_pressure_west_wall",
        "gu_pressure_east_wall",
        "gu_pressure_cyl_wall",
        "gu_pressure_west_gap",
        "gu_pressure_east_gap",
        "gu_pressure_vsro",
    )

    def __init__(self, channels: list[str], baselines: dict[str, dict]):
        self.channels = channels
        self.baselines = baselines
        self.score_service = ChannelScoreService(baselines)

    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        scores = self.score_service.channel_scores(df)
        weights = self.score_service.weights

        df["weighted_index"] = sum(scores[k] * weights[k] for k in scores.columns)
        df["danger_score"] = scores.apply(self.score_service.composite, axis=1) * 100.0

        deviation = pd.Series(0.0, index=df.index)
        for k in self.channels:
            b = self.baselines.get(k)
            if not b:
                continue
            p50 = float(b.get("p50", 0.0))
            std = max(0.5, float(b.get("std", 1.0)))
            deviation += (df[k] - p50).abs() / std
        df["total_deviation"] = deviation

        if "flow_kp_in" in df.columns and "flow_oo_out" in df.columns:
            df["flow_balance"] = df["flow_kp_in"] - df["flow_oo_out"]
        else:
            df["flow_balance"] = 0.0

        gu_cols = [c for c in self.GU_PRESSURE_COLUMNS if c in df.columns]
        if gu_cols:
            df["gu_max_abs_dev"] = df[gu_cols].abs().max(axis=1)
        else:
            df["gu_max_abs_dev"] = 0.0

        return df
