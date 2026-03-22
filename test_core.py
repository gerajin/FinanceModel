"""
Prueba rápida del pipeline completo.
Ejecutar desde la raíz del proyecto:
    python test_core.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.forecasting.engine import ejecutar_forecast
from core.forecasting.premisas import Premisas


def main():
    premisas = Premisas(
        inflacion_anual=0.04,      # 4%
        crecimiento_ventas=0.06,   # 6%
        variacion_costos=0.03,     # 3%
    )

    resultado = ejecutar_forecast(
        ruta_csv="sample_data.csv",
        premisas=premisas,
        metodo="auto",   # "auto" | "linear" | "arima" | "sarima"
    )

    info = resultado["info"]
    print(f"\n{'='*50}")
    print(f"  Meses históricos : {info['meses']}")
    print(f"  Confiabilidad    : {info['score']}")
    print(f"  Método usado     : {info['metodo_usado']}")
    print(f"  Métodos disponibles: {info['metodos_disponibles']}")
    print(f"{'='*50}\n")

    print("── P&L ANUAL (5 años) ──────────────────────────")
    print(resultado["pnl_anual"][
        ["ventas", "costo_ventas", "utilidad_bruta", "gastos_operacion", "utilidad_operacion"]
    ].to_string())

    print("\n── P&L MENSUAL (primeros 6 meses) ─────────────")
    print(resultado["pnl_mensual"][
        ["ventas", "utilidad_bruta", "utilidad_operacion"]
    ].head(6).to_string())


if __name__ == "__main__":
    main()
