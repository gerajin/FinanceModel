import pandas as pd
from pathlib import Path


# Columnas esperadas en el CSV (ajustar según necesidad)
CONCEPTOS_ESPERADOS = [
    "ventas",
    "mo_directa",
    "mo_indirecta",
    "materia_prima",
    "gastos_directos",
    "gastos_indirectos",
]

MESES_MINIMOS = 12   # mínimo absoluto
MESES_RECOMENDADOS = 24  # para SARIMA / estacionalidad


def cargar_csv(ruta: str | Path) -> pd.DataFrame:
    """
    Lee el CSV y devuelve un DataFrame limpio indexado por fecha.

    Formato esperado del CSV:
        periodo,ventas,mo_directa,mo_indirecta,materia_prima,...
        2023-01,150000,30000,10000,40000,...
        2023-02,155000,31000,10500,41000,...

    Returns:
        DataFrame con índice DatetimeIndex (frecuencia mensual) y columnas numéricas.

    Raises:
        ValueError: si faltan columnas o hay menos meses que el mínimo.
    """
    df = pd.read_csv(ruta, parse_dates=["periodo"])
    df = df.set_index("periodo")
    df.index = pd.DatetimeIndex(df.index).to_period("M").to_timestamp("M")
    df = df.sort_index()

    _validar_columnas(df)
    _validar_periodos(df)
    _validar_sin_nulos(df)

    return df.astype(float)


def _validar_columnas(df: pd.DataFrame) -> None:
    faltantes = [c for c in CONCEPTOS_ESPERADOS if c not in df.columns]
    if faltantes:
        raise ValueError(f"Columnas faltantes en el CSV: {faltantes}")


def _validar_periodos(df: pd.DataFrame) -> None:
    n = len(df)
    if n < MESES_MINIMOS:
        raise ValueError(
            f"El CSV tiene {n} meses. Mínimo requerido: {MESES_MINIMOS}."
        )


def _validar_sin_nulos(df: pd.DataFrame) -> None:
    nulos = df.isnull().sum()
    con_nulos = nulos[nulos > 0]
    if not con_nulos.empty:
        raise ValueError(f"Hay valores nulos en: {con_nulos.to_dict()}")


def confiabilidad(df: pd.DataFrame) -> dict:
    """
    Evalúa qué métodos están disponibles según los meses históricos.
    
    Returns:
        dict con score y métodos habilitados.
    """
    n = len(df)

    if n >= MESES_RECOMENDADOS:
        score = "alta"
        metodos = ["linear", "arima", "sarima"]
    elif n >= MESES_MINIMOS:
        score = "media"
        metodos = ["linear", "arima"]
    else:
        score = "baja"
        metodos = []

    return {
        "meses": n,
        "score": score,
        "metodos_disponibles": metodos,
        "recomendado": metodos[-1] if metodos else None,
    }
