import { apiClient } from '../../shared/api/client';
import type {
  GenerateProblemRequest,
  GenerateProblemResponse,
  GradeRequest,
  GradeResponse,
  MyProblemGroupsRequest,
  MyProblemGroupsResponse,
  ProblemGroupDetailResponse,
} from './types';

export const generateProblem = async (
  params: GenerateProblemRequest,
): Promise<GenerateProblemResponse> => {
  const response = await apiClient.post<GenerateProblemResponse>(
    '/problem-groups/generate',
    params,
  );
  return response;
};

export const gradeAnswers = async (params: GradeRequest): Promise<GradeResponse> => {
  const response = await apiClient.post<GradeResponse>('/problem-groups/grade', params);
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
  if (params?.mode) {
    searchParams.append('mode', params.mode);
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
): Promise<ProblemGroupDetailResponse> => {
  const response = await apiClient.get<ProblemGroupDetailResponse>(
    `/problem-groups/${problemGroupId}`,
  );
  return response;
};
