import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate, useLocation } from 'react-router-dom';
import {
  askRequirementQuestion,
  generateProblem,
  getRequirements,
  gradeAnswers,
} from '../../entities/problem/api';
import type {
  GenerateProblemResponse,
  RequirementItem,
  RequirementTurn,
} from '../../entities/problem/types';
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

type SolveTab = 'problems' | 'inquiry' | 'requirements';

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
  const [activeTab, setActiveTab] = useState<SolveTab>('problems');
  const [requirementQuestion, setRequirementQuestion] = useState('');
  const [requirementTurns, setRequirementTurns] = useState<RequirementTurn[]>([]);
  const [requirementItems, setRequirementItems] = useState<RequirementItem[]>([]);
  const [requirementsLoading, setRequirementsLoading] = useState(false);
  const [requirementsError, setRequirementsError] = useState<string | null>(null);
  const [askingRequirement, setAskingRequirement] = useState(false);

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
    if (!problemData || !isAuthenticated) {
      setRequirementTurns([]);
      setRequirementItems([]);
      setRequirementsError(null);
      setRequirementsLoading(false);
      return;
    }

    const fetchRequirements = async () => {
      try {
        setRequirementsLoading(true);
        setRequirementsError(null);
        const response = await getRequirements(problemData.problem_group.problem_group_id);
        setRequirementTurns(response.turn_logs);
        setRequirementItems(response.requirement_items);
      } catch (err) {
        setRequirementsError(
          err instanceof Error ? err.message : '要件問い合わせ履歴の取得に失敗しました',
        );
      } finally {
        setRequirementsLoading(false);
      }
    };

    fetchRequirements();
  }, [problemData, isAuthenticated]);

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

  const handleRequirementSubmit = async () => {
    if (!problemData || !isAuthenticated) return;

    const trimmedQuestion = requirementQuestion.trim();
    if (!trimmedQuestion) {
      alert('質問内容を入力してください');
      return;
    }

    try {
      setAskingRequirement(true);
      setRequirementsError(null);
      const response = await askRequirementQuestion(problemData.problem_group.problem_group_id, {
        question: trimmedQuestion,
      });
      setRequirementTurns((prev) => [...prev, response.turn]);
      setRequirementItems((prev) => [...prev, ...response.requirement_items]);
      setRequirementQuestion('');
    } catch (err) {
      setRequirementsError(err instanceof Error ? err.message : '要件問い合わせに失敗しました');
    } finally {
      setAskingRequirement(false);
    }
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
          <div className={styles.tabs}>
            <button
              className={`${styles.tab} ${activeTab === 'problems' ? styles.activeTab : ''}`}
              onClick={() => setActiveTab('problems')}
              type="button"
            >
              問題一覧
            </button>
            <button
              className={`${styles.tab} ${activeTab === 'inquiry' ? styles.activeTab : ''}`}
              onClick={() => setActiveTab('inquiry')}
              type="button"
            >
              要件問い合わせ
            </button>
            <button
              className={`${styles.tab} ${activeTab === 'requirements' ? styles.activeTab : ''}`}
              onClick={() => setActiveTab('requirements')}
              type="button"
            >
              確定要件
            </button>
          </div>
          <div className={styles.tabContent}>
            {activeTab === 'problems' && (
              <div className={styles.problemsList}>
                {problemData.problems.map((problem, index) => (
                  <div key={problem.problem_id} className={styles.problemItem}>
                    <div className={styles.problemTypeLabel}>
                      {formatQuestionLabel(problem, index)}
                    </div>
                    <div className={styles.problemBody}>
                      <pre>{problem.problem_body}</pre>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'inquiry' && (
              <div className={styles.inquiryPanel}>
                {isAuthenticated ? (
                  <>
                    <div className={styles.questionComposer}>
                      <label htmlFor="requirement-question" className={styles.questionLabel}>
                        要件について質問する
                      </label>
                      <div className={styles.questionRow}>
                        <textarea
                          id="requirement-question"
                          className={styles.questionInput}
                          rows={1}
                          value={requirementQuestion}
                          onChange={(event) => setRequirementQuestion(event.target.value)}
                          placeholder="例: 退会したユーザーの投稿やコメントはどう扱いますか？"
                          disabled={askingRequirement}
                        />
                        <button
                          className={styles.questionButton}
                          onClick={handleRequirementSubmit}
                          disabled={askingRequirement}
                          type="button"
                        >
                          {askingRequirement ? '送信中...' : '質問する'}
                        </button>
                      </div>
                    </div>

                    {requirementsError && (
                      <p className={styles.requirementError}>{requirementsError}</p>
                    )}

                    <div className={styles.requirementHistory}>
                      <h4>回答履歴</h4>
                      {requirementsLoading ? (
                        <p className={styles.requirementStatus}>読み込み中...</p>
                      ) : requirementTurns.length === 0 ? (
                        <p className={styles.requirementStatus}>
                          まだ問い合わせはありません。曖昧な点があれば質問してみましょう。
                        </p>
                      ) : (
                        <div className={styles.turnList}>
                          {requirementTurns.map((turn) => (
                            <div key={turn.id} className={styles.turnItem}>
                              <div className={styles.turnQuestion}>
                                <span className={styles.turnLabel}>Q{turn.turn_no}</span>
                                <p>{turn.user_question}</p>
                              </div>
                              <div className={styles.turnAnswer}>
                                <span className={styles.turnLabel}>A</span>
                                <p>{turn.ai_answer}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </>
                ) : (
                  <div className={styles.requirementNotice}>
                    <p>要件問い合わせはログインユーザーのみ利用できます。</p>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'requirements' && (
              <div className={styles.requirementsPanel}>
                {isAuthenticated ? (
                  requirementsLoading ? (
                    <p className={styles.requirementStatus}>読み込み中...</p>
                  ) : requirementsError ? (
                    <p className={styles.requirementError}>{requirementsError}</p>
                  ) : requirementItems.length === 0 ? (
                    <p className={styles.requirementStatus}>
                      まだ確定した要件はありません。要件問い合わせで明確化するとここに表示されます。
                    </p>
                  ) : (
                    <div className={styles.requirementsList}>
                      {requirementItems.map((item, index) => (
                        <div key={item.id} className={styles.requirementItem}>
                          <div className={styles.requirementItemHeader}>
                            <span className={styles.requirementIndex}>要件 {index + 1}</span>
                          </div>
                          <p>{item.detail_text}</p>
                        </div>
                      ))}
                    </div>
                  )
                ) : (
                  <div className={styles.requirementNotice}>
                    <p>確定要件の表示はログインユーザーのみ利用できます。</p>
                  </div>
                )}
              </div>
            )}
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
