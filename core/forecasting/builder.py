import pandas as pd


def construir_pnl_mensual(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensambla el P&L mensual a partir del DataFrame de proyección ajustada.
    
    Estructura:
        Ventas
        (-) Costo de Ventas
              MO Directa
              MO Indirecta
              Materia Prima
        = Utilidad Bruta
        (-) Gastos de Operación
              Gastos Directos
              Gastos Indirectos
        = Utilidad de Operación

    Returns:
        DataFrame con el P&L completo indexado por período.
    """
    pnl = pd.DataFrame(index=df.index)

    pnl["ventas"]            = df.get("ventas", 0)
    pnl["mo_directa"]        = df.get("mo_directa", 0)
    pnl["mo_indirecta"]      = df.get("mo_indirecta", 0)
    pnl["materia_prima"]     = df.get("materia_prima", 0)
    pnl["gastos_directos"]   = df.get("gastos_directos", 0)
    pnl["gastos_indirectos"] = df.get("gastos_indirectos", 0)

    pnl["costo_ventas"]       = pnl["mo_directa"] + pnl["mo_indirecta"] + pnl["materia_prima"]
    pnl["utilidad_bruta"]     = pnl["ventas"] - pnl["costo_ventas"]
    pnl["gastos_operacion"]   = pnl["gastos_directos"] + pnl["gastos_indirectos"]
    pnl["utilidad_operacion"] = pnl["utilidad_bruta"] - pnl["gastos_operacion"]

    return pnl


def construir_pnl_anual(pnl_mensual: pd.DataFrame) -> pd.DataFrame:
    """
    Consolida el P&L mensual a vista anual (suma de los 12 meses por año).

    Returns:
        DataFrame con 5 filas (una por año) y las mismas columnas.
    """
    return pnl_mensual.resample("YE").sum()
