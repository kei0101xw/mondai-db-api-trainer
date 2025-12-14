/**
 * ランキング関連の型定義
 */

/** 集計期間 */
export type Period = 'daily' | 'weekly' | 'monthly' | 'all';

/** スコア計算方式 */
export type ScoreType = 'problem_count' | 'correct_count' | 'grade_sum';

/** ランキングエントリ */
export interface RankingEntry {
  rank: number;
  user_id: number;
  name: string;
  score: number;
}

/** ランキング取得パラメータ */
export interface GetRankingParams {
  period?: Period;
  score_type?: ScoreType;
  limit?: number;
}

/** ランキングレスポンス */
export interface RankingResponse {
  period: Period;
  score_type: ScoreType;
  rankings: RankingEntry[];
}
