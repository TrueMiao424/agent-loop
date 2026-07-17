from django.urls import path

from apps.session.controller.views import SessionListView, SessionResetView

urlpatterns = [
    path("", SessionListView.as_view()),
    path("reset/", SessionResetView.as_view()),
]
