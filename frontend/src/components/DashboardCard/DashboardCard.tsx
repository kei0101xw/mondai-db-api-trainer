import { useEffect, useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { getDashboard } from '../../entities/problem/api';
import type { DashboardData } from '../../entities/problem/types';
import styles from './DashboardCard.module.css';

const GRADE_COLORS = {
  correct: '#05c832',
  partial: '#3a4e72',
  incorrect: '#c82424ff',
};

const DIFFICULTY_COLORS = {
  easy: '#05c832',
  medium: '#3a4e72',
  hard: '#c82424ff',
};

/**
 * ダッシュボード（マイページ）カード
 * ログインユーザーの学習統計を表示
 */
const DashboardCard = () => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const response = await getDashboard();
        setData(response);
      } catch (err) {
        console.error('Failed to fetch dashboard:', err);
        setError('データの取得に失敗しました');
      } finally {
        setIsLoading(false);
      }
    };

    fetchDashboard();
  }, []);

  if (isLoading) {
    return (
      <div className={styles.card}>
        <div className={styles.loading}>読み込み中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.card}>
        <div className={styles.error}>{error}</div>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  // 成績分布のグラフデータ
  const gradeChartData = [
    { name: '○', value: data.grade_distribution.correct, color: GRADE_COLORS.correct },
    { name: '△', value: data.grade_distribution.partial, color: GRADE_COLORS.partial },
    { name: '×', value: data.grade_distribution.incorrect, color: GRADE_COLORS.incorrect },
  ];

  // 難易度別のグラフデータ
  const difficultyChartData = [
    {
      name: 'Easy',
      count: data.difficulty_stats.easy.count,
      avg: data.difficulty_stats.easy.average_grade,
    },
    {
      name: 'Medium',
      count: data.difficulty_stats.medium.count,
      avg: data.difficulty_stats.medium.average_grade,
    },
    {
      name: 'Hard',
      count: data.difficulty_stats.hard.count,
      avg: data.difficulty_stats.hard.average_grade,
    },
  ];

  const getGradeEmoji = (grade: number): string => {
    if (grade >= 1.5) return '○';
    if (grade >= 0.5) return '△';
    return '×';
  };

  return (
    <div className={styles.card}>
      {/* サマリー */}
      <div className={styles.summary}>
        <div className={styles.statItem}>
          <span className={styles.statValue}>{data.total_problem_groups}</span>
          <span className={styles.statLabel}>題材</span>
        </div>
        <div className={styles.statItem}>
          <span className={styles.statValue}>{data.total_answers}</span>
          <span className={styles.statLabel}>回答</span>
        </div>
        <div className={styles.statItem}>
          <span className={styles.statValue}>{getGradeEmoji(data.average_grade)}</span>
          <span className={styles.statLabel}>平均</span>
        </div>
      </div>

      {/* ストリーク */}
      <div className={styles.streakSection}>
        <div className={styles.streakItem}>
          <span className={styles.streakIcon}>🔥</span>
          <div className={styles.streakInfo}>
            <span className={styles.streakValue}>{data.streak.current}日</span>
            <span className={styles.streakLabel}>連続学習中</span>
          </div>
        </div>
        {data.streak.longest > 0 && (
          <div className={styles.streakItem}>
            <span className={styles.streakIcon}>🏆</span>
            <div className={styles.streakInfo}>
              <span className={styles.streakValue}>{data.streak.longest}日</span>
              <span className={styles.streakLabel}>最長記録</span>
            </div>
          </div>
        )}
      </div>

      {/* 成績分布（円グラフ） */}
      {data.total_answers > 0 && (
        <div className={styles.chartSection}>
          <h5 className={styles.chartTitle}>成績分布</h5>
          <div className={styles.pieChartContainer}>
            <ResponsiveContainer width="100%" height={120}>
              <PieChart>
                <Pie
                  data={gradeChartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={30}
                  outerRadius={50}
                  paddingAngle={2}
                  dataKey="value"
                >
                  {gradeChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip formatter={(value: number, name: string) => [`${value}回`, name]} />
              </PieChart>
            </ResponsiveContainer>
            <div className={styles.legendContainer}>
              {gradeChartData.map((entry) => (
                <div key={entry.name} className={styles.legendItem}>
                  <span className={styles.legendColor} style={{ backgroundColor: entry.color }} />
                  <span className={styles.legendLabel}>
                    {entry.name}: {entry.value}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 難易度別（棒グラフ） */}
      {data.total_answers > 0 && (
        <div className={styles.chartSection}>
          <h5 className={styles.chartTitle}>難易度別</h5>
          <ResponsiveContainer width="100%" height={100}>
            <BarChart data={difficultyChartData} layout="vertical">
              <XAxis type="number" hide />
              <YAxis type="category" dataKey="name" width={50} tick={{ fontSize: 12 }} />
              <Tooltip
                formatter={(value: number) => [`${value}問`]}
                labelFormatter={(label) => `${label}`}
              />
              <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                {difficultyChartData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={
                      DIFFICULTY_COLORS[entry.name.toLowerCase() as keyof typeof DIFFICULTY_COLORS]
                    }
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* カレンダーヒートマップ（簡易版） */}
      {data.activity_calendar.length > 0 && (
        <div className={styles.chartSection}>
          <h5 className={styles.chartTitle}>学習履歴（過去90日）</h5>
          <div className={styles.heatmapContainer}>
            {data.activity_calendar.slice(-30).map((entry) => {
              const intensity = Math.min(entry.count / 3, 1);
              return (
                <div
                  key={entry.date}
                  className={styles.heatmapCell}
                  style={{
                    backgroundColor: `rgba(34, 197, 94, ${0.2 + intensity * 0.8})`,
                  }}
                  title={`${entry.date}: ${entry.count}回答`}
                />
              );
            })}
          </div>
        </div>
      )}

      {data.total_answers === 0 && (
        <div className={styles.emptyState}>
          <p>まだ問題を解いていません</p>
          <p className={styles.emptyHint}>問題を解いて学習記録を残しましょう！</p>
        </div>
      )}
    </div>
  );
};

export default DashboardCard;
