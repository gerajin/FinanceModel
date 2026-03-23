import base64
import io
import os
import tempfile
import uuid
from contextlib import contextmanager

import json
import requests

import matplotlib
matplotlib.use('Agg')  # debe ir antes de importar pyplot
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.forecasting.engine import ejecutar_forecast
from core.forecasting.parser import cargar_csv
from core.forecasting.premisas import Premisas

from .forms import ForecastForm
from .models import Proyecto


# Orden, etiquetas, subtotal y formato de filas en la tabla P&L
# fmt: 'int' = sin decimales | 'float' = 2 decimales | 'money' = $ 2 decimales
CONCEPTOS_TABLA = [
    ('volumen',           'Volumen',               False, 'int'),
    ('precio_unitario',   'Precio Unitario (PU)',  False, 'float'),
    ('ventas',            'Ventas',                False, 'money'),
    ('mo_directa',        'MO Directa',            False, 'money'),
    ('materia_prima',     'Materia Prima',         False, 'money'),
    ('gastos_directos',   'Gastos Directos',       False, 'money'),
    ('utilidad_bruta',    'Utilidad Bruta',        True,  'money'),
    ('mo_indirecta',      'MO Indirecta',          False, 'money'),
    ('gastos_indirectos', 'Gastos Indirectos',     False, 'money'),
    ('utilidad_operacion','Utilidad de Operación', True,  'money'),
]


# ─── Helpers de datos ─────────────────────────────────────────────────────────

@contextmanager
def _csv_temporal(uploaded_file):
    fd, path = tempfile.mkstemp(suffix='.csv')
    try:
        with os.fdopen(fd, 'wb') as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)
        yield path
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _run_forecast(path, inflacion, variacion, metodo):
    """Ejecuta el forecast y retorna (resultado, hist_df)."""
    premisas = Premisas(inflacion_anual=inflacion, variacion_costos=variacion)
    resultado = ejecutar_forecast(ruta_csv=path, premisas=premisas, metodo=metodo)
    hist_df   = cargar_csv(path)
    return resultado, hist_df


def _df_a_dict(df):
    return {
        'index':   [str(i)[:10] for i in df.index],
        'columns': list(df.columns),
        'data':    [
            [None if pd.isna(v) else round(float(v), 4) for v in row]
            for row in df.values.tolist()
        ],
    }


def _dict_a_df(data):
    if not data or not data.get('index'):
        return pd.DataFrame()
    df = pd.DataFrame(
        data['data'],
        index=pd.to_datetime(data['index']),
        columns=data['columns'],
    )
    return df.astype(float, errors='ignore')


def _pnl_para_tabla(df, n_meses=12):
    """Filas = conceptos, columnas = meses en formato mm-aaaa."""
    df_n = df.head(n_meses)
    headers = [pd.Timestamp(i).strftime('%m-%Y') for i in df_n.index]
    rows = []
    for col, label, is_total, fmt in CONCEPTOS_TABLA:
        if col in df_n.columns:
            values = [
                None if pd.isna(v) else round(float(v), 2)
                for v in df_n[col].values
            ]
            rows.append({'label': label, 'values': values, 'is_total': is_total, 'fmt': fmt})
    return {'headers': headers, 'rows': rows}


def _pnl_anual_para_tabla(df):
    """Filas = conceptos, columnas = años."""
    headers = [pd.Timestamp(i).strftime('%Y') for i in df.index]
    rows = []
    for col, label, is_total, fmt in CONCEPTOS_TABLA:
        if col in df.columns:
            values = [
                None if pd.isna(v) else round(float(v), 2)
                for v in df[col].values
            ]
            rows.append({'label': label, 'values': values, 'is_total': is_total, 'fmt': fmt})
    return {'headers': headers, 'rows': rows}


def _construir_hist_pnl(hist_df):
    """Reconstruye columnas derivadas del P&L a partir del CSV histórico."""
    pnl = hist_df.copy().astype(float)
    pnl['ventas']             = pnl['volumen'] * pnl['precio_unitario']
    pnl['costo_ventas']       = pnl['mo_directa'] + pnl['gastos_directos'] + pnl['materia_prima']
    pnl['utilidad_bruta']     = pnl['ventas'] - pnl['costo_ventas']
    pnl['gastos_operacion']   = pnl['mo_indirecta'] + pnl['gastos_indirectos']
    pnl['utilidad_operacion'] = pnl['utilidad_bruta'] - pnl['gastos_operacion']
    return pnl


# ─── Helpers de gráficas ──────────────────────────────────────────────────────

def _fig_to_b64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=96, bbox_inches='tight')
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode('ascii')
    plt.close(fig)
    return encoded


