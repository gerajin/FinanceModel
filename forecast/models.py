from django.db import models
from django.conf import settings


class Proyecto(models.Model):
    METODO_CHOICES = [
        ('auto',    'Automático'),
        ('promedio','Promedio'),
        ('linear',  'Linear'),
        ('arima',   'ARIMA'),
        ('sarima',  'SARIMA'),
        ('prophet', 'Prophet'),
    ]

    usuario             = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='proyectos',
    )
    nombre              = models.CharField(max_length=200)
    creado              = models.DateTimeField(auto_now_add=True)
    metodo_solicitado   = models.CharField(max_length=20, choices=METODO_CHOICES, default='auto')
    metodo_usado        = models.CharField(max_length=20)
    inflacion_anual     = models.FloatField(default=0.04)
    variacion_costos    = models.FloatField(default=0.03)
    incremento_salarial = models.FloatField(default=0.05)
    meses_historicos    = models.IntegerField()
    score_confiabilidad = models.CharField(max_length=20)
    pnl_mensual_json    = models.JSONField(default=dict)
    pnl_anual_json      = models.JSONField(default=dict)
    historial_json      = models.JSONField(default=dict)   # últimos 24 meses históricos
    analisis_ia         = models.TextField(blank=True, default='')  # análisis generado por IA

    class Meta:
        ordering = ['-creado']

    def __str__(self):
        return f'{self.nombre} ({self.usuario.username})'
