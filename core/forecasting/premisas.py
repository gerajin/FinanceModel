from dataclasses import dataclass


@dataclass
class Premisas:
    """
    Parámetros globales de ajuste para la proyección.
    Todos los porcentajes en decimal (ej: 5% → 0.05).

    - inflacion_anual:  ajusta precio_unitario, gastos_directos, gastos_indirectos
    - variacion_costos: ajusta costo unitario de materia_prima, mo_directa, mo_indirecta
    """
    inflacion_anual: float = 0.04     # aplica a precio_unitario y gastos
    variacion_costos: float = 0.03    # aplica a MO (costo fijo) y materia prima (costo unitario)
