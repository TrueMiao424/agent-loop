from django.urls import path

from apps.project.controller.views import ProjectDetailView, ProjectListCreateView

urlpatterns = [
    path("", ProjectListCreateView.as_view()),
    path("<int:project_id>/", ProjectDetailView.as_view()),
]
