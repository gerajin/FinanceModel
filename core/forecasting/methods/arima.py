import pandas as pd
from pmdarima import auto_arima

from .base import ForecastMethod


class ARIMAMethod(ForecastMethod):
    """
    ARIMA automático sin componente estacional.

    Usa auto_arima(seasonal=False) para selección automática de (p,d,q).
    Bueno para series con tendencia y autocorrelación sin patrón estacional marcado.
    Confiable con ≥ 18 meses históricos.
    """

    nombre = "arima"

    def __init__(self, periodos: int = 60):
        super().__init__(periodos)
        self._result = None
        self._ultimo_periodo = None

    def fit(self, serie: pd.Series) -> None:
        self._result = auto_arima(
            serie,
            seasonal=False,
            stepwise=True,
            suppress_warnings=True,
            error_action="ignore",
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
