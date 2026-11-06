"""
api_app/urls.py — REST-like JSON API URLs for Expo GUI.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('stats/', views.stats_view, name='api_stats'),
    path('events/', views.events_view, name='api_events'),
    path('evidence/', views.evidence_view, name='api_evidence'),
    path('collectors/', views.collectors_view, name='api_collectors'),
    path('collectors/start/', views.collector_start_view, name='api_collector_start'),
    path('collectors/stop/', views.collector_stop_view, name='api_collector_stop'),
    path('network/import/', views.network_import_view, name='api_network_import'),
]
