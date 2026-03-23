import pandas as pd
from pmdarima import auto_arima

from .base import ForecastMethod


class SARIMAMethod(ForecastMethod):
    """
    SARIMA automático con componente estacional (s=12 para datos mensuales).

    Usa auto_arima(seasonal=True, m=12) para selección automática de parámetros.
    Ideal para series con patrones anuales.
    Confiable con ≥ 24 meses históricos.
    """

    nombre = "sarima"

    def __init__(self, periodos: int = 60):
        super().__init__(periodos)
        self._result = None
        self._ultimo_periodo = None

    def fit(self, serie: pd.Series) -> None:
        self._result = auto_arima(
            serie,
            seasonal=True,
            m=12,
            stepwise=True,
            suppress_warnings=True,
            error_action="ignore",
            max_D=1,
            D=0,
        )
        self._ultimo_periodo = serie.index[-1]

    def predict(self) -> pd.Series:
        forecast = self._result.predict(n_periods=self.periodos)

        fechas = pd.date_range(
            start=self._ultimo_periodo,
            periods=self.periodos + 1,
            freq="MS",
        )[1:]

        return pd.Series(forecast.values, index=fechas, name="proyeccion")