def _fmt_eje_fecha(ax):
    """Formatea el eje X como mm-aaaa."""
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%Y'))
    ax.tick_params(axis='x', rotation=45)


def _make_charts_b64(pnl_mensual_df, hist_df=None, pnl_anual_df=None):
    """
    Genera 2 gráficas PNG como base64:
    - 'vol': últimos 24 meses históricos (sólido) + 12 meses proyectados (punteado)
    - 'pnl': barras anuales (hasta 5 años hist + 5 proyectados) + eje secundario % margen
    """
    charts = {}

    # ── Segmento histórico mensual ────────────────────────────────────────────
    hist_pnl_mensual = None
    hist_pnl_anual   = None
    if hist_df is not None and len(hist_df) > 0:
        try:
            hp = _construir_hist_pnl(hist_df)
            hist_pnl_mensual = hp.tail(24)
            hist_pnl_anual   = hp[['ventas', 'utilidad_operacion']].resample('YE').sum().tail(5)
        except Exception:
            pass

    proj_mensual = pnl_mensual_df.head(12)

    # ── Gráfica 1: Volumen mensual ────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(10, 4))

    if hist_pnl_mensual is not None and len(hist_pnl_mensual) > 0:
        ax.plot(hist_pnl_mensual.index, hist_pnl_mensual['volumen'],
                color='#1565C0', linewidth=2.5, label='Histórico')
        ax.axvline(x=proj_mensual.index[0], color='#757575', linestyle=':', linewidth=1.5, alpha=0.8)

    ax.plot(proj_mensual.index, proj_mensual['volumen'],
            color='#42A5F5', linewidth=2.5, linestyle='--', label='Proyectado')

    ax.set_title('Volumen Mensual – Histórico (últ. 24 m.) + Proyección Año 1', fontsize=11)
    ax.set_ylabel('Unidades')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    _fmt_eje_fecha(ax)
    fig.tight_layout()
    charts['vol'] = _fig_to_b64(fig)

    # ── Gráfica 2: P&L anual (barras + % margen) ──────────────────────────────
    # Preparar datos anuales proyectados
    proj_anual = None
    if pnl_anual_df is not None and len(pnl_anual_df) > 0:
        cols_ok = [c for c in ('ventas', 'utilidad_operacion') if c in pnl_anual_df.columns]
        if cols_ok:
            proj_anual = pnl_anual_df[cols_ok].head(5)

    n_hist = len(hist_pnl_anual) if hist_pnl_anual is not None else 0
    n_proj = len(proj_anual)     if proj_anual   is not None else 0
    total  = n_hist + n_proj

    fig, ax = plt.subplots(figsize=(10, 4))
    ax2 = ax.twinx()

    if total > 0:
        bar_w  = 0.35
        x_all  = np.arange(total)

        # Barras históricas
        if n_hist > 0:
            x_h = x_all[:n_hist]
            ax.bar(x_h - bar_w / 2, hist_pnl_anual['ventas'],
                   bar_w, color='#1565C0', label='Ventas (hist)', alpha=0.85)
            ax.bar(x_h + bar_w / 2, hist_pnl_anual['utilidad_operacion'],
                   bar_w, color='#2E7D32', label='Ut. Op. (hist)', alpha=0.85)

        # Barras proyectadas
        if n_proj > 0:
            x_p = x_all[n_hist:]
            ax.bar(x_p - bar_w / 2, proj_anual['ventas'],
                   bar_w, color='#42A5F5', label='Ventas (proy)', alpha=0.85)
            ax.bar(x_p + bar_w / 2, proj_anual['utilidad_operacion'],
                   bar_w, color='#66BB6A', label='Ut. Op. (proy)', alpha=0.85)

        # Separador hist / proy
        if n_hist > 0 and n_proj > 0:
            ax.axvline(x=n_hist - 0.5, color='#757575', linestyle=':', linewidth=1.5, alpha=0.8)

        # % Margen en eje secundario
        pct_vals = []
        if n_hist > 0:
            pct_vals += [
                u / v * 100 if v != 0 else 0
                for u, v in zip(hist_pnl_anual['utilidad_operacion'], hist_pnl_anual['ventas'])
            ]
        if n_proj > 0:
            pct_vals += [
                u / v * 100 if v != 0 else 0
                for u, v in zip(proj_anual['utilidad_operacion'], proj_anual['ventas'])
            ]
        ax2.plot(x_all, pct_vals, 'o:', color='#E65100', linewidth=1.8,
                 markersize=7, label='% Margen Op.')
        ax2.set_ylabel('% Margen Operacional', color='#E65100')
        ax2.tick_params(axis='y', labelcolor='#E65100')
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v:.1f}%'))

        # Etiquetas del eje X (años)
        years_h = [pd.Timestamp(i).strftime('%Y') for i in hist_pnl_anual.index] if n_hist > 0 else []
        years_p = [pd.Timestamp(i).strftime('%Y') for i in proj_anual.index]     if n_proj > 0 else []
        ax.set_xticks(x_all)
        ax.set_xticklabels(years_h + years_p)
    else:
        # Fallback: líneas mensuales si no hay datos anuales
        ax.plot(proj_mensual.index, proj_mensual['ventas'],
                color='#42A5F5', linewidth=2.5, label='Ventas')
        if 'utilidad_operacion' in proj_mensual.columns:
            ax.plot(proj_mensual.index, proj_mensual['utilidad_operacion'],
                    color='#66BB6A', linewidth=2.5, label='Ut. Operación')
        _fmt_eje_fecha(ax)

    ax.set_title('P&L Anual – Histórico + Proyectado', fontsize=11)
    ax.set_ylabel('Monto ($)')
    ax.grid(True, alpha=0.3, axis='y')

    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=8)

    fig.tight_layout()
    charts['pnl'] = _fig_to_b64(fig)

    return charts


