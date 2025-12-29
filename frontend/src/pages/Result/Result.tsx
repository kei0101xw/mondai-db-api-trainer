import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import type { GenerateProblemResponse, GradeResult } from '../../entities/problem/types';
import { useAuth } from '../../contexts';
import { CodeEditor } from '../../components/CodeEditor/CodeEditor';
import styles from './Result.module.css';
import { completeProblemGroup, getModelAnswers } from '../../entities/problem/api';

type TabType = 'problem' | 'solution' | 'grading';

interface LocationState {
  problemData: GenerateProblemResponse;
  gradeResults: GradeResult[];
  answers: { [key: number]: string };
}

const Result = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, isAuthenticated, refreshUser, setGuestProblemGroupId } = useAuth();
  const state = location.state as LocationState | null;
  const [activeTab, setActiveTab] = useState<TabType>('grading');
  const [modelAnswers, setModelAnswers] = useState<Record<number, string>>({});
  const [isCompleting, setIsCompleting] = useState(false);
  const [modelAnswersError, setModelAnswersError] = useState<string | null>(null);
  const [isLoadingModelAnswers, setIsLoadingModelAnswers] = useState(true);
  const problemData = state?.problemData;
  const gradeResults = state?.gradeResults;
  const answers = state?.answers ?? {};

  useEffect(() => {
    if (!problemData) return;

    const fetchModelAnswers = async () => {
      try {
        setIsLoadingModelAnswers(true);
        const results = await Promise.all(
          problemData.problems.map(async (problem) => {
            const response = await getModelAnswers(problem.problem_id);
            const latest = response.model_answers[response.model_answers.length - 1];
            return [problem.problem_id, latest?.model_answer ?? ''] as const;
          }),
        );

        const map: Record<number, string> = {};
        results.forEach(([problemId, answer]) => {
          if (answer) {
            map[problemId] = answer;
          }
        });
        setModelAnswers(map);
        setModelAnswersError(null);
      } catch (err) {
        console.error(err);
        setModelAnswersError('模範解答の取得に失敗しました');
      } finally {
        setIsLoadingModelAnswers(false);
      }
    };

    fetchModelAnswers();
  }, [problemData]);

  if (!problemData || !gradeResults) {
    return (
      <div className={styles.errorContainer}>
        <p>採点結果が見つかりません</p>
      </div>
    );
  }

  const handleComplete = async () => {
    try {
      setIsCompleting(true);
      await completeProblemGroup(problemData.problem_group.problem_group_id, {
        guest_token: problemData.kind === 'guest' ? problemData.guest_token : undefined,
      });

      const userPrefix = isAuthenticated ? `user_${user?.user_id}` : 'guest';
      sessionStorage.removeItem(`mondai_problem_current_${userPrefix}`);

      // ゲストユーザーの場合、guestProblemGroupIdをクリア
      if (!isAuthenticated) {
        setGuestProblemGroupId(null);
      } else {
        // ログインユーザーの場合、バックエンドのセッション情報を更新するため refreshUser を呼び出す
        await refreshUser();
      }

      navigate('/');
    } catch (err) {
      alert(err instanceof Error ? err.message : '問題の完了に失敗しました');
    } finally {
      setIsCompleting(false);
    }
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'problem':
        return (
          <div className={styles.tabContent}>
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
        );

      case 'solution':
        return (
          <div className={styles.tabContent}>
            <h3>模範解答</h3>
            {gradeResults.map((result, index) => (
              <div key={index} className={styles.solutionItem}>
                <div className={styles.solutionHeader}>
                  <span className={styles.problemTypeLabel}>
                    {result.problem_type === 'db' ? 'DB設計' : 'API設計'}
                  </span>
                  <span className={styles.gradeLabel}>{result.grade_display}</span>
                </div>
                <div className={styles.solutionBody}>
                  <CodeEditor
                    value={
                      isLoadingModelAnswers
                        ? '模範解答を取得中です...'
                        : modelAnswers[result.problem_ref.problem_id] ||
                          modelAnswersError ||
                          '模範解答が見つかりません'
                    }
                    language={result.problem_type === 'db' ? 'sql' : 'plain'}
                    readOnly
                  />
                </div>
                <div className={styles.explanation}>
                  <h4>解説</h4>
                  <p>{result.explanation.explanation_body}</p>
                </div>
              </div>
            ))}
          </div>
        );

      case 'grading':
        return (
          <div className={styles.tabContent}>
            <h3>採点結果</h3>
            <div className={styles.gradingSummary}>
              {gradeResults.map((result, index) => {
                const gradeClass =
                  result.grade === 2
                    ? styles.gradeMaru
                    : result.grade === 1
                      ? styles.gradeSankaku
                      : styles.gradeBatsu;

                return (
                  <div key={index} className={styles.gradingItem}>
                    <div className={styles.gradingHeader}>
                      <span className={styles.problemTypeLabel}>
                        {result.problem_type === 'db' ? 'DB設計' : 'API設計'}
                      </span>
                      <span className={`${styles.gradeDisplay} ${gradeClass}`}>
                        {result.grade_display}
                      </span>
                    </div>
                    <div className={styles.gradingExplanation}>
                      <p>{result.explanation.explanation_body}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.leftPanel}>
        <div className={styles.tabs}>
          <button
            className={`${styles.tab} ${activeTab === 'grading' ? styles.activeTab : ''}`}
            onClick={() => setActiveTab('grading')}
          >
            採点
          </button>
          <button
            className={`${styles.tab} ${activeTab === 'problem' ? styles.activeTab : ''}`}
            onClick={() => setActiveTab('problem')}
          >
            問題
          </button>
          <button
            className={`${styles.tab} ${activeTab === 'solution' ? styles.activeTab : ''}`}
            onClick={() => setActiveTab('solution')}
          >
            模範解答
          </button>
        </div>
        {renderTabContent()}
      </div>
      <div className={styles.divider}></div>
      <div className={styles.rightPanel}>
        <h3>あなたの回答</h3>
        {problemData.problems.map((problem) => {
          const answerKey = problem.problem_id;
          return (
            <div key={answerKey} className={styles.answerSection}>
              <h4>{problem.problem_type === 'db' ? 'DB設計' : 'API設計'} 回答</h4>
              <CodeEditor
                value={answers[answerKey] || '（回答なし）'}
                language={problem.problem_type === 'db' ? 'sql' : 'plain'}
                readOnly
              />
            </div>
          );
        })}
        <div className={styles.buttonContainer}>
          <button onClick={handleComplete} className={styles.finishButton} disabled={isCompleting}>
            {isCompleting ? '処理中...' : '終了してホームに戻る'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default Result;
