from django.urls import path
from . import views
from . import settings_views

urlpatterns = [
    path('', views.dashboard_overview, name='overview'),
    path('onboarding/', views.onboarding, name='onboarding'),
    path('catalog/', views.app_catalog, name='catalog'),
    path('install/<slug:slug>/', views.install_app, name='install_app'),
    path('app/<slug:slug>/', views.app_details, name='app_details'),
    path('app/<slug:slug>/<str:action>/', views.app_control, name='app_control'),
    path('stats/', views.system_stats, name='system_stats'),
    path('settings/', settings_views.system_settings, name='settings'),
    path('settings/update/', settings_views.system_update, name='system_update'),
]
