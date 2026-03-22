from abc import ABC, abstractmethod
import pandas as pd


class ForecastMethod(ABC):
    """
    Clase base para todos los métodos de proyección.
    Cada método recibe una Serie temporal y devuelve 60 períodos proyectados.
    """

    def __init__(self, periodos: int = 60):
        self.periodos = periodos  # default: 5 años mensualizados

    @abstractmethod
    def fit(self, serie: pd.Series) -> None:
        """Entrena el modelo con la serie histórica."""
        pass

    @abstractmethod
    def predict(self) -> pd.Series:
        """Devuelve la proyección como Serie con índice DatetimeIndex."""
        pass

    @property
    @abstractmethod
    def nombre(self) -> str:
        """Identificador del método."""
        pass
