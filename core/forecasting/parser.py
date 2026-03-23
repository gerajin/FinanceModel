import re
import pandas as pd
from pathlib import Path


# Columnas requeridas en el CSV de entrada
CONCEPTOS_ESPERADOS = [
    "volumen",
    "precio_unitario",
    "mo_directa",
    "mo_indirecta",
    "materia_prima",
    "gastos_directos",
    "gastos_indirectos",
]

# ── Umbrales de periodos ──────────────────────────────────────────────────────
MESES_ABSOLUTO_MINIMO = 3   # mínimo para calcular un promedio significativo
MESES_MINIMOS         = 12  # umbral para habilitar regresión lineal
MESES_ARIMA           = 24  # umbral para habilitar ARIMA (≥ 2 ciclos anuales)
MESES_SARIMA          = 24  # umbral para habilitar SARIMA (2 ciclos son suficientes con m=12)

# ── Límites de seguridad del CSV ─────────────────────────────────────────────
MAX_BYTES        = 2 * 1024 * 1024   # 2 MB
MAX_FILAS        = 600               # 50 años mensuales; más es irrazonable
MAX_COLUMNAS     = 30                # holgura suficiente para columnas extra
_RE_NOMBRE_COL   = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")  # sin inyección


def cargar_csv(ruta: str | Path) -> pd.DataFrame:
    """
    Lee el CSV y devuelve un DataFrame limpio indexado por fecha.

    Formato esperado del CSV:
        periodo,volumen,precio_unitario,mo_directa,mo_indirecta,materia_prima,...
        2023-01,1000,150.00,30000,10000,40000,...

    Nota: 'ventas' no es columna de entrada — se deriva como volumen × precio_unitario.

    Returns:
        DataFrame con índice DatetimeIndex (frecuencia mensual) y columnas numéricas.

    Raises:
        ValueError: validaciones de seguridad, estructura o datos.
    """
    ruta = Path(ruta)

    _validar_archivo(ruta)

    df = pd.read_csv(ruta, parse_dates=["periodo"])
    df = df.set_index("periodo")
    df.index = pd.DatetimeIndex(df.index).to_period("M").to_timestamp()
    df = df.sort_index()

    # Eliminar columnas vacías (artefacto de CSVs con coma final)
    df = df.loc[:, df.columns.str.strip() != ""]

    _validar_dimensiones(df)
    _validar_nombres_columnas(df)
    _validar_columnas(df)
    _validar_periodos(df)
    _validar_sin_nulos(df)
    _validar_valores_positivos(df)

    return df.astype(float)


# ── Validaciones de seguridad ─────────────────────────────────────────────────

def _validar_archivo(ruta: Path) -> None:
    if not ruta.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {ruta}")

    if ruta.suffix.lower() != ".csv":
        raise ValueError(f"Solo se aceptan archivos .csv (recibido: '{ruta.suffix}')")

    tam = ruta.stat().st_size
    if tam > MAX_BYTES:
        raise ValueError(
            f"El archivo pesa {tam / 1024 / 1024:.1f} MB. "
            f"Máximo permitido: {MAX_BYTES // 1024 // 1024} MB."
        )

    if tam == 0:
        raise ValueError("El archivo está vacío.")


def _validar_dimensiones(df: pd.DataFrame) -> None:
    if len(df) > MAX_FILAS:
        raise ValueError(
            f"El CSV tiene {len(df)} filas. Máximo permitido: {MAX_FILAS} "
            f"({MAX_FILAS // 12} años mensualizados)."
        )

    if len(df.columns) > MAX_COLUMNAS:
        raise ValueError(
            f"El CSV tiene {len(df.columns)} columnas. Máximo permitido: {MAX_COLUMNAS}."
        )


def _validar_nombres_columnas(df: pd.DataFrame) -> None:
    invalidos = [c for c in df.columns if not _RE_NOMBRE_COL.match(str(c))]
    if invalidos:
        raise ValueError(
            f"Nombres de columna inválidos (solo letras, números y guión bajo): {invalidos}"
        )


# ── Validaciones de estructura y datos ───────────────────────────────────────

def _validar_columnas(df: pd.DataFrame) -> None:
    faltantes = [c for c in CONCEPTOS_ESPERADOS if c not in df.columns]
    if faltantes:
        raise ValueError(f"Columnas faltantes en el CSV: {faltantes}")


def _validar_periodos(df: pd.DataFrame) -> None:
    n = len(df)
    if n < MESES_ABSOLUTO_MINIMO:
        raise ValueError(
            f"El CSV tiene {n} meses. Mínimo requerido: {MESES_ABSOLUTO_MINIMO} "
            f"(con menos de {MESES_MINIMOS} se usará proyección por promedio simple)."
        )


def _validar_sin_nulos(df: pd.DataFrame) -> None:
    nulos = df.isnull().sum()
    con_nulos = nulos[nulos > 0]
    if not con_nulos.empty:
        raise ValueError(f"Hay valores nulos en: {con_nulos.to_dict()}")


def _validar_valores_positivos(df: pd.DataFrame) -> None:
    """Volumen y precio_unitario deben ser estrictamente positivos."""
    for col in ("volumen", "precio_unitario"):
        if col in df.columns:
            n_neg = (df[col] <= 0).sum()
            if n_neg:
                raise ValueError(
                    f"'{col}' contiene {n_neg} valores <= 0. "
                    "Volumen y precio unitario deben ser positivos."
                )


# ── Evaluación de confiabilidad ───────────────────────────────────────────────

def confiabilidad(df: pd.DataFrame) -> dict:
    """
    Evalúa qué métodos están disponibles según los meses históricos.

    Umbrales:
        ≥ 24 meses → alta        (promedio, linear, arima, sarima, prophet)
        ≥ 12 meses → baja        (promedio, linear)
        <  12 meses → insuficiente (promedio — proyección por promedio + premisas)

    Returns:
        dict con meses, score y métodos disponibles.
    """
    n = len(df)

    if n >= MESES_SARIMA:
        score = "alta"
        metodos = ["promedio", "linear", "arima", "sarima", "prophet"]
    elif n >= MESES_ARIMA:
        score = "media"
        metodos = ["promedio", "linear", "arima"]
    elif n >= MESES_MINIMOS:
        score = "baja"
        metodos = ["promedio", "linear"]
    else:
        score = "insuficiente"
        metodos = ["promedio"]   # fallback: proyección por promedio + premisas

    return {
        "meses": n,
        "score": score,
        "metodos_disponibles": metodos,
        "recomendado": metodos[-1] if metodos else None,
    }
