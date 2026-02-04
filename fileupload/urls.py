"""
URL Configuration for File Upload App
"""
from django.urls import path
from .views import FileUploadView, FileListView, HealthCheckView

urlpatterns = [
    path('upload/', FileUploadView.as_view(), name='file-upload'),
    path('files/', FileListView.as_view(), name='file-list'),
    path('health/', HealthCheckView.as_view(), name='health-check'),
]
