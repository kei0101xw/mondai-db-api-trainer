import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate, useLocation } from 'react-router-dom';
import { generateProblem, gradeAnswers } from '../../entities/problem/api';
import type { GenerateProblemResponse } from '../../entities/problem/types';
import { useAuth } from '../../contexts';
import { CodeEditor } from '../../components/CodeEditor/CodeEditor';
import { FullScreenLoader } from '../../shared/ui/Loading';
import styles from './Solve.module.css';
import { completeGeneratePerf } from '../../shared/lib/perf';

const parseDifficulty = (value: string | null): 'easy' | 'medium' | 'hard' => {
  if (value === 'easy' || value === 'medium' || value === 'hard') return value;
  return 'easy';
};

// 再挑戦用のstate型
interface RetryLocationState {
  retryProblemGroupId?: number;
  problemData?: GenerateProblemResponse;
}

const Solve = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const location = useLocation();
  const {
    user,
    isAuthenticated,
    isLoading: isAuthLoading,
    refreshUser,
    setGuestProblemGroupId,
  } = useAuth();
  const [problemData, setProblemData] = useState<GenerateProblemResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [answers, setAnswers] = useState<{ [key: number]: string }>({});
  const [submitting, setSubmitting] = useState(false);
  const [hasFetched, setHasFetched] = useState(false);

  useEffect(() => {
    if (isAuthLoading) return;

    if (hasFetched) return;

    const state = location.state as RetryLocationState | null;
    if (state?.problemData && state?.retryProblemGroupId) {
      setProblemData(state.problemData);
      setLoading(false);
      setHasFetched(true);
      if (isAuthenticated) {
        refreshUser().catch(() => {});
      }
      window.history.replaceState({}, document.title);
      return;
    }

    const fetchProblem = async () => {
      try {
        setLoading(true);
        const difficulty = parseDifficulty(searchParams.get('difficulty'));

        const userPrefix = isAuthenticated ? `user_${user?.user_id}` : 'guest';
        const storageKey = `mondai_problem_current_${userPrefix}`;

        const cachedData = sessionStorage.getItem(storageKey);
        if (cachedData) {
          try {
            const parsed = JSON.parse(cachedData);
            setProblemData(parsed);
            setLoading(false);
            setHasFetched(true);
            return;
          } catch (parseError) {
            console.warn('SessionStorageのデータが不正です。新規生成します。', parseError);
            sessionStorage.removeItem(storageKey);
          }
        }

        let response;
        try {
          response = await generateProblem({ difficulty });
        } catch (err) {
          const apiError = err as { status?: number };
          if (apiError.status === 409 && user?.current_problem_group_id) {
            const { getProblemGroupDetail } = await import('../../entities/problem/api');
            const detailResponse = await getProblemGroupDetail(user.current_problem_group_id, {
              start: true,
            });
            const convertedResponse: GenerateProblemResponse = {
              kind: 'persisted',
              problem_group: detailResponse.problem_group,
              problems: detailResponse.problems,
            };
            sessionStorage.setItem(storageKey, JSON.stringify(convertedResponse));
            setProblemData(convertedResponse);
            setLoading(false);
            setHasFetched(true);
            return;
          }
          throw err;
        }

        setProblemData(response);
        setHasFetched(true);

        sessionStorage.setItem(storageKey, JSON.stringify(response));

        if (!isAuthenticated) {
          setGuestProblemGroupId(response.problem_group.problem_group_id);
        } else {
          await refreshUser();
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : '問題の生成に失敗しました');
        setHasFetched(true);
      } finally {
        setLoading(false);
      }
    };

    fetchProblem();
  }, [
    searchParams,
    isAuthenticated,
    user?.user_id,
    user?.current_problem_group_id,
    isAuthLoading,
    location.state,
    hasFetched,
    refreshUser,
    setGuestProblemGroupId,
  ]);

  useEffect(() => {
    if (!loading && problemData) {
      completeGeneratePerf(problemData.kind);
    }
  }, [loading, problemData]);

  useEffect(() => {
    const hasAnswers = Object.values(answers).some((answer) => answer.trim() !== '');

    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasAnswers) {
        e.preventDefault();
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

    const hasAnswers = problemData.problems.every((problem) => {
      const key = problem.problem_id;
      return answers[key]?.trim();
    });

    if (!hasAnswers) {
      alert('すべての問題に回答してください');
      return;
    }

    try {
      setSubmitting(true);

      if (import.meta.env.DEV) {
        console.log('problemData:', problemData);
        console.log('answers:', answers);
      }

      const gradeRequest =
        problemData.kind === 'persisted'
          ? {
              problem_group_id: problemData.problem_group.problem_group_id,
              answers: problemData.problems.map((problem) => ({
                problem_id: problem.problem_id,
                answer_body: answers[problem.problem_id],
              })),
            }
          : {
              guest_token: problemData.guest_token!,
              answers: problemData.problems.map((problem) => {
                return {
                  problem_id: problem.problem_id,
                  answer_body: answers[problem.problem_id],
                };
              }),
            };

      if (import.meta.env.DEV) {
        console.log('gradeRequest:', gradeRequest);
      }

      const gradeResponse = await gradeAnswers(gradeRequest);

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

  const formatQuestionLabel = (
    problem: GenerateProblemResponse['problems'][number],
    index: number,
  ) => {
    const orderNumber = problem.order_index ?? index + 1;
    const typeLabel = problem.problem_type === 'db' ? 'DB設計' : 'API設計';
    return `問${orderNumber}(${typeLabel})`;
  };

  if (loading) {
    return <FullScreenLoader isLoading={true} message="問題生成中..." />;
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
    <>
      {/* 採点中のローディング表示 */}
      <FullScreenLoader isLoading={submitting} message="採点中..." />

      <div className={styles.container}>
        <div className={styles.leftPanel}>
          <div className={styles.problemHeader}>
            <h2>{problemData.problem_group.title}</h2>
            <div className={styles.badges}>
              <span className={styles.badge}>{problemData.problem_group.difficulty}</span>
            </div>
          </div>
          <div className={styles.problemDescription}>
            <p>{problemData.problem_group.description}</p>
          </div>
          <div className={styles.problemsList}>
            {problemData.problems.map((problem, index) => (
              <div key={problem.problem_id} className={styles.problemItem}>
                <div className={styles.problemTypeLabel}>{formatQuestionLabel(problem, index)}</div>
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
            const answerKey = problem.problem_id;
            return (
              <div key={problem.problem_id} className={styles.answerSection}>
                <label className={styles.answerLabel}>{formatQuestionLabel(problem, index)}</label>
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
    </>
  );
};

export default Solve;
