from django.urls import path

from apps.settings_app.controller.views import SettingsTestView, SettingsView

urlpatterns = [
    path("", SettingsView.as_view()),
    path("test/", SettingsTestView.as_view()),
]
