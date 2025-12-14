import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { generateProblem, gradeAnswers } from '../../entities/problem/api';
import type { GenerateProblemResponse } from '../../entities/problem/types';
import { useAuth } from '../../contexts';
import { CodeEditor } from '../../components/CodeEditor/CodeEditor';
import styles from './Solve.module.css';

// バリデーション関数
const parseDifficulty = (value: string | null): 'easy' | 'medium' | 'hard' => {
  if (value === 'easy' || value === 'medium' || value === 'hard') return value;
  return 'easy';
};

const parseAppScale = (value: string | null): 'small' | 'medium' | 'large' => {
  if (value === 'small' || value === 'medium' || value === 'large') return value;
  return 'small';
};

const parseMode = (value: string | null): 'both' | 'api_only' | 'db_only' => {
  if (value === 'both' || value === 'api_only' || value === 'db_only') return value;
  return 'both';
};

const Solve = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user, isAuthenticated, isLoading: isAuthLoading } = useAuth();
  const [problemData, setProblemData] = useState<GenerateProblemResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [answers, setAnswers] = useState<{ [key: number]: string }>({});
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    // 認証状態が確定するまで待つ
    if (isAuthLoading) return;

    const fetchProblem = async () => {
      try {
        setLoading(true);
        const difficulty = parseDifficulty(searchParams.get('difficulty'));
        const appScale = parseAppScale(searchParams.get('app_scale'));
        const mode = parseMode(searchParams.get('mode'));

        // SessionStorageのキーを生成（ログイン状態を含める）
        const userPrefix = isAuthenticated ? `user_${user?.user_id}` : 'guest';
        const storageKey = `mondai_problem_${userPrefix}_${difficulty}_${appScale}_${mode}`;

        // SessionStorageから既存の問題データを取得
        const cachedData = sessionStorage.getItem(storageKey);
        if (cachedData) {
          try {
            const parsed = JSON.parse(cachedData);
            setProblemData(parsed);
            setLoading(false);
            return;
          } catch (parseError) {
            // パースエラーの場合は無視して新規生成
            console.warn('SessionStorageのデータが不正です。新規生成します。', parseError);
            sessionStorage.removeItem(storageKey);
          }
        }

        // SessionStorageにデータがない場合のみAPI呼び出し
        const response = await generateProblem({
          difficulty,
          app_scale: appScale,
          mode,
        });

        setProblemData(response);

        // 生成した問題をSessionStorageに保存
        sessionStorage.setItem(storageKey, JSON.stringify(response));
      } catch (err) {
        setError(err instanceof Error ? err.message : '問題の生成に失敗しました');
      } finally {
        setLoading(false);
      }
    };

    fetchProblem();
  }, [searchParams, isAuthenticated, user?.user_id, isAuthLoading]);

  // 回答が入力されている場合、ページ離脱時に確認ダイアログを表示
  useEffect(() => {
    const hasAnswers = Object.values(answers).some((answer) => answer.trim() !== '');

    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasAnswers) {
        e.preventDefault();
        // Chrome では returnValue の設定が必要
        e.returnValue = '';
      }
    };

    if (hasAnswers) {
      window.addEventListener('beforeunload', handleBeforeUnload);
    }

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [answers]);

  const handleAnswerChange = (key: number, value: string) => {
    setAnswers((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const handleSubmit = async () => {
    if (!problemData) return;

    // 回答が入力されているかチェック
    // ゲストの場合は problem_id が undefined なので、order_index をフォールバックとして使用
    const hasAnswers = problemData.problems.every((problem, index) => {
      const key = problem.problem_id ?? index;
      return answers[key]?.trim();
    });

    if (!hasAnswers) {
      alert('すべての問題に回答してください');
      return;
    }

    try {
      setSubmitting(true);

      // デバッグ: problemDataの内容を確認（開発環境のみ）
      if (import.meta.env.DEV) {
        console.log('problemData:', problemData);
        console.log('answers:', answers);
      }

      // 採点リクエストを構築
      const gradeRequest =
        problemData.kind === 'persisted'
          ? {
              problem_group_id: problemData.problem_group.problem_group_id!,
              answers: problemData.problems.map((problem) => ({
                problem_id: problem.problem_id!,
                answer_body: answers[problem.problem_id!],
              })),
            }
          : {
              guest_token: problemData.guest_token!,
              answers: problemData.problems.map((problem, index) => {
                // ゲストの場合は配列インデックスをキーとして使用
                const answerKey = index;
                return {
                  order_index: problem.order_index,
                  answer_body: answers[answerKey],
                };
              }),
            };

      if (import.meta.env.DEV) {
        console.log('gradeRequest:', gradeRequest);
      }

      // 採点API呼び出し
      const gradeResponse = await gradeAnswers(gradeRequest);

      // 採点結果ページに遷移
      navigate('/result', {
        state: {
          problemData,
          gradeResults: gradeResponse.results,
          answers,
        },
      });
    } catch (err) {
      alert(err instanceof Error ? err.message : '採点に失敗しました');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className={styles.loadingContainer}>
        <p>問題を生成中...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.errorContainer}>
        <p className={styles.errorMessage}>{error}</p>
      </div>
    );
  }

  if (!problemData) {
    return null;
  }

  return (
    <div className={styles.container}>
      <div className={styles.leftPanel}>
        <div className={styles.problemHeader}>
          <h2>{problemData.problem_group.title}</h2>
          <div className={styles.badges}>
            <span className={styles.badge}>{problemData.problem_group.difficulty}</span>
            <span className={styles.badge}>{problemData.problem_group.app_scale}</span>
            <span className={styles.badge}>{problemData.problem_group.mode}</span>
          </div>
        </div>
        <div className={styles.problemDescription}>
          <p>{problemData.problem_group.description}</p>
        </div>
        <div className={styles.problemsList}>
          {problemData.problems.map((problem, index) => (
            <div key={problem.problem_id || index} className={styles.problemItem}>
              <div className={styles.problemTypeLabel}>
                {problem.problem_type === 'db' ? 'DB設計' : 'API設計'}
              </div>
              <div className={styles.problemBody}>
                <pre>{problem.problem_body}</pre>
              </div>
            </div>
          ))}
        </div>
      </div>
      <div className={styles.divider}></div>
      <div className={styles.rightPanel}>
        <h3>回答エリア</h3>
        {problemData.problems.map((problem, index) => {
          // ログインユーザーは problem_id、ゲストは配列インデックスをキーとして使用
          const answerKey = problem.problem_id ?? index;
          return (
            <div key={problem.problem_id || index} className={styles.answerSection}>
              <label className={styles.answerLabel}>
                {problem.problem_type === 'db' ? 'DB設計' : 'API設計'} 回答
              </label>
              <CodeEditor
                value={answers[answerKey] || ''}
                onChange={(value) => handleAnswerChange(answerKey, value)}
                language={problem.problem_type === 'db' ? 'sql' : 'plain'}
                placeholder={
                  problem.problem_type === 'db'
                    ? 'CREATE TABLE などのDDL文を記述してください...'
                    : 'API の擬似コードを記述してください...'
                }
              />
            </div>
          );
        })}
        <button className={styles.submitButton} onClick={handleSubmit} disabled={submitting}>
          {submitting ? '採点中...' : '採点する'}
        </button>
      </div>
    </div>
  );
};

export default Solve;