# ─── Análisis de IA ───────────────────────────────────────────────────────────

def _generar_analisis_ia(info: dict, pnl_anual_df) -> str:
    """
    Llama a OpenRouter (modelo gratuito) para generar un análisis breve del forecast.
    Retorna el texto del análisis, o cadena vacía si falla o no hay clave configurada.
    """
    import traceback
    from django.conf import settings

    # ── DEBUG 1: clave ────────────────────────────────────────────────────────
    api_key = getattr(settings, 'OPENROUTER_API_KEY', '').strip()
    print(f"\n[IA-DEBUG] ── Inicio _generar_analisis_ia ──")
    print(f"[IA-DEBUG] API key cargada: {'SÍ' if api_key else 'NO (vacía)'}")
    if api_key:
        print(f"[IA-DEBUG] Key preview: {api_key[:12]}...{api_key[-6:]}  (len={len(api_key)})")
    else:
        print("[IA-DEBUG] ABORTANDO: no hay API key en settings.OPENROUTER_API_KEY")
        return ''

    metodo = info.get('metodo_usado', 'desconocido').upper()
    meses  = info.get('meses', 0)

    # ── DEBUG 2: datos del P&L ────────────────────────────────────────────────
    print(f"[IA-DEBUG] Método={metodo}  Meses históricos={meses}")
    print(f"[IA-DEBUG] pnl_anual_df type={type(pnl_anual_df)}  "
          f"empty={pnl_anual_df is None or (hasattr(pnl_anual_df, 'empty') and pnl_anual_df.empty)}")

    lineas = []
    if pnl_anual_df is not None and not pnl_anual_df.empty:
        for fecha, fila in pnl_anual_df.iterrows():
            año     = pd.Timestamp(fecha).strftime('%Y')
            ventas  = float(fila['ventas'])             if 'ventas'             in pnl_anual_df.columns else 0.0
            util_op = float(fila['utilidad_operacion']) if 'utilidad_operacion' in pnl_anual_df.columns else 0.0
            margen  = round(util_op / ventas * 100, 1) if ventas else 0
            lineas.append(f"  {año}: Ventas={ventas:,.0f}  Ut.Op={util_op:,.0f}  Margen={margen}%")

    resumen_pnl = '\n'.join(lineas) if lineas else 'No disponible'
    print(f"[IA-DEBUG] Resumen P&L:\n{resumen_pnl}")

    prompt = (
        f"Eres un analista financiero conciso. Se generó un pronóstico con los siguientes datos:\n"
        f"- Método de proyección: {metodo}\n"
        f"- Meses de historial disponibles: {meses}\n"
        f"- P&L proyectado anual:\n{resumen_pnl}\n\n"
        f"Responde en español con tres puntos usando viñetas (•), sin introducción ni cierre:\n"
        f"• Análisis de las proyecciones: tendencia de ventas, solidez del margen y observaciones clave (máx 3 oraciones).\n"
        f"• Explicación del método {metodo}: qué es y por qué aplica con {meses} meses de historial (máx 2 oraciones).\n"
        f"• Recomendación o punto de atención para la dirección del negocio (1 oración)."
    )

    payload = {
        "model": "openrouter/free",
        "messages": [{"role": "user", "content": prompt}],
    }

    # ── DEBUG 3: request ──────────────────────────────────────────────────────
    print(f"[IA-DEBUG] Enviando POST a OpenRouter  modelo={payload['model']}")
    print(f"[IA-DEBUG] Prompt ({len(prompt)} chars): {prompt[:200]}...")

    try:
        resp = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            data=json.dumps(payload),
            timeout=30,
        )

        # ── DEBUG 4: respuesta ────────────────────────────────────────────────
        print(f"[IA-DEBUG] HTTP status: {resp.status_code}")
        print(f"[IA-DEBUG] Response headers: {dict(resp.headers)}")
        print(f"[IA-DEBUG] Response body (500 chars): {resp.text[:500]}")

        resp.raise_for_status()
        data = resp.json()

        # ── DEBUG 5: contenido extraído ───────────────────────────────────────
        choices = data.get('choices', [])
        print(f"[IA-DEBUG] choices count: {len(choices)}")
        if choices:
            msg = choices[0].get('message', {})
            print(f"[IA-DEBUG] message keys: {list(msg.keys())}")
            content = msg.get('content', '') or ''
            print(f"[IA-DEBUG] content ({len(content)} chars): {content[:300]}")
            print(f"[IA-DEBUG] ── Fin OK ──\n")
            return content.strip()
        else:
            print(f"[IA-DEBUG] ERROR: 'choices' vacío. Full response: {data}")
            return ''

    except requests.exceptions.Timeout:
        print(f"[IA-DEBUG] ERROR: Timeout tras 30 s")
        return ''
    except requests.exceptions.HTTPError as e:
        print(f"[IA-DEBUG] ERROR HTTP: {e}  |  body: {resp.text[:500]}")
        return ''
    except Exception as e:
        print(f"[IA-DEBUG] ERROR inesperado: {type(e).__name__}: {e}")
        print(traceback.format_exc())
        return ''


