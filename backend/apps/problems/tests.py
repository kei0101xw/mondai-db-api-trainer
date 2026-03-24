import json
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.problems.models import (
    Problem,
    ProblemGroup,
    RequirementItem,
    RequirementTurnLog,
)

User = get_user_model()


class RequirementQuestionApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            name="tester",
            password="password123",
        )
        self.problem_group = ProblemGroup.objects.create(
            title="SNSアプリ",
            description="投稿、コメント、フォローができるSNSアプリです。",
            difficulty=ProblemGroup.Difficulty.EASY,
        )
        Problem.objects.create(
            problem_group=self.problem_group,
            problem_type=Problem.ProblemType.DB,
            order_index=1,
            problem_body="DB設計を行ってください。",
        )
        Problem.objects.create(
            problem_group=self.problem_group,
            problem_type=Problem.ProblemType.API,
            order_index=2,
            problem_body="API設計を行ってください。",
        )

    @patch("apps.problems.services.GeminiClient")
    def test_requirement_question_creates_turn_log_and_requirement_items(
        self, gemini_client_class
    ):
        self.client.force_login(self.user)

        gemini_client = Mock()
        gemini_client.generate_content.return_value = json.dumps(
            {
                "ai_answer": "投稿は論理削除とし、公開一覧には表示しない前提です。",
                "requirement_items": [
                    {
                        "subject": "posts",
                        "predicate": "delete_policy",
                        "object_value": "soft_delete",
                        "detail_text": "投稿は論理削除とし、公開一覧には表示しない",
                    }
                ],
            }
        )
        gemini_client_class.return_value = gemini_client

        response = self.client.post(
            f"/api/v1/problem-groups/{self.problem_group.problem_group_id}/requirements/questions",
            {"question": "退会したユーザーの投稿は物理削除ですか？"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data["error"])
        self.assertEqual(RequirementTurnLog.objects.count(), 1)
        self.assertEqual(RequirementItem.objects.count(), 1)

        turn_log = RequirementTurnLog.objects.get()
        requirement_item = RequirementItem.objects.get()

        self.assertEqual(turn_log.turn_no, 1)
        self.assertEqual(
            turn_log.user_question, "退会したユーザーの投稿は物理削除ですか？"
        )
        self.assertEqual(requirement_item.requirement_turn_log_id, turn_log.id)
        self.assertEqual(requirement_item.subject, "posts")
        self.assertEqual(
            response.data["data"]["turn"]["ai_answer"],
            "投稿は論理削除とし、公開一覧には表示しない前提です。",
        )
        self.assertEqual(len(response.data["data"]["requirement_items"]), 1)

    @patch("apps.problems.services.GeminiClient")
    def test_requirement_list_returns_turn_logs_and_requirement_items(
        self, gemini_client_class
    ):
        self.client.force_login(self.user)

        gemini_client = Mock()
        gemini_client.generate_content.return_value = json.dumps(
            {
                "ai_answer": "ユーザー名は重複不可とします。",
                "requirement_items": [
                    {
                        "subject": "users",
                        "predicate": "name_uniqueness",
                        "object_value": "unique",
                        "detail_text": "ユーザー名は一意でなければならない",
                    }
                ],
            }
        )
        gemini_client_class.return_value = gemini_client

        self.client.post(
            f"/api/v1/problem-groups/{self.problem_group.problem_group_id}/requirements/questions",
            {"question": "ユーザー名は重複できますか？"},
            format="json",
        )

        response = self.client.get(
            f"/api/v1/problem-groups/{self.problem_group.problem_group_id}/requirements"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]["turn_logs"]), 1)
        self.assertEqual(len(response.data["data"]["requirement_items"]), 1)
        self.assertEqual(
            response.data["data"]["requirement_items"][0]["predicate"],
            "name_uniqueness",
        )

    def test_requirement_question_requires_authentication(self):
        response = self.client.post(
            f"/api/v1/problem-groups/{self.problem_group.problem_group_id}/requirements/questions",
            {"question": "質問です"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["error"]["code"], "UNAUTHORIZED")


class GradeAnswerApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="grader@example.com",
            name="grader",
            password="password123",
        )
        self.problem_group = ProblemGroup.objects.create(
            title="SNSアプリ",
            description="投稿、コメント、フォローができるSNSアプリです。",
            difficulty=ProblemGroup.Difficulty.EASY,
        )
        self.db_problem = Problem.objects.create(
            problem_group=self.problem_group,
            problem_type=Problem.ProblemType.DB,
            order_index=1,
            problem_body="DB設計を行ってください。",
        )
        self.api_problem = Problem.objects.create(
            problem_group=self.problem_group,
            problem_type=Problem.ProblemType.API,
            order_index=2,
            problem_body="API設計を行ってください。",
        )

    @patch("apps.problems.views.AnswerGrader")
    def test_grade_appends_requirement_items_to_problem_body_for_authenticated_user(
        self, grader_class
    ):
        self.client.force_login(self.user)
        session = self.client.session
        session["current_problem_group_id"] = self.problem_group.problem_group_id
        session.save()

        turn_log = RequirementTurnLog.objects.create(
            problem_group=self.problem_group,
            user=self.user,
            user_question="退会したユーザーの投稿はどう扱いますか？",
            ai_answer="投稿は論理削除とし、公開一覧には表示しません。",
            turn_no=1,
        )
        RequirementItem.objects.create(
            requirement_turn_log=turn_log,
            problem_group=self.problem_group,
            user=self.user,
            subject="posts",
            predicate="delete_policy",
            object_value="soft_delete",
            detail_text="投稿は論理削除とし、公開一覧には表示しない",
        )

        grader = Mock()
        grader.grade_batch.return_value = [
            {
                "order_index": 1,
                "grade": 2,
                "model_answer": "CREATE TABLE posts (...);",
                "explanation": "よくできています。",
            },
            {
                "order_index": 2,
                "grade": 1,
                "model_answer": "POST /posts",
                "explanation": "概ね良いです。",
            },
        ]
        grader_class.return_value = grader

        response = self.client.post(
            "/api/v1/grade",
            {
                "problem_group_id": self.problem_group.problem_group_id,
                "answers": [
                    {
                        "problem_id": self.db_problem.problem_id,
                        "answer_body": "CREATE TABLE posts (...);",
                    },
                    {
                        "problem_id": self.api_problem.problem_id,
                        "answer_body": "def create_post(...): ...",
                    },
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        grader.grade_batch.assert_called_once()

        problems_with_answers = grader.grade_batch.call_args.args[0]
        self.assertEqual(len(problems_with_answers), 2)
        self.assertIn("## 追加要件", problems_with_answers[0]["problem_body"])
        self.assertIn(
            "投稿は論理削除とし、公開一覧には表示しない",
            problems_with_answers[0]["problem_body"],
        )
        self.assertIn(
            "subject=posts, predicate=delete_policy, object_value=soft_delete",
            problems_with_answers[0]["problem_body"],
        )
        self.assertIn("## 追加要件", problems_with_answers[1]["problem_body"])
