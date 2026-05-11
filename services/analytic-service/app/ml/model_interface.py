from abc import ABC, abstractmethod
import pandas as pd


class ModelInterface(ABC):
    @abstractmethod
    def train(self, dataset: pd.DataFrame):
        pass

    @abstractmethod
    def predict(self, sample: dict) -> dict:
        pass
