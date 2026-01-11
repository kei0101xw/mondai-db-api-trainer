import { apiClient } from '../../shared/api/client';
import type {
  GenerateProblemRequest,
  GenerateProblemResponse,
  GradeRequest,
  GradeResponse,
  MyProblemGroupsRequest,
  MyProblemGroupsResponse,
  ProblemGroupDetailResponse,
  DashboardData,
} from './types';

export const generateProblem = async (
  params: GenerateProblemRequest,
): Promise<GenerateProblemResponse> => {
  const searchParams = new URLSearchParams({ difficulty: params.difficulty });
  const response = await apiClient.get<GenerateProblemResponse>(
    `/problem-groups?${searchParams.toString()}`,
  );
  return response;
};

export const gradeAnswers = async (params: GradeRequest): Promise<GradeResponse> => {
  const response = await apiClient.post<GradeResponse>('/grade', params);
  return response;
};

/**
 * 自分の題材一覧を取得
 */
export const getMyProblemGroups = async (
  params?: MyProblemGroupsRequest,
): Promise<MyProblemGroupsResponse> => {
  const searchParams = new URLSearchParams();
  if (params?.difficulty) {
    searchParams.append('difficulty', params.difficulty);
  }
  const queryString = searchParams.toString();
  const url = `/problem-groups/mine${queryString ? `?${queryString}` : ''}`;

  const response = await apiClient.get<MyProblemGroupsResponse>(url);
  return response;
};

/**
 * 題材詳細を取得
 */
export const getProblemGroupDetail = async (
  problemGroupId: number,
  options?: { start?: boolean },
): Promise<ProblemGroupDetailResponse> => {
  const query = options?.start ? '?start=true' : '';
  const response = await apiClient.get<ProblemGroupDetailResponse>(
    `/problem-groups/${problemGroupId}${query}`,
  );
  return response;
};

/**
 * ダッシュボードデータを取得
 */
export const getDashboard = async (): Promise<DashboardData> => {
  const response = await apiClient.get<DashboardData>('/dashboard');
  return response;
};

export const completeProblemGroup = async (
  problemGroupId: number,
  payload?: { guest_token?: string },
) => {
  const response = await apiClient.post<{ ok: boolean }>(
    `/problem-groups/${problemGroupId}/complete`,
    payload,
  );
  return response;
};
