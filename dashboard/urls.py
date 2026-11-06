"""
dashboard/urls.py — Web dashboard URL routing.
9 pages as specified in Stage 1 requirements.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.overview, name='overview'),
    path('network/', views.network_activity, name='network'),
    path('usb/', views.usb_activity, name='usb'),
    path('files/', views.file_activity, name='files'),
    path('android/', views.android_activity, name='android'),
    path('timeline/', views.timeline, name='timeline'),
    path('evidence/', views.evidence_management, name='evidence'),
    path('evidence/verify/<str:evidence_id>/', views.verify_evidence, name='verify_evidence'),
    path('collectors/', views.collectors_management, name='collectors'),
    path('reports/', views.reports, name='reports'),
    path('reports/export/', views.export_csv, name='export_csv'),
]
