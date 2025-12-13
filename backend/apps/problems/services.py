import json
import secrets
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
        app_scale: str,
        mode: str,
        user: Optional[User] = None,
    ) -> Tuple[Optional[ProblemGroup], Optional[List[Problem]], Dict[str, Any]]:
        """
        問題を生成する

        Args:
            difficulty: 難易度 (easy/medium/hard)
            app_scale: アプリ規模 (small/medium/large)
            mode: モード (db_only/api_only/both)
            user: ログインユーザー（Noneの場合はゲスト）

        Returns:
            (ProblemGroupインスタンス or None, Problemリスト or None, レスポンスデータ)
            - ログインユーザーの場合：DB保存してインスタンスを返す
            - ゲストの場合：DBに保存せず、辞書データのみ返す

        Raises:
            ProblemGeneratorError: 問題生成に失敗した場合
        """
        # プロンプト構築
        prompt = build_problem_generation_prompt(difficulty, app_scale, mode)

        # Gemini APIで生成
        try:
            response_text = self.gemini_client.generate_content(
                prompt=prompt,
                temperature=0.8,
                response_format="application/json",
                timeout=120,  # 問題生成は複雑なため120秒のタイムアウトを設定
            )
        except GeminiClientError as e:
            raise ProblemGeneratorError(f"Gemini API呼び出しエラー: {e}") from e

        # JSONパース（前処理付き）
        try:
            json_str = self._extract_json_from_response(response_text)
            generated_data: GeneratedProblemGroup = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ProblemGeneratorError(f"JSONパースエラー: {e}") from e

        # バリデーション
        self._validate_generated_data(generated_data, mode)

        # ログインユーザーの場合：DB保存
        if user and user.is_authenticated:
            return self._save_to_db(
                generated_data=generated_data,
                difficulty=difficulty,
                app_scale=app_scale,
                mode=mode,
                user=user,
            )

        # ゲストの場合：一時データとして返す
        return self._create_guest_response(
            generated_data=generated_data,
            difficulty=difficulty,
            app_scale=app_scale,
            mode=mode,
        )

    @staticmethod
    def _extract_json_from_response(response_text: str) -> str:
        """
        Geminiレスポンスから JSON部分を抽出する

        Args:
            response_text: Gemini APIからのレスポンステキスト

        Returns:
            JSON文字列
        """
        # バッククォートで囲まれている場合を処理
        if response_text.strip().startswith("```"):
            # ```json から ``` までを抽出
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start != -1 and end > start:
                return response_text[start:end]
        return response_text.strip()

    def _validate_generated_data(self, data: GeneratedProblemGroup, mode: str) -> None:
        """
        生成されたデータをバリデーションする

        Args:
            data: 生成されたデータ
            mode: モード

        Raises:
            ProblemGeneratorError: バリデーションエラー
        """
        # 必須フィールドチェック
        if "title" not in data or not data["title"]:
            raise ProblemGeneratorError("title が含まれていません")
        if "description" not in data or not data["description"]:
            raise ProblemGeneratorError("description が含まれていません")
        if "problems" not in data or not isinstance(data["problems"], list):
            raise ProblemGeneratorError("problems が配列ではありません")

        # モードに応じた問題数チェック
        problem_count = len(data["problems"])
        if mode == "db_only":
            if problem_count != 1:
                raise ProblemGeneratorError(
                    f"問題数が不正です（期待: 1, 実際: {problem_count}）"
                )
        elif mode == "api_only":
            if problem_count < 1:
                raise ProblemGeneratorError(
                    f"問題数が不正です（期待: 1問以上, 実際: {problem_count}）"
                )
        elif mode == "both":
            if problem_count < 2:
                raise ProblemGeneratorError(
                    f"問題数が不正です（期待: 2問以上, 実際: {problem_count}）"
                )

        # 各問題のバリデーション
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

            # problem_type のバリデーション
            if problem["problem_type"] not in ["db", "api"]:
                raise ProblemGeneratorError(
                    f"問題{idx}: problem_type が不正です（{problem['problem_type']}）"
                )

        # モードと problem_type の整合性チェック
        problem_types = [p["problem_type"] for p in data["problems"]]

        if mode == "db_only":
            if not all(pt == "db" for pt in problem_types):
                raise ProblemGeneratorError(
                    f"mode=db_only ではすべて DB 設計問題である必要があります（実際: {problem_types}）"
                )
        elif mode == "api_only":
            if not all(pt == "api" for pt in problem_types):
                raise ProblemGeneratorError(
                    f"mode=api_only ではすべて API 設計問題である必要があります（実際: {problem_types}）"
                )
        elif mode == "both":
            # DB設計1問 + API設計1問以上を期待（順序: DB → API）
            if problem_types[0] != "db":
                raise ProblemGeneratorError(
                    f"mode=both では最初の問題は DB 設計である必要があります（実際: {problem_types[0]}）"
                )

            # DB問題の数をカウント
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

            # すべてのAPI問題がDB問題より後に配置されているか確認
            first_api_index = problem_types.index("api")
            if first_api_index == 0:
                raise ProblemGeneratorError(
                    "mode=both では DB 設計問題を最初に配置する必要があります"
                )

    @transaction.atomic
    def _save_to_db(
        self,
        generated_data: GeneratedProblemGroup,
        difficulty: str,
        app_scale: str,
        mode: str,
        user: User,
    ) -> Tuple[ProblemGroup, List[Problem], Dict[str, Any]]:
        """
        生成されたデータをDBに保存する（ログインユーザー用）

        Args:
            generated_data: 生成されたデータ
            difficulty: 難易度
            app_scale: アプリ規模
            mode: モード
            user: ログインユーザー

        Returns:
            (ProblemGroupインスタンス, Problemリスト, レスポンスデータ)
        """
        # ProblemGroup作成
        problem_group = ProblemGroup.objects.create(
            title=generated_data["title"],
            description=generated_data["description"],
            difficulty=difficulty,
            app_scale=app_scale,
            mode=mode,
            created_by_user=user,
        )

        # Problem作成
        problems = []
        for problem_data in generated_data["problems"]:
            problem = Problem.objects.create(
                problem_group=problem_group,
                problem_type=problem_data["problem_type"],
                order_index=problem_data["order_index"],
                problem_body=problem_data["problem_body"],
            )
            problems.append(problem)

        # レスポンスデータ構築
        response_data = {
            "kind": "persisted",
            "problem_group": {
                "problem_group_id": problem_group.problem_group_id,
                "title": problem_group.title,
                "description": problem_group.description,
                "difficulty": problem_group.difficulty,
                "app_scale": problem_group.app_scale,
                "mode": problem_group.mode,
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
        }

        return problem_group, problems, response_data

    def _create_guest_response(
        self,
        generated_data: GeneratedProblemGroup,
        difficulty: str,
        app_scale: str,
        mode: str,
    ) -> Tuple[None, None, Dict[str, Any]]:
        """
        ゲスト用のレスポンスデータを作成する

        Args:
            generated_data: 生成されたデータ
            difficulty: 難易度
            app_scale: アプリ規模
            mode: モード

        Returns:
            (None, None, レスポンスデータ)
        """
        # ゲストトークン生成（32文字のランダム文字列）
        guest_token = secrets.token_urlsafe(32)

        response_data = {
            "kind": "guest",
            "guest_token": guest_token,
            "problem_group": {
                "title": generated_data["title"],
                "description": generated_data["description"],
                "difficulty": difficulty,
                "app_scale": app_scale,
                "mode": mode,
            },
            "problems": [
                {
                    "order_index": p["order_index"],
                    "problem_type": p["problem_type"],
                    "problem_body": p["problem_body"],
                }
                for p in generated_data["problems"]
            ],
        }

        return None, None, response_data


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
        # 入力サニタイゼーション
        answer_body = self._sanitize_answer(answer_body)

        # プロンプト構築
        prompt = build_grading_prompt(problem_type, problem_body, answer_body)

        # Gemini APIで採点
        try:
            response_text = self.gemini_client.generate_content(
                prompt=prompt,
                temperature=0.3,  # 採点は一貫性を重視するため低めに設定
                response_format="application/json",
                timeout=90,  # 採点処理は90秒のタイムアウトを設定
            )
        except GeminiClientError as e:
            raise AnswerGraderError(f"Gemini API呼び出しエラー: {e}") from e

        # JSONパース（前処理付き）
        try:
            json_str = self._extract_json_from_response(response_text)
            grading_result: GradingResult = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise AnswerGraderError(f"JSONパースエラー: {e}") from e

        # 結果が辞書型かチェック
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
        # NFC正規化（合字を分解）
        text = unicodedata.normalize("NFC", text)

        # 制御文字の除去（改行・タブ以外）
        cleaned = []
        for char in text:
            if ord(char) < 32 and char not in "\n\t":
                continue
            cleaned.append(char)

        return "".join(cleaned)

    @staticmethod
    def _extract_json_from_response(response_text: str) -> str:
        """
        Geminiレスポンスから JSON部分を抽出する

        Args:
            response_text: Gemini APIからのレスポンステキスト

        Returns:
            JSON文字列
        """
        # バッククォートで囲まれている場合を処理
        if response_text.strip().startswith("```"):
            # ```json から ``` までを抽出
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start != -1 and end > start:
                return response_text[start:end]
        return response_text.strip()

    def _validate_grading_result(self, result: GradingResult) -> None:
        """
        採点結果をバリデーションする

        Args:
            result: 採点結果

        Raises:
            AnswerGraderError: バリデーションエラー
        """
        # 必須フィールドチェック
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

        # プロンプト構築
        prompt = build_batch_grading_prompt(sanitized_items)

        # Gemini APIで一括採点
        try:
            response_text = self.gemini_client.generate_content(
                prompt=prompt,
                temperature=0.3,  # 採点は一貫性を重視するため低めに設定
                response_format="application/json",
                timeout=90,  # 一括採点は90秒のタイムアウトを設定
            )
        except GeminiClientError as e:
            raise AnswerGraderError(f"Gemini API呼び出しエラー: {e}") from e

        # JSONパース（前処理付き）
        try:
            json_str = self._extract_json_from_response(response_text)
            parsed_response = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise AnswerGraderError(f"JSONパースエラー: {e}") from e

        # 結果が辞書型かチェック
        if not isinstance(parsed_response, dict):
            raise AnswerGraderError(
                f"採点結果がオブジェクトではありません（型: {type(parsed_response).__name__}）"
            )

        # results 配列のバリデーション
        if "results" not in parsed_response or not isinstance(
            parsed_response["results"], list
        ):
            raise AnswerGraderError("results 配列が含まれていません")

        results = parsed_response["results"]

        # 各結果のバリデーション
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

        # order_index の一致チェック
        result_indices = {r["order_index"] for r in validated_results}
        if result_indices != expected_indices:
            missing = expected_indices - result_indices
            raise AnswerGraderError(
                f"採点結果に不足があります（不足: order_index {missing}）"
            )

        # order_index でソートして返す
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
        # order_index チェック
        if "order_index" not in result:
            raise AnswerGraderError("order_index が含まれていません")
        if not isinstance(result["order_index"], int):
            raise AnswerGraderError(
                f"order_index は整数である必要があります（実際: {result['order_index']}）"
            )

        # 必須フィールドチェック
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

        # grade の値チェック
        if not isinstance(result["grade"], int) or result["grade"] not in [0, 1, 2]:
            raise AnswerGraderError(
                f"order_index {result['order_index']}: grade は 0, 1, 2 のいずれかである必要があります（実際: {result['grade']}）"
            )
