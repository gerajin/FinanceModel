from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from forecast import views as forecast_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/register/', forecast_views.register, name='register'),
    path('forecast/', include('forecast.urls')),
    path('', RedirectView.as_view(url='/forecast/', permanent=False)),
]
