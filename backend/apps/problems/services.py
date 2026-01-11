import json
import unicodedata
from typing import Any, TypedDict, Optional, List, Tuple, Dict
from django.contrib.auth import get_user_model
from django.db import transaction

from common.ai.gemini_client import GeminiClient, GeminiClientError
from .models import ProblemGroup, Problem
from .prompts import (
    build_problem_generation_prompt,
    build_grading_prompt,
    build_batch_grading_prompt,
)

User = get_user_model()


def _fix_unescaped_newlines(json_str: str) -> str:
    return json_str


def _attempt_fix_incomplete_json(json_str: str) -> str:
    return json_str


class ProblemData(TypedDict):
    """小問のデータ構造"""

    problem_type: str
    order_index: int
    problem_body: str


class GeneratedProblemGroup(TypedDict):
    """生成された問題グループのデータ構造"""

    title: str
    description: str
    problems: List[ProblemData]


class GradingResult(TypedDict):
    """採点結果のデータ構造"""

    grade: int
    model_answer: str
    explanation: str


class BatchGradingResult(TypedDict):
    """一括採点の個別結果のデータ構造"""

    order_index: int
    grade: int
    model_answer: str
    explanation: str


class ProblemGeneratorError(Exception):
    """問題生成エラー"""

    pass


class AnswerGraderError(Exception):
    """採点エラー"""

    pass


