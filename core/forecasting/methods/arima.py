import pandas as pd
from statsmodels.tsa.arima.model import ARIMA as StatsARIMA

from .base import ForecastMethod


class ARIMAMethod(ForecastMethod):
    """
    ARIMA(p, d, q) — AutoRegressive Integrated Moving Average.
    
    Sin componente estacional. Bueno para series con tendencia y autocorrelación.
    Confiable con ≥ 18 meses históricos.
    
    Parámetros por defecto (1,1,1) — ajustar según la serie.
    Para selección automática de parámetros considera usar auto_arima de pmdarima.
    """

    nombre = "arima"

    def __init__(self, periodos: int = 60, order: tuple = (1, 1, 1)):
        super().__init__(periodos)
        self.order = order  # (p, d, q)
        self._result = None
        self._ultimo_periodo = None

    def fit(self, serie: pd.Series) -> None:
        modelo = StatsARIMA(serie, order=self.order)
        self._result = modelo.fit(disp=False)
        self._ultimo_periodo = serie.index[-1]

    def predict(self) -> pd.Series:
        forecast = self._result.forecast(steps=self.periodos)

        fechas = pd.date_range(
            start=self._ultimo_periodo,
            periods=self.periodos + 1,
            freq="MS"
        )[1:]

        return pd.Series(forecast.values, index=fechas, name="proyeccion")
