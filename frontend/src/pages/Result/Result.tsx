import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import type { GenerateProblemResponse, GradeResult } from '../../entities/problem/types';
import { useAuth } from '../../contexts';
import styles from './Result.module.css';

type TabType = 'problem' | 'solution' | 'grading';

interface LocationState {
  problemData: GenerateProblemResponse;
  gradeResults: GradeResult[];
  answers: { [key: number]: string };
}

const Result = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuth();
  const state = location.state as LocationState;
  const [activeTab, setActiveTab] = useState<TabType>('grading');

  if (!state || !state.problemData || !state.gradeResults) {
    return (
      <div className={styles.errorContainer}>
        <p>採点結果が見つかりません</p>
      </div>
    );
  }

  const { problemData, gradeResults, answers } = state;

  const getGradeEmoji = (grade: number) => {
    switch (grade) {
      case 2:
        return '◯';
      case 1:
        return '△';
      case 0:
        return '×';
      default:
        return '?';
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
                  <span className={styles.gradeLabel}>{getGradeEmoji(result.grade)}</span>
                </div>
                <div className={styles.solutionBody}>
                  <pre>{result.solution.solution_body}</pre>
                </div>
                <div className={styles.explanation}>
                  <h4>解説</h4>
                  <p>{result.solution.explanation}</p>
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
                        {getGradeEmoji(result.grade)}
                      </span>
                    </div>
                    <div className={styles.gradingExplanation}>
                      <p>{result.solution.explanation}</p>
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
        {problemData.problems.map((problem, index) => {
          const answerKey = problem.problem_id || index;
          return (
            <div key={answerKey} className={styles.answerSection}>
              <h4>{problem.problem_type === 'db' ? 'DB設計' : 'API設計'} 回答</h4>
              <div className={styles.answerDisplay}>
                <pre>{answers[answerKey] || '（回答なし）'}</pre>
              </div>
            </div>
          );
        })}
        <div className={styles.buttonContainer}>
          <button
            onClick={() => {
              // SessionStorageから問題データをクリア（Solveと同じキー構造で削除）
              const { difficulty, app_scale, mode } = problemData.problem_group;
              const userPrefix = isAuthenticated ? `user_${user?.user_id}` : 'guest';
              const storageKey = `mondai_problem_${userPrefix}_${difficulty}_${app_scale}_${mode}`;
              sessionStorage.removeItem(storageKey);
              navigate('/');
            }}
            className={styles.finishButton}
          >
            終了してホームに戻る
          </button>
        </div>
      </div>
    </div>
  );
};

export default Result;
