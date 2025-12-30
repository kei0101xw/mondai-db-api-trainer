"""
問題在庫管理バッチコマンド

難易度ごとに未解答問題の在庫をチェックし、5問未満の場合は自動補充する。

使用方法:
    python manage.py maintain_stock

オプション:
    --min-stock: 最低在庫数（デフォルト: 5）
    --dry-run: 実際には生成せず、ログ出力のみ行う
"""

from django.core.management.base import BaseCommand

from apps.problems.models import ProblemGroup, ProblemGroupAttempt
from apps.problems.services import ProblemGenerator, ProblemGeneratorError


class Command(BaseCommand):
    """問題在庫を管理するコマンド."""

    help = "難易度ごとの問題在庫をチェックし、必要に応じて補充します"

    def add_arguments(self, parser):
        """コマンドライン引数を追加する."""
        parser.add_argument(
            "--min-stock",
            type=int,
            default=5,
            help="最低在庫数（デフォルト: 5）",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="実際には生成せず、ログ出力のみ行う",
        )

    def handle(self, *args, **options):
        """コマンドを実行する."""
        min_stock = options["min_stock"]
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUNモード: 実際には問題を生成しません")
            )

        difficulties = ["easy", "medium", "hard"]
        total_generated = 0

        for difficulty in difficulties:
            total_count = ProblemGroup.objects.filter(difficulty=difficulty).count()

            attempted_ids = (
                ProblemGroupAttempt.objects.filter(problem_group__difficulty=difficulty)
                .values_list("problem_group_id", flat=True)
                .distinct()
            )

            stock_count = total_count - len(set(attempted_ids))

            self.stdout.write(
                f"難易度 {difficulty}: 在庫 {stock_count} 問 "
                f"(全体 {total_count} - 解答済み {len(set(attempted_ids))})"
            )

            if stock_count < min_stock:
                shortage = min_stock - stock_count
                self.stdout.write(
                    self.style.WARNING(
                        f"  → {shortage} 問不足しています。補充を開始します..."
                    )
                )

                for i in range(shortage):
                    if dry_run:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  [DRY RUN] {difficulty} の問題 {i + 1}/{shortage} を生成します"
                            )
                        )
                    else:
                        try:
                            generator = ProblemGenerator()
                            problem_group, problems, _ = generator.generate(
                                difficulty=difficulty
                            )
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"  ✓ 問題 {i + 1}/{shortage} を生成しました "
                                    f"(ID: {problem_group.problem_group_id}, "
                                    f"タイトル: {problem_group.title})"
                                )
                            )
                            total_generated += 1
                        except ProblemGeneratorError as e:
                            self.stdout.write(
                                self.style.ERROR(
                                    f"  ✗ 問題 {i + 1}/{shortage} の生成に失敗しました: {e}"
                                )
                            )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"  → 在庫は十分です（最低 {min_stock} 問以上）")
                )

        self.stdout.write("\n" + "=" * 60)
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    "[DRY RUN] 補充処理を完了しました（実際には生成していません）"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"補充処理を完了しました（合計 {total_generated} 問生成）"
                )
            )
