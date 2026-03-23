import pandas as pd

from .parser import cargar_csv, confiabilidad
from .premisas import Premisas
from .builder import construir_pnl_mensual, construir_pnl_anual
from .methods.average import AverageMethod
from .methods.linear import LinearMethod
from .methods.arima import ARIMAMethod
from .methods.sarima import SARIMAMethod


METODOS_DISPONIBLES = {
    "promedio": AverageMethod,
    "linear":   LinearMethod,
    "arima":    ARIMAMethod,
    "sarima":   SARIMAMethod,
}

try:
    from .methods.prophet import ProphetMethod, _PROPHET_OK
    if _PROPHET_OK:
        METODOS_DISPONIBLES["prophet"] = ProphetMethod
except ImportError:
    pass


def ejecutar_forecast(
    ruta_csv: str,
    premisas: Premisas = None,
    metodo: str = "auto",
    periodos: int = 60,
) -> dict:
    """
    Pipeline completo: CSV → P&L proyectado mensual y anual.

    Solo el volumen es proyectado con el modelo estadístico.
    Los demás conceptos se derivan con reglas de negocio y premisas:
        - precio_unitario : base histórica × inflacion_anual acumulada
        - ventas          : volumen_proyectado × precio_unitario_proyectado
        - mo_directa/ind  : costo fijo mensual × variacion_costos acumulada
        - materia_prima   : costo_unitario_hist × variacion_costos × volumen_proyectado
        - gastos_dir/ind  : promedio mensual histórico × inflacion_anual acumulada

    Args:
        ruta_csv:  Ruta al archivo CSV histórico.
        premisas:  Instancia de Premisas. Si None usa valores por defecto.
        metodo:    "auto" | "linear" | "arima" | "sarima" | "prophet"
        periodos:  Meses a proyectar (default 60 = 5 años)

    Returns:
        {
            "info":        dict con meses, score, método usado,
            "pnl_mensual": DataFrame (periodos filas),
            "pnl_anual":   DataFrame (años consolidados),
        }
    """
    if premisas is None:
        premisas = Premisas()

    df_hist = cargar_csv(ruta_csv)
    info = confiabilidad(df_hist)

    metodo_seleccionado = _resolver_metodo(metodo, info)
    info["metodo_usado"] = metodo_seleccionado

    # 1. Forecast: solo volumen
    clase = METODOS_DISPONIBLES[metodo_seleccionado]
    modelo = clase(periodos=periodos)
    modelo.fit(df_hist["volumen"])
    volumen_proy = modelo.predict()

    idx = volumen_proy.index
    año_ref = df_hist.index[-1].year

    # 2. Precio unitario: promedio último año histórico + inflación anual compuesta
    precio_proy = _proy_base_fija(
        df_hist["precio_unitario"], idx, año_ref, premisas.inflacion_anual
    )

    # 3. Ventas = volumen proyectado × precio unitario proyectado
    ventas_proy = volumen_proy * precio_proy

    # 4. MO directa e indirecta: costo fijo mensual + variacion_costos anual
    mo_directa_proy = _proy_base_fija(
        df_hist["mo_directa"], idx, año_ref, premisas.variacion_costos
    )
    mo_indirecta_proy = _proy_base_fija(
        df_hist["mo_indirecta"], idx, año_ref, premisas.variacion_costos
    )

    # 5. Materia prima: costo variable (costo_unitario × volumen proyectado)
    materia_prima_proy = _proy_materia_prima(
        df_hist["materia_prima"], df_hist["volumen"],
        volumen_proy, idx, año_ref, premisas.variacion_costos,
    )

    # 6. Gastos directos e indirectos: promedio mensual histórico + inflación
    gastos_directos_proy = _proy_base_fija(
        df_hist["gastos_directos"], idx, año_ref, premisas.inflacion_anual
    )
    gastos_indirectos_proy = _proy_base_fija(
        df_hist["gastos_indirectos"], idx, año_ref, premisas.inflacion_anual
    )

    df_proyeccion = pd.DataFrame({
        "volumen":           volumen_proy,
        "precio_unitario":   precio_proy,
        "ventas":            ventas_proy,
        "mo_directa":        mo_directa_proy,
        "mo_indirecta":      mo_indirecta_proy,
        "materia_prima":     materia_prima_proy,
        "gastos_directos":   gastos_directos_proy,
        "gastos_indirectos": gastos_indirectos_proy,
    })

    pnl_mensual = construir_pnl_mensual(df_proyeccion)
    pnl_anual   = construir_pnl_anual(pnl_mensual)

    return {
        "info":        info,
        "pnl_mensual": pnl_mensual,
        "pnl_anual":   pnl_anual,
    }


# ─── Helpers de proyección ────────────────────────────────────────────────────

def _base_ultimo_año(serie: pd.Series) -> float:
    """Promedio mensual del último año histórico disponible."""
    ultimo_año = serie.index[-1].year
    return serie[serie.index.year == ultimo_año].mean()


def _factores(idx: pd.DatetimeIndex, año_ref: int, tasa: float) -> pd.Series:
    """Capitalización anual compuesta: (1 + tasa) ^ (año_proyectado - año_ref)."""
    return pd.Series((1 + tasa) ** (idx.year - año_ref), index=idx)


def _proy_base_fija(
    serie: pd.Series, idx: pd.DatetimeIndex, año_ref: int, tasa: float
) -> pd.Series:
    """
    Proyecta un valor con base fija mensual y crecimiento anual compuesto.
    Base = promedio mensual del último año histórico.
    """
    base = _base_ultimo_año(serie)
    return base * _factores(idx, año_ref, tasa)


def _proy_materia_prima(
    mp: pd.Series,
    vol_hist: pd.Series,
    vol_proy: pd.Series,
    idx: pd.DatetimeIndex,
    año_ref: int,
    tasa: float,
) -> pd.Series:
    """
    Materia prima como costo variable:
        costo_unitario_hist = MP_hist / volumen_hist  (promedio último año)
        MP_proyectada = costo_unitario × (1 + tasa)^año × volumen_proyectado
    """
    costo_unitario_hist = mp / vol_hist
    base_cu = _base_ultimo_año(costo_unitario_hist)
    cu_proy = base_cu * _factores(idx, año_ref, tasa)
    return pd.Series(cu_proy.values * vol_proy.values, index=idx)


def _resolver_metodo(metodo: str, info: dict) -> str:
    """Valida el método solicitado y lo resuelve contra disponibles e instalados."""
    teoricos = info["metodos_disponibles"]
    disponibles = [m for m in teoricos if m in METODOS_DISPONIBLES]

    if not disponibles:
        # No debería ocurrir: 'promedio' siempre está disponible
        raise ValueError("No hay métodos de proyección disponibles.")

    if metodo == "auto":
        return disponibles[-1]

    if metodo not in METODOS_DISPONIBLES:
        raise ValueError(
            f"Método '{metodo}' no reconocido. Opciones: {list(METODOS_DISPONIBLES)}"
        )

    if metodo not in disponibles:
        if metodo in teoricos:
            raise ValueError(
                f"Método '{metodo}' requiere más datos históricos. "
                f"Con {info['meses']} meses solo disponibles: {disponibles}"
            )
        raise ValueError(f"Método '{metodo}' no está instalado.")

    return metodo
