/**
 * ランキング関連のAPI関数
 */

import { apiClient } from '../../shared/api/client';
import type { GetRankingParams, RankingResponse } from './types';

/**
 * ランキングを取得する
 *
 * @param params - 取得パラメータ
 * @returns ランキングデータ
 */
export async function getRanking(params: GetRankingParams = {}): Promise<RankingResponse> {
  const searchParams = new URLSearchParams();

  if (params.period) {
    searchParams.set('period', params.period);
  }
  if (params.score_type) {
    searchParams.set('score_type', params.score_type);
  }
  if (params.limit !== undefined) {
    searchParams.set('limit', String(params.limit));
  }

  const queryString = searchParams.toString();
  const endpoint = `/rankings${queryString ? `?${queryString}` : ''}`;

  return apiClient.get<RankingResponse>(endpoint);
}
