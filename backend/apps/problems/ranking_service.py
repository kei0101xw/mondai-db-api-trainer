"""
ランキング集計サービス

将来の拡張を考慮した設計:
- スコア計算方式: problem_count（MVP）、correct_count、grade_sum
- 期間: daily（MVP）、weekly、monthly、all
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from django.db.models import Count, Sum, Case, When, IntegerField
from django.db.models.functions import Coalesce
from django.utils import timezone

from .models import Answer


class Period(Enum):
    """ランキング集計期間"""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ALL = "all"


class ScoreType(Enum):
    """スコア計算方式"""

    PROBLEM_COUNT = "problem_count"  # 解いた問題数（MVP）
    CORRECT_COUNT = "correct_count"  # 〇の数
    GRADE_SUM = "grade_sum"  # 採点結果の合計（〇=2, △=1, ×=0）


@dataclass
class RankingEntry:
    """ランキングエントリ"""

    rank: int
    user_id: int
    name: str
    score: int


def get_period_start(period: Period) -> Optional[datetime]:
    """
    期間に応じた開始日時を取得する

    Args:
        period: 集計期間

    Returns:
        開始日時（ALLの場合はNone）
    """
    now = timezone.now()

    if period == Period.DAILY:
        # 今日の0時0分0秒
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == Period.WEEKLY:
        # 今週の月曜日の0時0分0秒
        days_since_monday = now.weekday()
        monday = now - timedelta(days=days_since_monday)
        return monday.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == Period.MONTHLY:
        # 今月の1日の0時0分0秒
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        # ALL: フィルタなし
        return None


def get_ranking(
    period: Period = Period.DAILY,
    score_type: ScoreType = ScoreType.PROBLEM_COUNT,
    limit: int = 5,
) -> list[RankingEntry]:
    """
    ランキングを取得する

    Args:
        period: 集計期間（デフォルト: DAILY）
        score_type: スコア計算方式（デフォルト: PROBLEM_COUNT）
        limit: 取得件数（デフォルト: 5）

    Returns:
        ランキングエントリのリスト
    """
    # 期間フィルタの開始日時を取得
    period_start = get_period_start(period)

    # ベースクエリ
    queryset = Answer.objects.all()

    # 期間でフィルタ
    if period_start is not None:
        queryset = queryset.filter(created_at__gte=period_start)

    # ユーザーでグループ化し、スコアを計算
    if score_type == ScoreType.PROBLEM_COUNT:
        # 解いた問題数
        queryset = queryset.values("user_id", "user__name").annotate(
            score=Count("answer_id")
        )
    elif score_type == ScoreType.CORRECT_COUNT:
        # 〇の数（grade=2）
        queryset = queryset.values("user_id", "user__name").annotate(
            score=Count(Case(When(grade=2, then=1), output_field=IntegerField()))
        )
    elif score_type == ScoreType.GRADE_SUM:
        # 採点結果の合計
        queryset = queryset.values("user_id", "user__name").annotate(
            score=Coalesce(Sum("grade"), 0)
        )
    else:
        # デフォルトは問題数
        queryset = queryset.values("user_id", "user__name").annotate(
            score=Count("answer_id")
        )

    # スコアが0より大きいもののみ、スコア降順でソート
    queryset = queryset.filter(score__gt=0).order_by("-score")[:limit]

    # RankingEntry に変換
    rankings = []
    for rank, entry in enumerate(queryset, start=1):
        rankings.append(
            RankingEntry(
                rank=rank,
                user_id=entry["user_id"],
                name=entry["user__name"],
                score=entry["score"],
            )
        )

    return rankings
