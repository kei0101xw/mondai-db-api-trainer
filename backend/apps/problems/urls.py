from django.urls import path
from . import views

app_name = "problems"

urlpatterns = [
    path("generate", views.GenerateProblemView.as_view(), name="generate"),
    path("grade", views.GradeAnswerView.as_view(), name="grade"),
]
