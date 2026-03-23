from django.urls import path
from . import views

app_name = 'forecast'

urlpatterns = [
    path('',                                          views.forecast_upload,    name='upload'),
    path('nuevo/',                                    views.forecast_nuevo,     name='nuevo'),
    path('result/<uuid:token>/',                      views.result_anon,        name='result_anon'),
    path('download/<uuid:token>/mensual/',            views.download_anon,      name='download_anon'),
    path('projects/',                                 views.project_list,       name='project_list'),
    path('projects/<int:pk>/',                        views.project_detail,     name='project_detail'),
    path('projects/<int:pk>/charts/',                 views.project_charts,     name='project_charts'),
    path('projects/<int:pk>/download/<str:tipo>/',    views.download_proyecto,  name='download_proyecto'),
    path('projects/<int:pk>/delete/',                 views.delete_proyecto,    name='delete_proyecto'),
    path('sample-csv/',                               views.download_sample,    name='download_sample'),
    path('ia/<uuid:token>/',                          views.ia_stream_anon,     name='ia_stream_anon'),
    path('projects/<int:pk>/ia/',                     views.ia_stream_proyecto, name='ia_stream_proyecto'),
]
