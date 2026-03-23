import pandas as pd

from .base import ForecastMethod


class AverageMethod(ForecastMethod):
    """
    Proyección por promedio simple.

    Repite el promedio histórico para todos los períodos futuros.
    Sin tendencia ni estacionalidad.

    Fallback automático cuando hay menos de 12 meses históricos,
    donde los modelos estadísticos no son confiables.
    """

    nombre = "promedio"

    def __init__(self, periodos: int = 60):
        super().__init__(periodos)
        self._promedio: float = 0.0
        self._ultimo_periodo = None

    def fit(self, serie: pd.Series) -> None:
        self._promedio = float(serie.mean())
        self._ultimo_periodo = serie.index[-1]

    def predict(self) -> pd.Series:
        fechas = pd.date_range(
            start=self._ultimo_periodo,
            periods=self.periodos + 1,
            freq="MS",
        )[1:]

        return pd.Series(
            [self._promedio] * self.periodos,
            index=fechas,
            name="proyeccion",
        )
