from django.urls import path
from . import views

app_name = "problems"

urlpatterns = [
    # 問題生成（バッチ専用）
    path("generate", views.GenerateProblemView.as_view(), name="generate"),
    # 新規問題取得
    path("", views.GetProblemGroupView.as_view(), name="get_problem_group"),
    # 復習（自分の問題一覧）
    path("mine", views.MyProblemGroupsView.as_view(), name="mine"),
    # 特定問題詳細
    path(
        "<int:problem_group_id>",
        views.ProblemGroupDetailView.as_view(),
        name="detail",
    ),
    # 問題完了
    path(
        "<int:problem_group_id>/complete",
        views.CompleteProblemGroupView.as_view(),
        name="complete",
    ),
]