class ProblemGenerator:
    """
    Gemini APIを使用して問題を生成するサービスクラス
    """

    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        """
        Args:
            gemini_client: GeminiClientインスタンス（テスト用）
        """
        self.gemini_client = gemini_client or GeminiClient()

    def generate(
        self,
        difficulty: str,
    ) -> Tuple[Optional[ProblemGroup], Optional[List[Problem]], Dict[str, Any]]:
        """
        問題を生成する（バッチ専用API）

        Args:
            difficulty: 難易度 (easy/medium/hard)

        Returns:
            (ProblemGroupインスタンス, Problemリスト, レスポンスデータ)
            - DB保存してインスタンスを返す
            - model_answers も同時に生成・保存する

        Raises:
            ProblemGeneratorError: 問題生成に失敗した場合
        """

        prompt = build_problem_generation_prompt(difficulty)

        try:
            response_text = self.gemini_client.generate_content(
                prompt=prompt,
                temperature=0.8,
                max_output_tokens=16384,  # 問題生成は長いレスポンスになるため十分なトークン数を確保
                response_format="application/json",
                timeout=120,  # 問題生成は複雑なため120秒のタイムアウトを設定
            )
        except GeminiClientError as e:
            raise ProblemGeneratorError(f"Gemini API呼び出しエラー: {e}") from e

        try:
            json_str = self._extract_json_from_response(response_text)
            generated_data: GeneratedProblemGroup = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ProblemGeneratorError(f"JSONパースエラー: {e}") from e
        except ValueError as e:
            debug_snippet = (
                response_text[:500] if len(response_text) > 500 else response_text
            )
            raise ProblemGeneratorError(
                f"JSON抽出エラー: {e}\nレスポンス先頭: {debug_snippet}"
            ) from e

        self._validate_generated_data(generated_data)

        return self._save_to_db(
            generated_data=generated_data,
            difficulty=difficulty,
        )

    @staticmethod
    def _extract_json_from_response(response_text: str) -> str:
        """
        GeminiレスポンスはJSONのみを想定しているため、最小限の整形で返す。
        - 先頭末尾にコードフェンスが両方付いていれば剥がす（簡易対応）
        - それ以外はそのまま返す
        """
        text = response_text.strip()
        if text.startswith("```") and text.rstrip().endswith("```"):
            first_newline = text.find("\n")
            if first_newline != -1:
                text = text[first_newline + 1 :]
            text = text.rsplit("```", 1)[0].strip()
        return text

    def _validate_generated_data(self, data: GeneratedProblemGroup) -> None:
        """
        生成されたデータをバリデーションする

        Args:
            data: 生成されたデータ

        Raises:
            ProblemGeneratorError: バリデーションエラー
        """
        if "title" not in data or not data["title"]:
            raise ProblemGeneratorError("title が含まれていません")
        if "description" not in data or not data["description"]:
            raise ProblemGeneratorError("description が含まれていません")
        if "problems" not in data or not isinstance(data["problems"], list):
            raise ProblemGeneratorError("problems が配列ではありません")
        if "model_answers" not in data or not isinstance(data["model_answers"], list):
            raise ProblemGeneratorError("model_answers が配列ではありません")

        # 問題数チェック（mode=both固定: DB1問 + API1問以上）
        problem_count = len(data["problems"])
        if problem_count < 2:
            raise ProblemGeneratorError(
                f"問題数が不正です（期待: 2問以上, 実際: {problem_count}）"
            )

        for idx, problem in enumerate(data["problems"], start=1):
            if "problem_type" not in problem:
                raise ProblemGeneratorError(
                    f"問題{idx}: problem_type が含まれていません"
                )
            if "order_index" not in problem:
                raise ProblemGeneratorError(
                    f"問題{idx}: order_index が含まれていません"
                )
            if "problem_body" not in problem:
                raise ProblemGeneratorError(
                    f"問題{idx}: problem_body が含まれていません"
                )

            if problem["problem_type"] not in ["db", "api"]:
                raise ProblemGeneratorError(
                    f"問題{idx}: problem_type が不正です（{problem['problem_type']}）"
                )

        problem_types = [p["problem_type"] for p in data["problems"]]
        if problem_types[0] != "db":
            raise ProblemGeneratorError(
                f"mode=both では最初の問題は DB 設計である必要があります（実際: {problem_types[0]}）"
            )

        db_count = problem_types.count("db")
        api_count = problem_types.count("api")

        if db_count != 1:
            raise ProblemGeneratorError(
                f"mode=both では DB 設計問題は1問である必要があります（実際: {db_count}問）"
            )

        if api_count < 1:
            raise ProblemGeneratorError(
                f"mode=both では API 設計問題は1問以上必要です（実際: {api_count}問）"
            )

        for idx, model_answer in enumerate(data["model_answers"], start=1):
            if "order_index" not in model_answer:
                raise ProblemGeneratorError(
                    f"模範解答{idx}: order_index が含まれていません"
                )
            if "version" not in model_answer:
                raise ProblemGeneratorError(
                    f"模範解答{idx}: version が含まれていません"
                )
            if "model_answer" not in model_answer or not model_answer["model_answer"]:
                raise ProblemGeneratorError(
                    f"模範解答{idx}: model_answer が含まれていません"
                )
            if model_answer["version"] != 1:
                raise ProblemGeneratorError(
                    f"模範解答{idx}: version は 1 である必要があります（実際: {model_answer['version']}）"
                )

    @transaction.atomic
    def _save_to_db(
        self,
        generated_data: GeneratedProblemGroup,
        difficulty: str,
    ) -> Tuple[ProblemGroup, List[Problem], Dict[str, Any]]:
        """
        生成されたデータをDBに保存する（バッチ専用）

        Args:
            generated_data: 生成されたデータ
            difficulty: 難易度

        Returns:
            (ProblemGroupインスタンス, Problemリスト, レスポンスデータ)
        """
        from .models import ModelAnswer

        problem_group = ProblemGroup.objects.create(
            title=generated_data["title"],
            description=generated_data["description"],
            difficulty=difficulty,
        )

        problems = []
        problem_id_by_order = {}
        for problem_data in generated_data["problems"]:
            problem = Problem.objects.create(
                problem_group=problem_group,
                problem_type=problem_data["problem_type"],
                order_index=problem_data["order_index"],
                problem_body=problem_data["problem_body"],
            )
            problems.append(problem)
            problem_id_by_order[problem.order_index] = problem.problem_id

        model_answers = []
        for ma_data in generated_data["model_answers"]:
            problem = next(
                (p for p in problems if p.order_index == ma_data["order_index"]), None
            )
            if problem:
                model_answer = ModelAnswer.objects.create(
                    problem=problem,
                    version=ma_data["version"],
                    model_answer=ma_data["model_answer"],
                )
                model_answers.append(model_answer)

        response_data = {
            "kind": "persisted",
            "problem_group": {
                "problem_group_id": problem_group.problem_group_id,
                "title": problem_group.title,
                "description": problem_group.description,
                "difficulty": problem_group.difficulty,
                "created_at": problem_group.created_at.isoformat(),
            },
            "problems": [
                {
                    "problem_id": p.problem_id,
                    "problem_group_id": problem_group.problem_group_id,
                    "problem_type": p.problem_type,
                    "order_index": p.order_index,
                    "problem_body": p.problem_body,
                }
                for p in problems
            ],
            "model_answers": [
                {
                    "problem_id": ma.problem.problem_id,
                    "version": ma.version,
                    "model_answer": ma.model_answer,
                }
                for ma in model_answers
            ],
        }

        return problem_group, problems, response_data


