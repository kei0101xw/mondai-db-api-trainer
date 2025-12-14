import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../contexts';
import { getProblemGroupDetail } from '../../entities/problem/api';
import type { ProblemGroupDetailResponse, AnswerHistory } from '../../entities/problem/types';
import { CodeEditor } from '../../components/CodeEditor/CodeEditor';
import { Spinner } from '../../shared/ui/Loading';
import styles from './HistoryDetail.module.css';

type TabType = 'problem' | 'answer';

const HistoryDetail = () => {
  const { problemGroupId } = useParams<{ problemGroupId: string }>();
  const navigate = useNavigate();
  const { user, isLoading: isAuthLoading } = useAuth();
  const [data, setData] = useState<ProblemGroupDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('answer');
  const [selectedProblemIndex, setSelectedProblemIndex] = useState(0);

  useEffect(() => {
    if (!isAuthLoading && !user) {
      navigate('/login', { state: { from: `/history/${problemGroupId}` } });
      return;
    }

    if (!isAuthLoading && user && problemGroupId) {
      fetchDetail();
    }
  }, [user, isAuthLoading, problemGroupId, navigate]);

  const fetchDetail = async () => {
    if (!problemGroupId) return;

    setIsLoading(true);
    setError(null);
    try {
      const response = await getProblemGroupDetail(parseInt(problemGroupId, 10));
      setData(response);
    } catch (err) {
      setError('問題の詳細取得に失敗しました');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const getGradeEmoji = (grade: number): string => {
    switch (grade) {
      case 2:
        return '○';
      case 1:
        return '△';
      case 0:
        return '×';
      default:
        return '?';
    }
  };

  const getGradeClass = (grade: number): string => {
    switch (grade) {
      case 2:
        return styles.gradeMaru;
      case 1:
        return styles.gradeSankaku;
      case 0:
        return styles.gradeBatsu;
      default:
        return '';
    }
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString('ja-JP', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getDifficultyLabel = (difficulty: string): string => {
    switch (difficulty) {
      case 'easy':
        return 'Easy';
      case 'medium':
        return 'Medium';
      case 'hard':
        return 'Hard';
      default:
        return difficulty;
    }
  };

  const getModeLabel = (mode: string): string => {
    switch (mode) {
      case 'db_only':
        return 'DB設計';
      case 'api_only':
        return 'API設計';
      case 'both':
        return 'DB・API';
      default:
        return mode;
    }
  };

  if (isAuthLoading || isLoading) {
    return (
      <div className={styles.loadingContainer}>
        <Spinner />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className={styles.errorContainer}>
        <p>{error || '問題が見つかりません'}</p>
        <Link to="/history" className={styles.backButton}>
          一覧に戻る
        </Link>
      </div>
    );
  }

  const { problem_group, problems, answers } = data;
  const currentProblem = problems[selectedProblemIndex];
  const currentAnswers: AnswerHistory[] = currentProblem
    ? answers[currentProblem.problem_id] || []
    : [];

  return (
    <div className={styles.container}>
      <div className={styles.leftPanel}>
        <div className={styles.header}>
          <Link to="/history" className={styles.backLink}>
            ← 一覧に戻る
          </Link>
          <h1>{problem_group.title}</h1>
          <div className={styles.badges}>
            <span className={`${styles.badge} ${styles[`badge${problem_group.difficulty}`]}`}>
              {getDifficultyLabel(problem_group.difficulty)}
            </span>
            <span className={styles.badge}>{getModeLabel(problem_group.mode)}</span>
            <span className={styles.badge}>{problem_group.app_scale}</span>
          </div>
          <p className={styles.description}>{problem_group.description}</p>
          <p className={styles.date}>作成日: {formatDate(problem_group.created_at)}</p>
        </div>

        {/* 問題選択タブ（複数問題がある場合） */}
        {problems.length > 1 && (
          <div className={styles.problemTabs}>
            {problems.map((problem, index) => (
              <button
                key={problem.problem_id}
                className={`${styles.problemTab} ${selectedProblemIndex === index ? styles.activeTab : ''}`}
                onClick={() => setSelectedProblemIndex(index)}
              >
                {problem.problem_type === 'db' ? 'DB設計' : 'API設計'}
                {currentAnswers.length > 0 && (
                  <span
                    className={`${styles.tabGrade} ${getGradeClass(answers[problem.problem_id]?.[0]?.grade ?? -1)}`}
                  >
                    {getGradeEmoji(answers[problem.problem_id]?.[0]?.grade ?? -1)}
                  </span>
                )}
              </button>
            ))}
          </div>
        )}

        {/* タブ切り替え */}
        <div className={styles.tabs}>
          <button
            className={`${styles.tab} ${activeTab === 'answer' ? styles.activeTab : ''}`}
            onClick={() => setActiveTab('answer')}
          >
            回答履歴
          </button>
          <button
            className={`${styles.tab} ${activeTab === 'problem' ? styles.activeTab : ''}`}
            onClick={() => setActiveTab('problem')}
          >
            問題文
          </button>
        </div>

        {/* タブコンテンツ */}
        <div className={styles.tabContent}>
          {activeTab === 'problem' && currentProblem && (
            <div className={styles.problemContent}>
              <div className={styles.problemTypeLabel}>
                {currentProblem.problem_type === 'db' ? 'DB設計問題' : 'API設計問題'}
              </div>
              <pre className={styles.problemBody}>{currentProblem.problem_body}</pre>
            </div>
          )}

          {activeTab === 'answer' && (
            <div className={styles.answerContent}>
              {currentAnswers.length === 0 ? (
                <div className={styles.noAnswers}>
                  <p>この問題への回答はありません</p>
                </div>
              ) : (
                <div className={styles.answerList}>
                  {currentAnswers.map((answer, index) => (
                    <div key={answer.answer_id} className={styles.answerItem}>
                      <div className={styles.answerHeader}>
                        <div className={styles.answerMeta}>
                          <span className={styles.answerNumber}>
                            回答 #{currentAnswers.length - index}
                          </span>
                          <span className={styles.answerDate}>{formatDate(answer.created_at)}</span>
                        </div>
                        <span className={`${styles.answerGrade} ${getGradeClass(answer.grade)}`}>
                          {answer.grade_display}
                        </span>
                      </div>
                      <div className={styles.answerBody}>
                        <CodeEditor
                          value={answer.answer_body}
                          language={currentProblem?.problem_type === 'db' ? 'sql' : 'plain'}
                          readOnly
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div className={styles.divider}></div>

      <div className={styles.rightPanel}>
        <h3>アクション</h3>
        <div className={styles.actions}>
          <button
            onClick={() => {
              // 再挑戦機能（Solveページに問題データを渡す）
              navigate('/solve', {
                state: {
                  retryProblemGroupId: problem_group.problem_group_id,
                  problemData: {
                    kind: 'persisted',
                    problem_group,
                    problems,
                  },
                },
              });
            }}
            className={styles.retryButton}
          >
            再挑戦する
          </button>
          <Link to="/" className={styles.newButton}>
            新しい問題を解く
          </Link>
        </div>

        {/* 成績サマリー */}
        <div className={styles.summary}>
          <h4>成績サマリー</h4>
          <div className={styles.summaryList}>
            {problems.map((problem) => {
              const problemAnswers = answers[problem.problem_id] || [];
              const latestAnswer = problemAnswers[0];
              return (
                <div key={problem.problem_id} className={styles.summaryItem}>
                  <span className={styles.summaryLabel}>
                    {problem.problem_type === 'db' ? 'DB設計' : 'API設計'}
                  </span>
                  <div className={styles.summaryGrades}>
                    {latestAnswer ? (
                      <span
                        className={`${styles.summaryGrade} ${getGradeClass(latestAnswer.grade)}`}
                      >
                        {latestAnswer.grade_display}
                      </span>
                    ) : (
                      <span className={styles.summaryGrade}>-</span>
                    )}
                    <span className={styles.summaryCount}>({problemAnswers.length}回解答)</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};

export default HistoryDetail;
