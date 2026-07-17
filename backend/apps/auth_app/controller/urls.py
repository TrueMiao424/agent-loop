from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.auth_app.controller.views import LoginView, MeView, RegisterView

urlpatterns = [
    path("login/", LoginView.as_view()),
    path("refresh/", TokenRefreshView.as_view()),
    path("register/", RegisterView.as_view()),
    path("me/", MeView.as_view()),
]