class AnswerGrader:
    """
    Gemini APIを使用して解答を採点するサービスクラス
    """

    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        """
        Args:
            gemini_client: GeminiClientインスタンス（テスト用）
        """
        self.gemini_client = gemini_client or GeminiClient()

    def grade(
        self, problem_type: str, problem_body: str, answer_body: str
    ) -> GradingResult:
        """
        解答を採点する

        Args:
            problem_type: 問題タイプ (db/api)
            problem_body: 問題本文
            answer_body: ユーザーの回答

        Returns:
            採点結果（grade, model_answer, explanation）

        Raises:
            AnswerGraderError: 採点に失敗した場合
        """
        answer_body = self._sanitize_answer(answer_body)

        prompt = build_grading_prompt(problem_type, problem_body, answer_body)

        try:
            response_text = self.gemini_client.generate_content(
                prompt=prompt,
                temperature=0.3,  # 採点は一貫性を重視するため低めに設定
                max_output_tokens=8192,
                response_format="application/json",
                timeout=90,
            )
        except GeminiClientError as e:
            raise AnswerGraderError(f"Gemini API呼び出しエラー: {e}") from e
        try:
            json_str = self._extract_json_from_response(response_text)
            grading_result: GradingResult = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise AnswerGraderError(f"JSONパースエラー: {e}") from e
        except ValueError as e:
            debug_snippet = (
                response_text[:500] if len(response_text) > 500 else response_text
            )
            raise AnswerGraderError(
                f"JSON抽出エラー: {e}\nレスポンス先頭: {debug_snippet}"
            ) from e

        if not isinstance(grading_result, dict):
            raise AnswerGraderError(
                f"採点結果がオブジェクトではありません（型: {type(grading_result).__name__}）"
            )

        # バリデーション
        self._validate_grading_result(grading_result)

        return grading_result

    @staticmethod
    def _sanitize_answer(text: str) -> str:
        """
        ユーザー入力をサニタイズする

        Args:
            text: ユーザーの回答テキスト

        Returns:
            サニタイズされたテキスト
        """
        text = unicodedata.normalize("NFC", text)

        cleaned = []
        for char in text:
            if ord(char) < 32 and char not in "\n\t":
                continue
            cleaned.append(char)

        return "".join(cleaned)

    @staticmethod
    def _extract_json_from_response(response_text: str) -> str:
        """
        GeminiレスポンスはJSONのみを想定しているため、最小限の整形で返す。
        - 先頭末尾にコードフェンスが両方付いていれば剥がす（簡易対応）
        - それ以外はそのまま返す
        """
        text = response_text.strip()
        if text.startswith("```") and text.rstrip().endswith("```"):
            first_newline = text.find("\n")
            if first_newline != -1:
                text = text[first_newline + 1 :]
            text = text.rsplit("```", 1)[0].strip()
        return text

    def _validate_grading_result(self, result: GradingResult) -> None:
        """
        採点結果をバリデーションする

        Args:
            result: 採点結果

        Raises:
            AnswerGraderError: バリデーションエラー
        """
        if "grade" not in result:
            raise AnswerGraderError("grade が含まれていません")
        if "model_answer" not in result or not result["model_answer"]:
            raise AnswerGraderError("model_answer が含まれていません")
        if "explanation" not in result or not result["explanation"]:
            raise AnswerGraderError("explanation が含まれていません")

        # grade の値チェック
        if not isinstance(result["grade"], int) or result["grade"] not in [0, 1, 2]:
            raise AnswerGraderError(
                f"grade は 0, 1, 2 のいずれかである必要があります（実際: {result['grade']}）"
            )

    def grade_batch(
        self,
        problems_with_answers: List[Dict[str, Any]],
    ) -> List[BatchGradingResult]:
        """
        複数の問題と回答を一括で採点する

        Args:
            problems_with_answers: 問題と回答のペアリスト
                [
                    {
                        "order_index": 1,
                        "problem_type": "db",
                        "problem_body": "問題文",
                        "answer_body": "回答"
                    },
                    ...
                ]

        Returns:
            各問題の採点結果リスト

        Raises:
            AnswerGraderError: 採点に失敗した場合
        """
        # 入力サニタイゼーション
        sanitized_items = []
        for item in problems_with_answers:
            sanitized_items.append(
                {
                    "order_index": item["order_index"],
                    "problem_type": item["problem_type"],
                    "problem_body": item["problem_body"],
                    "answer_body": self._sanitize_answer(item["answer_body"]),
                }
            )

        prompt = build_batch_grading_prompt(sanitized_items)

        try:
            response_text = self.gemini_client.generate_content(
                prompt=prompt,
                temperature=0.3,  # 採点は一貫性を重視するため低めに設定
                max_output_tokens=65536,  # 一括採点は複数問題の模範解答を含むため大きめに設定
                response_format="application/json",
                timeout=90,
            )
        except GeminiClientError as e:
            raise AnswerGraderError(f"Gemini API呼び出しエラー: {e}") from e

        try:
            json_str = self._extract_json_from_response(response_text)
            parsed_response = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise AnswerGraderError(f"JSONパースエラー: {e}") from e
        except ValueError as e:
            debug_snippet = (
                response_text[:500] if len(response_text) > 500 else response_text
            )
            raise AnswerGraderError(
                f"JSON抽出エラー: {e}\nレスポンス先頭: {debug_snippet}"
            ) from e

        if not isinstance(parsed_response, dict):
            raise AnswerGraderError(
                f"採点結果がオブジェクトではありません（型: {type(parsed_response).__name__}）"
            )

        if "results" not in parsed_response or not isinstance(
            parsed_response["results"], list
        ):
            raise AnswerGraderError("results 配列が含まれていません")

        results = parsed_response["results"]

        validated_results: List[BatchGradingResult] = []
        expected_indices = {item["order_index"] for item in problems_with_answers}

        for result in results:
            self._validate_batch_grading_result(result, expected_indices)
            validated_results.append(
                {
                    "order_index": result["order_index"],
                    "grade": result["grade"],
                    "model_answer": result["model_answer"],
                    "explanation": result["explanation"],
                }
            )

        result_indices = {r["order_index"] for r in validated_results}
        if result_indices != expected_indices:
            missing = expected_indices - result_indices
            raise AnswerGraderError(
                f"採点結果に不足があります（不足: order_index {missing}）"
            )

        validated_results.sort(key=lambda x: x["order_index"])

        return validated_results

    def _validate_batch_grading_result(
        self, result: Dict[str, Any], expected_indices: set
    ) -> None:
        """
        一括採点の個別結果をバリデーションする

        Args:
            result: 採点結果
            expected_indices: 期待される order_index の集合

        Raises:
            AnswerGraderError: バリデーションエラー
        """
        if "order_index" not in result:
            raise AnswerGraderError("order_index が含まれていません")
        if not isinstance(result["order_index"], int):
            raise AnswerGraderError(
                f"order_index は整数である必要があります（実際: {result['order_index']}）"
            )

        if "grade" not in result:
            raise AnswerGraderError(
                f"order_index {result['order_index']}: grade が含まれていません"
            )
        if "model_answer" not in result or not result["model_answer"]:
            raise AnswerGraderError(
                f"order_index {result['order_index']}: model_answer が含まれていません"
            )
        if "explanation" not in result or not result["explanation"]:
            raise AnswerGraderError(
                f"order_index {result['order_index']}: explanation が含まれていません"
            )

        if not isinstance(result["grade"], int) or result["grade"] not in [0, 1, 2]:
            raise AnswerGraderError(
                f"order_index {result['order_index']}: grade は 0, 1, 2 のいずれかである必要があります（実際: {result['grade']}）"
            )
