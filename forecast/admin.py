from django.contrib import admin
from .models import Proyecto


@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'usuario', 'metodo_usado', 'score_confiabilidad', 'creado')
    list_filter  = ('metodo_usado', 'usuario')
    search_fields = ('nombre', 'usuario__username')
    readonly_fields = ('creado', 'metodo_usado', 'meses_historicos', 'score_confiabilidad')
