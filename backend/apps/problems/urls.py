from django.urls import path
from . import views

app_name = "problems"

urlpatterns = [
    path("generate", views.GenerateProblemView.as_view(), name="generate"),
]
