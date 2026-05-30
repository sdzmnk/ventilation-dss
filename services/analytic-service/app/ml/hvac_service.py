import logging

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

from ml.feature_engineering import VentilationFeatureEngineeringService
from ml.metric_service import ModelMetricsService
from ml.model_interface import ModelInterface
from ml.risk_policy import HVACStateService
from ml.weight_service import WeightService

log = logging.getLogger(__name__)


class HVACVentilationModelService(ModelInterface):
    """XGBoost classifier over the 22 ventilation channels.

    Labels are generated from the rule-based danger_score computed in
    feature engineering, so the trained model reproduces the legacy
    rule logic while remaining learnable from raw sensor readings.
    """

    def __init__(self, baselines: dict[str, dict]):
        self.baselines = baselines
        self.core_cols: list[str] = []
        self.features: list[str] = []
        self.latest_sample: dict | None = None
        self.latest_batch: list[dict] = []
        self.is_trained = False
        self.encoder = LabelEncoder()
        self.metrics: dict = {}
        self.top_channels: list[str] = []

        self.model = XGBClassifier(
            n_estimators=400,
            learning_rate=0.05,
            max_depth=5,
            subsample=0.8,
            colsample_bytree=0.8,
            eval_metric="mlogloss",
            random_state=42,
        )
        self.feature_engineer: VentilationFeatureEngineeringService | None = None

    def train(self, dataset: pd.DataFrame):
        df = dataset.copy()
        self._initialize(df)

        self.feature_engineer.create_features(df)

        df["hvac_state"] = df.apply(HVACStateService.create_state, axis=1)
        df = df.dropna(subset=self.features)

        X = df[self.features]
        y = df["hvac_state"]
        y_encoded = self.encoder.fit_transform(y)

        if len(set(y_encoded)) < 2:
            log.warning(
                "Training data has a single class (%s) — skipping XGBoost fit",
                set(y),
            )
            self.is_trained = False
            return self

        X_train, X_test, y_train, y_test = train_test_split(
            X, y_encoded,
            test_size=0.2,
            random_state=42,
            stratify=y_encoded,
        )

        self.model.fit(X_train, y_train)
        predictions = self.model.predict(X_test)

        self.metrics = ModelMetricsService.full_report(
            y_true=self.encoder.inverse_transform(y_test),
            y_pred=self.encoder.inverse_transform(predictions),
            features=self.features,
            importance=self.model.feature_importances_,
        )
        self.is_trained = True
        raw_channels = set(WeightService.CHANNEL_WEIGHTS)
        self.top_channels = [
            f["feature"]
            for f in self.metrics["feature_importance"]
            if f["feature"] in raw_channels and f["importance"] > 0
        ]
        log.info(
            "HVACVentilationModel trained: rows=%d features=%d accuracy=%s classes=%s top_channels=%s",
            len(df), len(self.features), self.metrics["accuracy"],
            list(self.encoder.classes_), self.top_channels[:5],
        )
        return self

    def predict(self, sample: dict) -> dict:
        if not self.is_trained:
            return {
                "status": "MODEL_NOT_READY",
                "risk_score": None,
                "confidence": None,
                "probabilities": {},
            }

        data = pd.DataFrame([sample])
        self.feature_engineer.create_features(data)

        X_input = data[self.features]
        pred = self.model.predict(X_input)[0]
        probabilities = self.model.predict_proba(X_input)[0]

        danger = float(data["danger_score"].iloc[0])
        return {
            "status": self.encoder.inverse_transform([pred])[0],
            "risk_score": round(100.0 - danger, 2),
            "danger_score": round(danger, 2),
            "confidence": round(float(np.max(probabilities)), 4),
            "probabilities": {
                self.encoder.classes_[i]: round(float(probabilities[i]), 4)
                for i in range(len(probabilities))
            },
        }

    def predict_batch(self, samples: list[dict]) -> list[dict]:
        if not self.is_trained or not samples:
            return []

        df = pd.DataFrame(samples)
        self.feature_engineer.create_features(df)
        X = df[self.features]

        predictions = self.model.predict(X)
        probabilities = self.model.predict_proba(X)

        results = []
        for i, pred in enumerate(predictions):
            danger = float(df["danger_score"].iloc[i])
            results.append({
                "status": self.encoder.inverse_transform([pred])[0],
                "risk_score": round(100.0 - danger, 2),
                "danger_score": round(danger, 2),
                "confidence": round(float(np.max(probabilities[i])), 4),
                "probabilities": {
                    self.encoder.classes_[j]: round(float(probabilities[i][j]), 4)
                    for j in range(len(probabilities[i]))
                },
            })
        return results

    def _initialize(self, df: pd.DataFrame) -> None:
        known = WeightService.CHANNEL_WEIGHTS
        self.core_cols = [c for c in df.columns if c in known]
        self.feature_engineer = VentilationFeatureEngineeringService(
            channels=self.core_cols,
            baselines=self.baselines,
        )
        self.features = self.core_cols + self.feature_engineer.ENGINEERED_FEATURES
