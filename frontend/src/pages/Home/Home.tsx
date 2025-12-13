import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import styles from './Home.module.css';

const Home = () => {
  const navigate = useNavigate();
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
          <div className={styles.formGroup}>
            <label className={styles.label}>難易度</label>
            <div className={styles.radioGroup}>
              <label className={styles.radioLabel}>
                <input
                  type="radio"
                  name="difficulty"
                  value="easy"
                  checked={difficulty === 'easy'}
                  onChange={(e) => setDifficulty(e.target.value as 'easy')}
                  className={styles.radio}
                />
                <span>Easy</span>
              </label>
              <label className={styles.radioLabel}>
                <input
                  type="radio"
                  name="difficulty"
                  value="medium"
                  checked={difficulty === 'medium'}
                  onChange={(e) => setDifficulty(e.target.value as 'medium')}
                  className={styles.radio}
                />
                <span>Medium</span>
              </label>
              <label className={styles.radioLabel}>
                <input
                  type="radio"
                  name="difficulty"
                  value="hard"
                  checked={difficulty === 'hard'}
                  onChange={(e) => setDifficulty(e.target.value as 'hard')}
                  className={styles.radio}
                />
                <span>Hard</span>
              </label>
            </div>
          </div>

          {/* アプリ規模 */}
          <div className={styles.formGroup}>
            <label className={styles.label}>アプリ規模</label>
            <div className={styles.radioGroup}>
              <label className={styles.radioLabel}>
                <input
                  type="radio"
                  name="appScale"
                  value="small"
                  checked={appScale === 'small'}
                  onChange={(e) => setAppScale(e.target.value as 'small')}
                  className={styles.radio}
                />
                <span>Small</span>
              </label>
              <label className={styles.radioLabel}>
                <input
                  type="radio"
                  name="appScale"
                  value="medium"
                  checked={appScale === 'medium'}
                  onChange={(e) => setAppScale(e.target.value as 'medium')}
                  className={styles.radio}
                />
                <span>Medium</span>
              </label>
              <label className={styles.radioLabel}>
                <input
                  type="radio"
                  name="appScale"
                  value="large"
                  checked={appScale === 'large'}
                  onChange={(e) => setAppScale(e.target.value as 'large')}
                  className={styles.radio}
                />
                <span>Large</span>
              </label>
            </div>
          </div>

          {/* 問題タイプ */}
          <div className={styles.formGroup}>
            <label className={styles.label}>問題タイプ</label>
            <div className={styles.radioGroup}>
              <label className={styles.radioLabel}>
                <input
                  type="radio"
                  name="mode"
                  value="both"
                  checked={mode === 'both'}
                  onChange={(e) => setMode(e.target.value as 'both')}
                  className={styles.radio}
                />
                <span>DB・API設計</span>
              </label>
              <label className={styles.radioLabel}>
                <input
                  type="radio"
                  name="mode"
                  value="api_only"
                  checked={mode === 'api_only'}
                  onChange={(e) => setMode(e.target.value as 'api_only')}
                  className={styles.radio}
                />
                <span>API設計のみ</span>
              </label>
              <label className={styles.radioLabel}>
                <input
                  type="radio"
                  name="mode"
                  value="db_only"
                  checked={mode === 'db_only'}
                  onChange={(e) => setMode(e.target.value as 'db_only')}
                  className={styles.radio}
                />
                <span>DB設計のみ</span>
              </label>
            </div>
          </div>

          <button type="submit" className={styles.generateButton}>
            問題を生成する
          </button>
        </form>
      </div>
    </div>
  );
};

export default Home;
