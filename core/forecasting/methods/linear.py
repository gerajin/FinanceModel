import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from .base import ForecastMethod


class LinearMethod(ForecastMethod):
    """
    Regresión lineal simple: usa el índice temporal como variable independiente.
    Adecuado para series con tendencia clara y sin estacionalidad marcada.
    Confiable con ≥ 12 meses históricos.
    """

    nombre = "linear"

    def __init__(self, periodos: int = 60):
        super().__init__(periodos)
        self._model = LinearRegression()
        self._ultimo_indice: int = 0
        self._freq: str = "MS"  # Month Start

    def fit(self, serie: pd.Series) -> None:
        X = np.arange(len(serie)).reshape(-1, 1)
        y = serie.values
        self._model.fit(X, y)
        self._ultimo_indice = len(serie)
        self._ultimo_periodo = serie.index[-1]

    def predict(self) -> pd.Series:
        indices_futuros = np.arange(
            self._ultimo_indice,
            self._ultimo_indice + self.periodos
        ).reshape(-1, 1)

        valores = self._model.predict(indices_futuros)

        fechas = pd.date_range(
            start=self._ultimo_periodo,
            periods=self.periodos + 1,
            freq=self._freq
        )[1:]  # excluye el último período histórico

        return pd.Series(valores, index=fechas, name="proyeccion")
