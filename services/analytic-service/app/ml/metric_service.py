import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)


class ModelMetricsService:
    @staticmethod
    def accuracy(y_true, y_pred) -> float:
        return round(accuracy_score(y_true, y_pred), 4)

    @staticmethod
    def classification(y_true, y_pred) -> dict:
        return classification_report(y_true, y_pred, output_dict=True)

    @staticmethod
    def matrix(y_true, y_pred) -> list[list[int]]:
        return confusion_matrix(y_true, y_pred).tolist()

    @staticmethod
    def feature_importance(features, importance) -> list[dict]:
        importance_df = pd.DataFrame({
            "feature": features,
            "importance": importance,
        })
        return (
            importance_df
            .sort_values(by="importance", ascending=False)
            .to_dict(orient="records")
        )

    @classmethod
    def full_report(cls, y_true, y_pred, features, importance) -> dict:
        return {
            "accuracy": cls.accuracy(y_true, y_pred),
            "classification_report": cls.classification(y_true, y_pred),
            "confusion_matrix": cls.matrix(y_true, y_pred),
            "feature_importance": cls.feature_importance(features, importance),
        }
