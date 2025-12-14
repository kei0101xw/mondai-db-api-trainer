import { apiClient } from '../../shared/api/client';
import type {
  GenerateProblemRequest,
  GenerateProblemResponse,
  GradeRequest,
  GradeResponse,
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
