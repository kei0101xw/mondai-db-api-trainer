import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../contexts/auth';
import RankingCard from '../../components/RankingCard/RankingCard';
import DashboardCard from '../../components/DashboardCard/DashboardCard';
import styles from './Home.module.css';
import { startGeneratePerf } from '../../shared/lib/perf';
import { getProblemGroupDetail } from '../../entities/problem/api';
import type { GenerateProblemResponse } from '../../entities/problem/types';

type LeftPanelTab = 'ranking' | 'mypage';

const Home = () => {
  const navigate = useNavigate();
  const { user, guestProblemGroupId } = useAuth();
  const [difficulty, setDifficulty] = useState<'easy' | 'medium' | 'hard'>('easy');
  // ログインユーザーはマイページをデフォルト表示
  const [leftPanelTab, setLeftPanelTab] = useState<LeftPanelTab>(user ? 'mypage' : 'ranking');
  const [isLoading, setIsLoading] = useState(false);

  // 進行中の問題を判定（ログインユーザーはuser.current_problem_group_id、ゲストはguestProblemGroupId）
  const hasProgressingProblem = user ? !!user.current_problem_group_id : !!guestProblemGroupId;

  const handleGenerate = async () => {
    if (hasProgressingProblem) {
      try {
        setIsLoading(true);
        const problemGroupId = user?.current_problem_group_id || guestProblemGroupId;
        if (!problemGroupId) {
          navigate('/solve');
          return;
        }

        const detailResponse = await getProblemGroupDetail(problemGroupId);

        const problemData: GenerateProblemResponse = {
          kind: 'persisted',
          problem_group: detailResponse.problem_group,
          problems: detailResponse.problems,
        };

        navigate('/solve', {
          state: {
            problemData,
            retryProblemGroupId: problemGroupId,
          },
        });
      } catch (error) {
        console.error('既存の問題取得に失敗しました:', error);
        navigate('/solve');
      } finally {
        setIsLoading(false);
      }
      return;
    }

    startGeneratePerf({
      difficulty,
      user_type: user ? 'user' : 'guest',
      user_id: user?.user_id ?? null,
    });
    navigate(`/solve?difficulty=${difficulty}`);
  };

  return (
    <div className={styles.container}>
      <div className={styles.leftPanel}>
        <div className={styles.header}>
          <h1>ホーム</h1>
          <p className={styles.description}>
            DB設計・API設計の練習問題を解いてスキルアップしましょう！
          </p>
        </div>

        {/* タブ切り替え */}
        <div className={styles.tabContainer}>
          <button
            className={`${styles.tab} ${leftPanelTab === 'ranking' ? styles.activeTab : ''}`}
            onClick={() => setLeftPanelTab('ranking')}
          >
            ランキング
          </button>
          {user && (
            <button
              className={`${styles.tab} ${leftPanelTab === 'mypage' ? styles.activeTab : ''}`}
              onClick={() => setLeftPanelTab('mypage')}
            >
              マイページ
            </button>
          )}
        </div>

        {/* タブコンテンツ */}
        {leftPanelTab === 'ranking' && <RankingCard />}
        {leftPanelTab === 'mypage' && user && <DashboardCard />}
      </div>
      <div className={styles.divider}></div>
      <div className={styles.rightPanel}>
        <h3>問題を生成する</h3>
        <p className={styles.description}>学習したい内容に合わせて、難易度を選択してください。</p>

        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault();
            handleGenerate();
          }}
        >
          {/* 難易度 */}
          <fieldset className={styles.formGroup} disabled={hasProgressingProblem}>
            <legend className={styles.label}>難易度</legend>
            <div className={styles.radioGroup}>
              <label htmlFor="difficulty-easy" className={styles.radioLabel}>
                <input
                  type="radio"
                  id="difficulty-easy"
                  name="difficulty"
                  value="easy"
                  checked={difficulty === 'easy'}
                  onChange={(e) => setDifficulty(e.target.value as 'easy')}
                  disabled={hasProgressingProblem}
                  className={styles.radio}
                />
                <span>Easy</span>
              </label>
              <label htmlFor="difficulty-medium" className={styles.radioLabel}>
                <input
                  type="radio"
                  id="difficulty-medium"
                  name="difficulty"
                  value="medium"
                  checked={difficulty === 'medium'}
                  onChange={(e) => setDifficulty(e.target.value as 'medium')}
                  disabled={hasProgressingProblem}
                  className={styles.radio}
                />
                <span>Medium</span>
              </label>
              <label htmlFor="difficulty-hard" className={styles.radioLabel}>
                <input
                  type="radio"
                  id="difficulty-hard"
                  name="difficulty"
                  value="hard"
                  checked={difficulty === 'hard'}
                  onChange={(e) => setDifficulty(e.target.value as 'hard')}
                  disabled={hasProgressingProblem}
                  className={styles.radio}
                />
                <span>Hard</span>
              </label>
            </div>
          </fieldset>

          <button type="submit" className={styles.generateButton} disabled={isLoading}>
            {isLoading
              ? 'ロード中...'
              : hasProgressingProblem
                ? 'すでに生成した問題を解く'
                : '問題を生成する'}
          </button>

          {!user && (
            <p className={styles.guestNotice}>
              ※ ログインしていない場合、1問しか解くことができません。
              <br />
              複数の問題を解いて学習を進めるには、<Link to="/register">ユーザー登録</Link>
              をしてください。
            </p>
          )}
        </form>
      </div>
    </div>
  );
};

export default Home;
