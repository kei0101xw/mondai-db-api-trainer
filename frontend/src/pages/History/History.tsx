import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../contexts';
import { getMyProblemGroups } from '../../entities/problem/api';
import type { ProblemGroupListItem } from '../../entities/problem/types';
import { Spinner } from '../../shared/ui/Loading';
import styles from './History.module.css';

type DifficultyFilter = 'all' | 'easy' | 'medium' | 'hard';
type ModeFilter = 'all' | 'db_only' | 'api_only' | 'both';

const History = () => {
  const navigate = useNavigate();
  const { user, isLoading: isAuthLoading } = useAuth();
  const [problemGroups, setProblemGroups] = useState<ProblemGroupListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [difficultyFilter, setDifficultyFilter] = useState<DifficultyFilter>('all');
  const [modeFilter, setModeFilter] = useState<ModeFilter>('all');

  useEffect(() => {
    console.log('History useEffect:', { isAuthLoading, user });

    // 認証状態の確認後、未ログインならログインページへ
    if (!isAuthLoading && !user) {
      console.log('Redirecting to login...');
      navigate('/login', { state: { from: '/history' } });
      return;
    }

    if (!isAuthLoading && user) {
      console.log('Fetching problem groups...');
      fetchProblemGroups();
    }
  }, [user, isAuthLoading, navigate]);

  const fetchProblemGroups = async () => {
    console.log('fetchProblemGroups called');
    setIsLoading(true);
    setError(null);
    try {
      const params: {
        difficulty?: 'easy' | 'medium' | 'hard';
        mode?: 'db_only' | 'api_only' | 'both';
      } = {};
      if (difficultyFilter !== 'all') {
        params.difficulty = difficultyFilter;
      }
      if (modeFilter !== 'all') {
        params.mode = modeFilter;
      }
      console.log('Calling API with params:', params);
      const response = await getMyProblemGroups(params);
      console.log('API response:', response);
      setProblemGroups(response.items);
    } catch (err) {
      setError('問題一覧の取得に失敗しました');
      console.error('API error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  // フィルタ変更時に再取得
  useEffect(() => {
    if (!isAuthLoading && user) {
      fetchProblemGroups();
    }
  }, [difficultyFilter, modeFilter]);

  const getGradeEmoji = (grade: number | null): string => {
    switch (grade) {
      case 2:
        return '○';
      case 1:
        return '△';
      case 0:
        return '×';
      default:
        return '-';
    }
  };

  const getGradeClass = (grade: number | null): string => {
    switch (grade) {
      case 2:
        return styles.gradeMaru;
      case 1:
        return styles.gradeSankaku;
      case 0:
        return styles.gradeBatsu;
      default:
        return styles.gradeNone;
    }
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

  if (isAuthLoading) {
    return (
      <div className={styles.loadingContainer}>
        <Spinner />
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1>復習</h1>
        <p className={styles.description}>過去に解いた問題を確認・復習できます</p>
      </div>

      <div className={styles.filters}>
        <div className={styles.filterGroup}>
          <label className={styles.filterLabel}>難易度</label>
          <select
            value={difficultyFilter}
            onChange={(e) => setDifficultyFilter(e.target.value as DifficultyFilter)}
            className={styles.select}
          >
            <option value="all">すべて</option>
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>
        </div>

        <div className={styles.filterGroup}>
          <label className={styles.filterLabel}>問題タイプ</label>
          <select
            value={modeFilter}
            onChange={(e) => setModeFilter(e.target.value as ModeFilter)}
            className={styles.select}
          >
            <option value="all">すべて</option>
            <option value="db_only">DB設計のみ</option>
            <option value="api_only">API設計のみ</option>
            <option value="both">DB・API設計</option>
          </select>
        </div>
      </div>

      {isLoading ? (
        <div className={styles.loadingContainer}>
          <Spinner />
        </div>
      ) : error ? (
        <div className={styles.errorContainer}>
          <p>{error}</p>
          <button onClick={fetchProblemGroups} className={styles.retryButton}>
            再読み込み
          </button>
        </div>
      ) : problemGroups.length === 0 ? (
        <div className={styles.emptyContainer}>
          <p>まだ問題を解いていません</p>
          <Link to="/" className={styles.startButton}>
            問題を解く
          </Link>
        </div>
      ) : (
        <div className={styles.list}>
          {problemGroups.map((pg) => (
            <div
              key={pg.problem_group_id}
              className={styles.card}
              onClick={() => navigate(`/history/${pg.problem_group_id}`)}
            >
              <div className={styles.cardHeader}>
                <h3 className={styles.cardTitle}>{pg.title}</h3>
                <div className={styles.badges}>
                  <span className={`${styles.badge} ${styles[`badge${pg.difficulty}`]}`}>
                    {getDifficultyLabel(pg.difficulty)}
                  </span>
                  <span className={styles.badge}>{getModeLabel(pg.mode)}</span>
                </div>
              </div>

              <p className={styles.cardDescription}>{pg.description}</p>

              <div className={styles.cardFooter}>
                <div className={styles.grades}>
                  <span className={styles.gradeLabel}>結果:</span>
                  {pg.answer_summary.latest_grades.map((grade, idx) => (
                    <span key={idx} className={`${styles.gradeItem} ${getGradeClass(grade)}`}>
                      {getGradeEmoji(grade)}
                    </span>
                  ))}
                </div>
                <span className={styles.date}>{formatDate(pg.created_at)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default History;
