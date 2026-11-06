"""
forensics_core/urls.py — Root URL configuration
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api_app.urls')),
    path('', include('dashboard.urls')),
]
