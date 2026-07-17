from django.urls import path

from apps.task.controller.views import (
    TaskCancelView,
    TaskDetailView,
    TaskForceStepView,
    TaskInterruptView,
    TaskListCreateView,
    TaskOpinionView,
    TaskResumableListView,
    TaskResumeView,
    TaskReview1View,
    TaskReview2View,
)

urlpatterns = [
    path("", TaskListCreateView.as_view()),
    path("resumable/", TaskResumableListView.as_view()),
    path("<int:task_id>/", TaskDetailView.as_view()),
    path("<int:task_id>/review1/", TaskReview1View.as_view()),
    path("<int:task_id>/review2/", TaskReview2View.as_view()),
    path("<int:task_id>/opinion/", TaskOpinionView.as_view()),
    path("<int:task_id>/force-step/", TaskForceStepView.as_view()),
    path("<int:task_id>/interrupt/", TaskInterruptView.as_view()),
    path("<int:task_id>/cancel/", TaskCancelView.as_view()),
    path("<int:task_id>/resume/", TaskResumeView.as_view()),
]