# ─── Vistas ───────────────────────────────────────────────────────────────────

def forecast_upload(request):
    form = ForecastForm(user=request.user)

    if request.method == 'POST':
        form = ForecastForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            csv_file  = form.cleaned_data['csv_file']
            inflacion = form.cleaned_data['inflacion_anual']
            variacion = form.cleaned_data['variacion_costos']
            metodo    = form.cleaned_data.get('metodo', 'auto') or 'auto'

            try:
                with _csv_temporal(csv_file) as path:
                    resultado, hist_df = _run_forecast(path, inflacion, variacion, metodo)
            except (ValueError, FileNotFoundError) as e:
                form.add_error('csv_file', str(e))
                return render(request, 'forecast/upload.html', {'form': form})
            except Exception as e:
                messages.error(request, f'Error inesperado: {e}')
                return render(request, 'forecast/upload.html', {'form': form})

            info        = resultado['info']
            pnl_mensual = resultado['pnl_mensual']
            pnl_anual   = resultado['pnl_anual']
            hist_24     = hist_df.tail(24)

            # Análisis de IA (puede tardar; falla silenciosamente si no hay clave)
            analisis_ia = _generar_analisis_ia(info, pnl_anual)
            print(f"[IA-DEBUG] analisis_ia resultado: {repr(analisis_ia[:80]) if analisis_ia else 'VACÍO'}")

            if request.user.is_authenticated:
                nombre = form.cleaned_data.get('nombre', 'Proyecto sin nombre')
                proyecto = Proyecto.objects.create(
                    usuario             = request.user,
                    nombre              = nombre,
                    metodo_solicitado   = metodo,
                    metodo_usado        = info.get('metodo_usado', metodo),
                    inflacion_anual     = inflacion,
                    variacion_costos    = variacion,
                    meses_historicos    = info.get('meses', 0),
                    score_confiabilidad = info.get('score', ''),
                    pnl_mensual_json    = _df_a_dict(pnl_mensual),
                    pnl_anual_json      = _df_a_dict(pnl_anual),
                    historial_json      = _df_a_dict(hist_24),
                    analisis_ia         = analisis_ia,
                )
                messages.success(request, f'Proyecto "{nombre}" guardado exitosamente.')
                return redirect('forecast:project_detail', pk=proyecto.pk)
            else:
                token = uuid.uuid4()
                request.session[f'forecast_{token}'] = {
                    'info':        info,
                    'pnl_mensual': _df_a_dict(pnl_mensual),
                    'pnl_anual':   _df_a_dict(pnl_anual),
                    'historial':   _df_a_dict(hist_24),
                    'analisis_ia': analisis_ia,
                }
                return redirect('forecast:result_anon', token=token)

    return render(request, 'forecast/upload.html', {'form': form})


