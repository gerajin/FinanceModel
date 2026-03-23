from django import forms
from .models import Proyecto


class ForecastForm(forms.Form):
    METODO_CHOICES = [
        ('auto',    'Automático (recomendado)'),
        ('promedio','Promedio'),
        ('linear',  'Regresión Lineal'),
        ('arima',   'ARIMA'),
        ('sarima',  'SARIMA'),
        ('prophet', 'Prophet'),
    ]

    csv_file = forms.FileField(
        label='Archivo CSV histórico',
        help_text='Formato: fecha, volumen, precio_unitario, materia_prima, mo_directa, '
                  'mo_indirecta, gastos_directos, gastos_indirectos',
    )
    inflacion_anual = forms.FloatField(
        label='Inflación anual (%)',
        initial=4.0,
        min_value=0.0,
        max_value=100.0,
        help_text='Porcentaje anual (ej: 4 = 4%)',
    )
    variacion_costos = forms.FloatField(
        label='Variación de costos (%)',
        initial=3.0,
        min_value=0.0,
        max_value=100.0,
        help_text='Porcentaje anual (ej: 3 = 3%)',
    )

    # Campos solo para usuarios autenticados
    nombre = forms.CharField(
        label='Nombre del proyecto',
        max_length=200,
        required=False,
    )
    metodo = forms.ChoiceField(
        label='Método de proyección',
        choices=METODO_CHOICES,
        required=False,
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        # Bootstrap classes
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.Select):
                widget.attrs['class'] = 'form-select'
            else:
                widget.attrs['class'] = 'form-control'

        if user is None or not user.is_authenticated:
            # Anónimos no ven nombre ni método
            del self.fields['nombre']
            del self.fields['metodo']
        else:
            self.fields['nombre'].required = True

    def clean_csv_file(self):
        f = self.cleaned_data['csv_file']
        if not f.name.endswith('.csv'):
            raise forms.ValidationError('El archivo debe tener extensión .csv')
        if f.size > 2 * 1024 * 1024:
            raise forms.ValidationError('El archivo no puede superar 2 MB')
        return f

    def clean_inflacion_anual(self):
        v = self.cleaned_data['inflacion_anual']
        return v / 100.0  # convertir a decimal

    def clean_variacion_costos(self):
        v = self.cleaned_data['variacion_costos']
        return v / 100.0  # convertir a decimal
