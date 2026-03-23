import pandas as pd


def construir_pnl_mensual(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensambla el P&L mensual a partir del DataFrame de proyección.

    Estructura:
        Volumen / Precio unitario (referencia)
        Ventas  = volumen × precio_unitario
        (-) Costo de Ventas
              MO Directa      (costo fijo)
              Gastos Directos (promedio + inflación)
              Materia Prima   (costo variable)
        = Utilidad Bruta
        (-) Gastos de Operación
              MO Indirecta      (costo fijo)
              Gastos Indirectos (promedio + inflación)
        = Utilidad de Operación

    Returns:
        DataFrame con el P&L completo indexado por período.
    """
    pnl = pd.DataFrame(index=df.index)

    pnl["volumen"]           = df.get("volumen", 0)
    pnl["precio_unitario"]   = df.get("precio_unitario", 0)
    pnl["ventas"]            = df.get("ventas", 0)
    pnl["mo_directa"]        = df.get("mo_directa", 0)
    pnl["mo_indirecta"]      = df.get("mo_indirecta", 0)
    pnl["materia_prima"]     = df.get("materia_prima", 0)
    pnl["gastos_directos"]   = df.get("gastos_directos", 0)
    pnl["gastos_indirectos"] = df.get("gastos_indirectos", 0)

    pnl["costo_ventas"]       = pnl["mo_directa"] + pnl["gastos_directos"] + pnl["materia_prima"]
    pnl["utilidad_bruta"]     = pnl["ventas"] - pnl["costo_ventas"]
    pnl["gastos_operacion"]   = pnl["mo_indirecta"] + pnl["gastos_indirectos"]
    pnl["utilidad_operacion"] = pnl["utilidad_bruta"] - pnl["gastos_operacion"]

    return pnl


def construir_pnl_anual(pnl_mensual: pd.DataFrame) -> pd.DataFrame:
    """
    Consolida el P&L mensual a vista anual.

    Suma la mayoría de columnas; para precio_unitario usa el precio efectivo anual
    calculado como ventas_anuales / volumen_anual.

    Returns:
        DataFrame con una fila por año.
    """
    cols_suma = [c for c in pnl_mensual.columns if c != "precio_unitario"]
    annual = pnl_mensual[cols_suma].resample("YE").sum()

    if "precio_unitario" in pnl_mensual.columns:
        annual["precio_unitario"] = annual["ventas"] / annual["volumen"]

    return annual
