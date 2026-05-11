import pandas as pd


class HVACStateService:
    """Map danger_score (0..100, high = bad) to a discrete HVAC state."""

    @staticmethod
    def create_state(row: pd.Series) -> str:
        danger = row["danger_score"]
        if danger >= 65:
            return "CRITICAL"
        if danger >= 35:
            return "WARNING"
        return "OK"
