export interface Problem {
  problem_id?: number; // ゲストの場合は存在しない
  problem_group_id?: number; // ゲストの場合は存在しない
  problem_type: 'db' | 'api';
  order_index: number;
  problem_body: string;
}

export interface ProblemGroup {
  problem_group_id?: number; // ゲストの場合は存在しない
  title: string;
  description: string;
  difficulty: 'easy' | 'medium' | 'hard';
  app_scale: 'small' | 'medium' | 'large';
  mode: 'both' | 'api_only' | 'db_only';
  created_at?: string; // ゲストの場合は存在しない
}

export interface GenerateProblemRequest {
  difficulty: 'easy' | 'medium' | 'hard';
  app_scale: 'small' | 'medium' | 'large';
  mode: 'both' | 'api_only' | 'db_only';
}

export interface GenerateProblemResponse {
  kind: 'persisted' | 'guest';
  guest_token?: string;
  problem_group: ProblemGroup;
  problems: Problem[];
}

export interface GradeAnswer {
  problem_id?: number; // ログインユーザーの場合
  order_index?: number; // ゲストユーザーの場合
  answer_body: string;
}

export interface GradeRequest {
  problem_group_id?: number; // ログインユーザーの場合
  guest_token?: string; // ゲストユーザーの場合
  answers: GradeAnswer[];
}

export interface ProblemSolution {
  version: number;
  solution_body: string;
  explanation: string;
}

export interface GradeResult {
  problem_ref: {
    problem_id?: number;
    order_index: number;
  };
  problem_type: 'db' | 'api';
  grade: number; // 0: ×, 1: △, 2: ○
  grade_display: string;
  solution: ProblemSolution;
  answer_id?: number; // ログインユーザーの場合
}

export interface GradeResponse {
  results: GradeResult[];
}

// 復習画面用の型定義
export interface AnswerSummary {
  total_problems: number;
  answered_problems: number;
  latest_grades: (number | null)[];
}

export interface ProblemGroupListItem {
  problem_group_id: number;
  title: string;
  description: string;
  difficulty: 'easy' | 'medium' | 'hard';
  app_scale: 'small' | 'medium' | 'large';
  mode: 'both' | 'api_only' | 'db_only';
  created_at: string;
  answer_summary: AnswerSummary;
}

export interface MyProblemGroupsResponse {
  items: ProblemGroupListItem[];
  next_cursor: string | null;
}

export interface MyProblemGroupsRequest {
  difficulty?: 'easy' | 'medium' | 'hard';
  mode?: 'both' | 'api_only' | 'db_only';
}

export interface AnswerHistory {
  answer_id: number;
  answer_body: string;
  grade: number;
  grade_display: string;
  created_at: string;
}

export interface ProblemGroupDetailResponse {
  problem_group: ProblemGroup & { problem_group_id: number; created_at: string };
  problems: (Problem & { problem_id: number })[];
  answers: Record<number, AnswerHistory[]>;
}