def result_anon(request, token):
    key = f'forecast_{token}'
    data = request.session.get(key)
    if data is None:
        messages.warning(request, 'Resultado no encontrado o sesión expirada.')
        return redirect('forecast:upload')

    pnl_mensual_df = _dict_a_df(data['pnl_mensual'])
    pnl_anual_df   = _dict_a_df(data['pnl_anual'])
    hist_data      = data.get('historial', {})
    hist_df        = _dict_a_df(hist_data) if hist_data else None
    charts         = _make_charts_b64(pnl_mensual_df, hist_df, pnl_anual_df)

    analisis_ia = data.get('analisis_ia', '')
    print(f"[CARD-DEBUG] result_anon: analisis_ia type={type(analisis_ia)} len={len(analisis_ia)} bool={bool(analisis_ia)}")
    print(f"[CARD-DEBUG] keys en session data: {list(data.keys())}")

    context = {
        'info':          data['info'],
        'charts':        charts,
        'tabla_mensual': _pnl_para_tabla(pnl_mensual_df, n_meses=12),
        'tabla_anual':   _pnl_anual_para_tabla(pnl_anual_df),
        'analisis_ia':   analisis_ia,
        'token':         token,
    }
    return render(request, 'forecast/result_anon.html', context)


def download_anon(request, token):
    key = f'forecast_{token}'
    data = request.session.get(key)
    if data is None:
        messages.warning(request, 'Resultado no encontrado o sesión expirada.')
        return redirect('forecast:upload')
    df = _dict_a_df(data['pnl_mensual'])
    response = HttpResponse(df.to_csv(), content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="pnl_mensual.csv"'
    return response


@login_required
def project_list(request):
    proyectos = Proyecto.objects.filter(usuario=request.user)
    return render(request, 'forecast/project_list.html', {'proyectos': proyectos})


@login_required
def project_detail(request, pk):
    proyecto = get_object_or_404(Proyecto, pk=pk, usuario=request.user)
    pnl_mensual_df = _dict_a_df(proyecto.pnl_mensual_json)
    pnl_anual_df   = _dict_a_df(proyecto.pnl_anual_json)
    hist_df        = _dict_a_df(proyecto.historial_json) if proyecto.historial_json else None
    charts         = _make_charts_b64(pnl_mensual_df, hist_df, pnl_anual_df)

    analisis_ia = proyecto.analisis_ia
    print(f"[CARD-DEBUG] project_detail pk={pk}: analisis_ia type={type(analisis_ia)} len={len(analisis_ia)} bool={bool(analisis_ia)}")

    context = {
        'proyecto':      proyecto,
        'charts':        charts,
        'tabla_mensual': _pnl_para_tabla(pnl_mensual_df, n_meses=12),
        'tabla_anual':   _pnl_anual_para_tabla(pnl_anual_df),
        'analisis_ia':   analisis_ia,
    }
    return render(request, 'forecast/project_detail.html', context)


@login_required
def project_charts(request, pk):
    proyecto = get_object_or_404(Proyecto, pk=pk, usuario=request.user)
    pnl_mensual_df = _dict_a_df(proyecto.pnl_mensual_json)
    pnl_anual_df   = _dict_a_df(proyecto.pnl_anual_json)
    hist_df        = _dict_a_df(proyecto.historial_json) if proyecto.historial_json else None
    charts         = _make_charts_b64(pnl_mensual_df, hist_df, pnl_anual_df)
    return render(request, 'forecast/charts.html', {'proyecto': proyecto, 'charts': charts})


@login_required
def download_proyecto(request, pk, tipo):
    proyecto = get_object_or_404(Proyecto, pk=pk, usuario=request.user)
    if tipo == 'mensual':
        df       = _dict_a_df(proyecto.pnl_mensual_json)
        filename = f'pnl_mensual_{proyecto.pk}.csv'
    else:
        df       = _dict_a_df(proyecto.pnl_anual_json)
        filename = f'pnl_anual_{proyecto.pk}.csv'
    response = HttpResponse(df.to_csv(), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
@require_POST
def delete_proyecto(request, pk):
    proyecto = get_object_or_404(Proyecto, pk=pk, usuario=request.user)
    nombre = proyecto.nombre
    proyecto.delete()
    messages.success(request, f'Proyecto "{nombre}" eliminado.')
    return redirect('forecast:project_list')


def download_sample(request):
    from django.conf import settings as _settings
    sample_path = _settings.BASE_DIR / 'sample_data.csv'
    with open(sample_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sample_data.csv"'
    return response


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Bienvenido, {user.username}!')
            return redirect('forecast:upload')
    else:
        form = UserCreationForm()

    for field in form.fields.values():
        field.widget.attrs['class'] = 'form-control'

    return render(request, 'registration/register.html', {'form': form})
