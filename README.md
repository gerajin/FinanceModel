# FinanceModel – Forecasting Financiero P&L con IA

Aplicación web Django para generar proyecciones del Estado de Resultados (P&L) a partir de datos históricos CSV, con selección automática de modelo estadístico y análisis de IA generado en tiempo real.

Se puede probar en [NexoForecasting](https://forecast.nexocontable.com.mx/forecast/)

---

## Índice

1. [Características](#características)
2. [Arquitectura](#arquitectura)
3. [Requisitos](#requisitos)
4. [Instalación local](#instalación-local)
5. [Configuración (.env)](#configuración-env)
6. [Uso](#uso)
7. [Formato del CSV](#formato-del-csv)
8. [Modelos de proyección](#modelos-de-proyección)
9. [Deploy en producción](#deploy-en-producción)
10. [Estructura del proyecto](#estructura-del-proyecto)

---

## Características

- Proyección del P&L mensual (12 meses) y anual (hasta 5 años) a partir de un CSV histórico
- Selección automática del modelo estadístico según historial disponible
- Cinco modelos disponibles: Promedio, Lineal, ARIMA, SARIMA, Prophet
- Análisis de texto generado por IA vía OpenRouter (streaming en tiempo real)
- Gráficas interactivas: volumen histórico + proyectado, P&L anual con margen operacional
- Tabla P&L mensual transpuesta (conceptos × periodos)
- Dos modos de uso: anónimo (sesión temporal) y registrado (proyectos guardados)
- Descarga CSV de resultados mensual y anual
- Deploy listo para producción con Gunicorn + Whitenoise + PostgreSQL

---

## Arquitectura

```
┌─────────────────────────────────────────────────────┐
│                   Django Web Layer                  │
│  financemodel/  ←  urls, settings, wsgi             │
│  forecast/      ←  views, models, forms, urls       │
│  templates/     ←  base.html, forecast/, partials/  │
└────────────────────┬────────────────────────────────┘
                     │  llama a
┌────────────────────▼────────────────────────────────┐
│              Core de Forecasting (Python puro)      │
│  core/forecasting/                                  │
│  ├── engine.py      ← pipeline principal            │
│  ├── parser.py      ← carga y valida el CSV         │
│  ├── premisas.py    ← parámetros de proyección      │
│  ├── builder.py     ← construye P&L mensual/anual   │
│  └── methods/                                       │
│      ├── average.py ← Promedio                      │
│      ├── linear.py  ← Regresión Lineal              │
│      ├── arima.py   ← ARIMA (pmdarima)              │
│      ├── sarima.py  ← SARIMA estacional             │
│      └── prophet.py ← Prophet (Meta)                │
└─────────────────────────────────────────────────────┘
```

### Flujo de datos

```
CSV histórico
    │
    ▼
parser.cargar_csv()         → DataFrame (DatetimeIndex)
    │
    ▼
engine.ejecutar_forecast()
    ├── Selección de método (auto o manual)
    ├── Proyección de volumen (modelo estadístico)
    └── Cálculo de P&L con premisas:
        ├── Ventas       = volumen_proyectado × precio × (1+inflación)^año
        ├── MO           = base fija × (1+incremento_salarial)^año
        ├── Materia Prima = costo_unit × (1+var_costos)^año × volumen
        └── Gastos       = base × (1+inflación)^año
    │
    ▼
builder.construir_pnl_mensual() → DataFrame mensual
builder.construir_pnl_anual()   → DataFrame anual
    │
    ▼
Vista Django (views.py)
    ├── Gráficas base64 (matplotlib Agg)
    ├── Análisis IA streaming (OpenRouter SSE)
    └── Respuesta HTML o redirect
```

---

## Requisitos

- Python 3.10+
- Ver dependencias completas en `requirements.txt`

Dependencias principales:

| Paquete | Uso |
|---------|-----|
| Django 6.0 | Framework web |
| pandas / numpy | Procesamiento de datos |
| pmdarima | ARIMA / SARIMA automático |
| prophet | Modelo Prophet (Meta) |
| matplotlib | Generación de gráficas |
| gunicorn | Servidor WSGI para producción |
| whitenoise | Archivos estáticos en producción |
| psycopg2-binary | Conector PostgreSQL |
| python-dotenv | Variables de entorno desde `.env` |
| requests | Llamadas a la API de OpenRouter |

---

## Instalación local

```bash
# 1. Clonar el repositorio
git clone https://github.com/gerajin/FinanceModel.git
cd FinanceModel

# 2. Crear y activar entorno virtual
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Crear archivo de configuración
cp .env.example .env   # o crear .env manualmente (ver sección siguiente)

# 5. Aplicar migraciones
python manage.py migrate

# 6. Crear superusuario (opcional)
python manage.py createsuperuser

# 7. Levantar el servidor de desarrollo
python manage.py runserver
```
La aplicación estará disponible en `http://127.0.0.1:8000/forecast/`.

---

## Uso

### Usuario anónimo

1. Visita `/forecast/` → landing informativo
2. Haz clic en **Empezar ahora** → `/forecast/nuevo/`
3. Sube tu CSV histórico y configura las premisas
4. Obtén el P&L proyectado, gráficas y análisis de IA
5. Descarga el resultado en CSV (sesión válida por 1 hora)

### Usuario registrado

1. Regístrate en `/accounts/register/` (gratuito)
2. El navbar te lleva directamente al formulario `/forecast/nuevo/`
3. Los proyectos se guardan automáticamente con nombre
4. Accede al historial en **Mis Proyectos** → `/forecast/projects/`
5. Descarga CSV mensual y anual desde el detalle del proyecto

### Parámetros del formulario

| Campo | Descripción | Valor por defecto |
|-------|-------------|-------------------|
| Nombre del proyecto | Identificador del forecast (solo auth) | — |
| Método de proyección | Auto / Promedio / Lineal / ARIMA / SARIMA / Prophet | Auto |
| Inflación anual (%) | Ajusta precio de venta y gastos operativos | 4% |
| Variación de costos (%) | Ajusta costo de materia prima | 3% |
| Incremento salarial (%) | Ajusta mano de obra directa e indirecta | 5% |
| Archivo CSV | Historial mensual de ventas y costos | — |

---

## Formato del CSV

El archivo debe ser UTF-8, separado por comas, con encabezado en la primera fila:

```csv
fecha,volumen,precio_unitario,materia_prima,mo_directa,mo_indirecta,gastos_directos,gastos_indirectos
2022-01-01,1500,250.00,120000,45000,15000,20000,10000
2022-02-01,1620,250.00,130000,45000,15000,21000,10500
...
```

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `fecha` | YYYY-MM-DD | Primer día del mes (frecuencia mensual) |
| `volumen` | entero | Unidades vendidas |
| `precio_unitario` | decimal | Precio de venta por unidad |
| `materia_prima` | decimal | Costo total de materia prima del mes |
| `mo_directa` | decimal | Mano de obra directa (costo fijo mensual) |
| `mo_indirecta` | decimal | Mano de obra indirecta (costo fijo mensual) |
| `gastos_directos` | decimal | Gastos directos de producción |
| `gastos_indirectos` | decimal | Gastos indirectos / administrativos |

Descarga un CSV de ejemplo desde la app: `/forecast/sample-csv/`

---

## Modelos de proyección

Solo el **volumen** se proyecta estadísticamente. El resto de conceptos del P&L se calculan aplicando las premisas sobre bases históricas.

| Modelo | Mínimo | Selección auto | Cuándo usarlo |
|--------|--------|:--------------:|---------------|
| **Auto** | — | ✓ | Siempre recomendado — elige el mejor disponible |
| Promedio | 3 meses | — | Datos sin tendencia, historial muy corto |
| Lineal | 6 meses | — | Crecimiento o decrecimiento sostenido |
| ARIMA | 24 meses | — | Tendencia sin estacionalidad marcada |
| SARIMA | 24 meses | — | Patrones estacionales (temporadas) |
| Prophet | 24 meses | — | Múltiples estacionalidades y cambios de tendencia |

La selección automática elige el método más avanzado disponible según el número de meses históricos.

---

## Estructura del proyecto

```
FinanceModel/
├── core/
│   └── forecasting/
│       ├── engine.py          # Pipeline principal de forecast
│       ├── parser.py          # Carga y validación del CSV
│       ├── premisas.py        # Dataclass con parámetros de ajuste
│       ├── builder.py         # Construcción del P&L mensual/anual
│       └── methods/
│           ├── base.py        # Clase base abstracta
│           ├── average.py     # Método promedio
│           ├── linear.py      # Regresión lineal
│           ├── arima.py       # ARIMA automático (pmdarima)
│           ├── sarima.py      # SARIMA estacional
│           └── prophet.py     # Prophet (Meta)
├── financemodel/
│   ├── settings.py            # Configuración Django
│   ├── urls.py                # URLs raíz
│   └── wsgi.py                # Entry point WSGI
├── forecast/
│   ├── models.py              # Modelo Proyecto
│   ├── views.py               # Vistas (landing, formulario, resultados, streaming IA)
│   ├── forms.py               # ForecastForm
│   ├── urls.py                # URLs de la app
│   └── admin.py
├── templates/
│   ├── base.html
│   ├── partials/
│   │   ├── _navbar.html
│   │   └── _footer.html
│   ├── registration/
│   │   ├── login.html
│   │   └── register.html
│   └── forecast/
│       ├── upload.html        # Landing page
│       ├── nuevo.html         # Formulario de nuevo forecast
│       ├── result_anon.html   # Resultados usuario anónimo
│       ├── project_detail.html
│       ├── project_list.html
│       └── charts.html
├── static/
│   └── css/
│       └── financemodel.css
├── .env                       # Variables de entorno (no en git)
├── .gitignore
├── gunicorn.conf.py           # Configuración Gunicorn
├── start.sh                   # Script de inicio para producción
├── requirements.txt
├── manage.py
└── sample_data.csv            # CSV de ejemplo para pruebas
```
