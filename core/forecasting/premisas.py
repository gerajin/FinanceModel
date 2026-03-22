import pandas as pd
from dataclasses import dataclass, field


@dataclass
class Premisas:
    """
    Parámetros globales que se aplican sobre la proyección base.
    Todos los porcentajes en decimal (ej: 5% → 0.05).
    """
    inflacion_anual: float = 0.04        # aplica a costos
    crecimiento_ventas: float = 0.05     # aplica solo a ventas
    variacion_costos: float = 0.03       # aplica a MO y MP
    # Extender aquí con más drivers según necesidad


# Qué premisa aplica a cada concepto
MAPA_PREMISAS = {
    "ventas":           "crecimiento_ventas",
    "mo_directa":       "variacion_costos",
    "mo_indirecta":     "variacion_costos",
    "materia_prima":    "variacion_costos",
    "gastos_directos":  "inflacion_anual",
    "gastos_indirectos":"inflacion_anual",
}


def aplicar_premisas(df_proyeccion: pd.DataFrame, premisas: Premisas) -> pd.DataFrame:
    """
    Ajusta el DataFrame de proyección mensual aplicando las premisas globales.
    
    El ajuste es acumulativo por año:
        mes_ajustado = mes_base * (1 + tasa_anual) ^ (año_relativo)
    
    Args:
        df_proyeccion: DataFrame con índice DatetimeIndex y columnas = conceptos.
        premisas: instancia de Premisas con las tasas configuradas.
    
    Returns:
        DataFrame con montos ajustados.
    """
    df = df_proyeccion.copy()
    año_base = df.index[0].year

    for concepto, attr_premisa in MAPA_PREMISAS.items():
        if concepto not in df.columns:
            continue

        tasa = getattr(premisas, attr_premisa)

        años_relativos = df.index.year - año_base
        factores = (1 + tasa) ** años_relativos

        df[concepto] = df[concepto] * factores

    return df
