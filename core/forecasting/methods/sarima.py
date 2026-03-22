import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX
from pmdarima import auto_arima

from .base import ForecastMethod


class SARIMAMethod(ForecastMethod):
    """
    SARIMA(p,d,q)(P,D,Q,s) — ARIMA con componente estacional.
    
    Ideal para datos con patrones anuales (s=12 para mensual).
    El más completo pero requiere ≥ 24 meses para ser confiable.
    
    Parámetros por defecto: SARIMA(1,1,1)(1,1,1,12)
    Para selección automática considera pmdarima.auto_arima con seasonal=True.
    """

    nombre = "sarima"

    def __init__(
        self,
        periodos: int = 60,
        order: tuple = (1, 1, 1),
        seasonal_order: tuple = (1, 1, 1, 12),  # s=12 → ciclo anual mensual
    ):
        super().__init__(periodos)
        self.order = order
        self.seasonal_order = seasonal_order
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
        #modelo = SARIMAX(
        #    serie,
        #    order=self.order,
        #    seasonal_order=self.seasonal_order,
        #    enforce_stationarity=False,
        #    enforce_invertibility=False,
        #)
        #self._result = modelo.fit(disp=False)
        self._ultimo_periodo = serie.index[-1]

    def predict(self) -> pd.Series:
        forecast = self._result.predict(n_periods=self.periodos)

        fechas = pd.date_range(
            start=self._ultimo_periodo,
            periods=self.periodos + 1,
            freq="MS"
        )[1:]

        return pd.Series(forecast.values, index=fechas, name="proyeccion")
