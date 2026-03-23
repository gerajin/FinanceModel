from dataclasses import dataclass


@dataclass
class Premisas:
    """
    Parámetros globales de ajuste para la proyección.
    Todos los porcentajes en decimal (ej: 5% → 0.05).

    - inflacion_anual:     ajusta precio_unitario, gastos_directos, gastos_indirectos
    - variacion_costos:    ajusta costo unitario de materia_prima
    - incremento_salarial: ajusta mo_directa y mo_indirecta (mano de obra)
    """
    inflacion_anual: float = 0.04
    variacion_costos: float = 0.03
    incremento_salarial: float = 0.05
