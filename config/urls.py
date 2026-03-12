"""
URL configuration for django-htmx-starter project.

For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from core import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('examples/counter/', views.counter, name='counter'),
    path('examples/counter/update/', views.counter_update, name='counter_update'),
    path('admin/', admin.site.urls),
    path('', include('allauth.urls')),
]

if settings.DEBUG:
    urlpatterns += [
        path("__reload__/", include("django_browser_reload.urls")),
    ]
