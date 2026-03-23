from django.urls import path
from . import views

app_name = 'forecast'

urlpatterns = [
    path('',                                          views.forecast_upload,    name='upload'),
    path('result/<uuid:token>/',                      views.result_anon,        name='result_anon'),
    path('download/<uuid:token>/mensual/',            views.download_anon,      name='download_anon'),
    path('projects/',                                 views.project_list,       name='project_list'),
    path('projects/<int:pk>/',                        views.project_detail,     name='project_detail'),
    path('projects/<int:pk>/charts/',                 views.project_charts,     name='project_charts'),
    path('projects/<int:pk>/download/<str:tipo>/',    views.download_proyecto,  name='download_proyecto'),
    path('projects/<int:pk>/delete/',                 views.delete_proyecto,    name='delete_proyecto'),
]
