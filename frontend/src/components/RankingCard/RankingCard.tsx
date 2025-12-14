import { useEffect, useState } from 'react';
import { getRanking } from '../../entities/ranking/api';
import type { RankingEntry } from '../../entities/ranking/types';
import styles from './RankingCard.module.css';

interface RankingCardProps {
  /** 表示件数 */
  limit?: number;
}

/**
 * 今日のトップ学習者ランキングを表示するカード
 */
const RankingCard = ({ limit = 5 }: RankingCardProps) => {
  const [rankings, setRankings] = useState<RankingEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchRanking = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const response = await getRanking({
          period: 'daily',
          score_type: 'problem_count',
          limit,
        });
        setRankings(response.rankings);
      } catch (err) {
        console.error('Failed to fetch ranking:', err);
        setError('ランキングの取得に失敗しました');
      } finally {
        setIsLoading(false);
      }
    };

    fetchRanking();
  }, [limit]);

  /**
   * 順位に応じたメダルアイコンを返す
   */
  const getRankIcon = (rank: number): string => {
    switch (rank) {
      case 1:
        return '🥇';
      case 2:
        return '🥈';
      case 3:
        return '🥉';
      default:
        return `${rank}.`;
    }
  };

  if (isLoading) {
    return (
      <div className={styles.card}>
        <h4 className={styles.title}>今日のトップ学習者</h4>
        <div className={styles.loading}>読み込み中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.card}>
        <h4 className={styles.title}>今日のトップ学習者</h4>
        <div className={styles.error}>{error}</div>
      </div>
    );
  }

  if (rankings.length === 0) {
    return (
      <div className={styles.card}>
        <h4 className={styles.title}>今日のトップ学習者</h4>
        <div className={styles.empty}>まだ今日の挑戦者がいません。最初の1人になりましょう！</div>
      </div>
    );
  }

  return (
    <div className={styles.card}>
      <h4 className={styles.title}>今日のトップ学習者</h4>
      <ul className={styles.rankingList}>
        {rankings.map((entry) => (
          <li key={entry.user_id} className={styles.rankingItem}>
            <span className={styles.rank}>{getRankIcon(entry.rank)}</span>
            <span className={styles.name}>{entry.name}</span>
            <span className={styles.score}>{entry.score}問</span>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default RankingCard;
