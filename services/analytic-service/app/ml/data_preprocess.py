import pandas as pd


class VentilationPreprocessingService:
    """Coerce raw CSV columns to numeric and drop non-feature columns."""

    DROP_COLUMNS = ("ts",)

    @classmethod
    def preprocess(cls, dataset: pd.DataFrame) -> pd.DataFrame:
        data = dataset.copy()

        for col in cls.DROP_COLUMNS:
            if col in data.columns:
                data = data.drop(columns=[col])

        for col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")

        return data.dropna(how="any").reset_index(drop=True)
