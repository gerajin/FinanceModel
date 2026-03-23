import pandas as pd

from .base import ForecastMethod
from prophet import Prophet


class ProphetMethod(ForecastMethod):
    """
    Prophet (Meta/Facebook) para series temporales mensuales.

    Maneja automáticamente tendencia, estacionalidad anual y puntos de quiebre.
    Requiere: pip install prophet
    Confiable con ≥ 24 meses históricos.
    """

    nombre = "prophet"

    def __init__(self, periodos: int = 60):
        if not _PROPHET_OK:
            raise ImportError(
                "prophet no está instalado. Ejecuta: pip install prophet"
            )
        super().__init__(periodos)
        self._model = None
        self._ultimo_periodo = None

    def fit(self, serie: pd.Series) -> None:
        df_prophet = pd.DataFrame({
            "ds": serie.index,
            "y": serie.values,
        })
        self._model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
        )
        self._model.fit(df_prophet)
        self._ultimo_periodo = serie.index[-1]

    def predict(self) -> pd.Series:
        fechas = pd.date_range(
            start=self._ultimo_periodo,
            periods=self.periodos + 1,
            freq="MS",
        )[1:]

        future = pd.DataFrame({"ds": fechas})
        forecast = self._model.predict(future)

        return pd.Series(forecast["yhat"].values, index=fechas, name="proyeccion")
