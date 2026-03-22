import pandas as pd

from .parser import cargar_csv, confiabilidad, CONCEPTOS_ESPERADOS
from .premisas import Premisas, aplicar_premisas
from .builder import construir_pnl_mensual, construir_pnl_anual
from .methods.linear import LinearMethod
from .methods.arima import ARIMAMethod
from .methods.sarima import SARIMAMethod


METODOS_DISPONIBLES = {
    "linear": LinearMethod,
    "arima":  ARIMAMethod,
    "sarima": SARIMAMethod,
}


def ejecutar_forecast(
    ruta_csv: str,
    premisas: Premisas = None,
    metodo: str = "auto",
    periodos: int = 60,
) -> dict:
    """
    Pipeline completo: CSV → P&L proyectado mensual y anual.

    Args:
        ruta_csv:  Ruta al archivo CSV histórico.
        premisas:  Instancia de Premisas. Si None usa valores por defecto.
        metodo:    "auto" | "linear" | "arima" | "sarima"
        periodos:  Meses a proyectar (default 60 = 5 años)

    Returns:
        {
            "info":        dict con meses, score, método usado,
            "pnl_mensual": DataFrame (60 filas),
            "pnl_anual":   DataFrame (5 filas),
        }
    """
    if premisas is None:
        premisas = Premisas()

    # 1. Cargar y validar CSV
    df_historico = cargar_csv(ruta_csv)
    info = confiabilidad(df_historico)

    # 2. Seleccionar método
    metodo_seleccionado = _resolver_metodo(metodo, info)
    info["metodo_usado"] = metodo_seleccionado

    # 3. Proyectar concepto por concepto
    clase_metodo = METODOS_DISPONIBLES[metodo_seleccionado]
    proyecciones = {}

    for concepto in CONCEPTOS_ESPERADOS:
        if concepto not in df_historico.columns:
            continue

        serie = df_historico[concepto]
        modelo = clase_metodo(periodos=periodos)
        modelo.fit(serie)
        proyecciones[concepto] = modelo.predict()

    df_proyeccion = pd.DataFrame(proyecciones)

    # 4. Aplicar premisas globales
    df_ajustado = aplicar_premisas(df_proyeccion, premisas)

    # 5. Ensamblar P&L
    pnl_mensual = construir_pnl_mensual(df_ajustado)
    pnl_anual   = construir_pnl_anual(pnl_mensual)

    return {
        "info":        info,
        "pnl_mensual": pnl_mensual,
        "pnl_anual":   pnl_anual,
    }


def _resolver_metodo(metodo: str, info: dict) -> str:
    """Valida y resuelve el método a usar."""
    disponibles = info["metodos_disponibles"]

    if not disponibles:
        raise ValueError(
            f"No hay suficientes datos históricos ({info['meses']} meses). "
            f"Mínimo requerido: 12 meses."
        )

    if metodo == "auto":
        return info["recomendado"]

    if metodo not in METODOS_DISPONIBLES:
        raise ValueError(f"Método '{metodo}' no reconocido. Opciones: {list(METODOS_DISPONIBLES)}")

    if metodo not in disponibles:
        raise ValueError(
            f"Método '{metodo}' requiere más datos históricos. "
            f"Con {info['meses']} meses solo están disponibles: {disponibles}"
        )

    return metodo
