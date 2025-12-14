import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../contexts/auth';
import RankingCard from '../../components/RankingCard/RankingCard';
import styles from './Home.module.css';

const Home = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [difficulty, setDifficulty] = useState<'easy' | 'medium' | 'hard'>('easy');
  const [appScale, setAppScale] = useState<'small' | 'medium' | 'large'>('small');
  const [mode, setMode] = useState<'both' | 'api_only' | 'db_only'>('both');

  const handleGenerate = () => {
    // パラメータをクエリパラメータとして渡してsolveページに遷移
    navigate(`/solve?difficulty=${difficulty}&app_scale=${appScale}&mode=${mode}`);
  };

  return (
    <div className={styles.container}>
      <div className={styles.leftPanel}>
        <h2>mondAI</h2>
        <p>DB設計・API設計の練習問題を解いてスキルアップしましょう！</p>
        <RankingCard />
      </div>
      <div className={styles.divider}></div>
      <div className={styles.rightPanel}>
        <h3>問題を生成する</h3>
        <p className={styles.description}>
          学習したい内容に合わせて、難易度・アプリ規模・問題タイプを設定してください。
        </p>

        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault();
            handleGenerate();
          }}
        >
          {/* 難易度 */}
          <fieldset className={styles.formGroup}>
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
                  className={styles.radio}
                />
                <span>Hard</span>
              </label>
            </div>
          </fieldset>

          {/* アプリ規模 */}
          <fieldset className={styles.formGroup}>
            <legend className={styles.label}>アプリ規模</legend>
            <div className={styles.radioGroup}>
              <label htmlFor="appScale-small" className={styles.radioLabel}>
                <input
                  type="radio"
                  id="appScale-small"
                  name="appScale"
                  value="small"
                  checked={appScale === 'small'}
                  onChange={(e) => setAppScale(e.target.value as 'small')}
                  className={styles.radio}
                />
                <span>Small</span>
              </label>
              <label htmlFor="appScale-medium" className={styles.radioLabel}>
                <input
                  type="radio"
                  id="appScale-medium"
                  name="appScale"
                  value="medium"
                  checked={appScale === 'medium'}
                  onChange={(e) => setAppScale(e.target.value as 'medium')}
                  className={styles.radio}
                />
                <span>Medium</span>
              </label>
              <label htmlFor="appScale-large" className={styles.radioLabel}>
                <input
                  type="radio"
                  id="appScale-large"
                  name="appScale"
                  value="large"
                  checked={appScale === 'large'}
                  onChange={(e) => setAppScale(e.target.value as 'large')}
                  className={styles.radio}
                />
                <span>Large</span>
              </label>
            </div>
          </fieldset>

          {/* 問題タイプ */}
          <fieldset className={styles.formGroup}>
            <legend className={styles.label}>問題タイプ</legend>
            <div className={styles.radioGroup}>
              <label htmlFor="mode-both" className={styles.radioLabel}>
                <input
                  type="radio"
                  id="mode-both"
                  name="mode"
                  value="both"
                  checked={mode === 'both'}
                  onChange={(e) => setMode(e.target.value as 'both')}
                  className={styles.radio}
                />
                <span>DB・API設計</span>
              </label>
              <label htmlFor="mode-api_only" className={styles.radioLabel}>
                <input
                  type="radio"
                  id="mode-api_only"
                  name="mode"
                  value="api_only"
                  checked={mode === 'api_only'}
                  onChange={(e) => setMode(e.target.value as 'api_only')}
                  className={styles.radio}
                />
                <span>API設計のみ</span>
              </label>
              <label htmlFor="mode-db_only" className={styles.radioLabel}>
                <input
                  type="radio"
                  id="mode-db_only"
                  name="mode"
                  value="db_only"
                  checked={mode === 'db_only'}
                  onChange={(e) => setMode(e.target.value as 'db_only')}
                  className={styles.radio}
                />
                <span>DB設計のみ</span>
              </label>
            </div>
          </fieldset>

          <button type="submit" className={styles.generateButton}>
            問題を生成する
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
