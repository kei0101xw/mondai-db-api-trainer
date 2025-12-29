export interface Problem {
  problem_id: number;
  problem_group_id: number;
  problem_type: 'db' | 'api';
  order_index: number;
  problem_body: string;
}

export interface ProblemGroup {
  problem_group_id: number;
  title: string;
  description: string;
  difficulty: 'easy' | 'medium' | 'hard';
  created_at?: string;
}

export interface GenerateProblemRequest {
  difficulty: 'easy' | 'medium' | 'hard';
}

export interface GenerateProblemResponse {
  kind: 'persisted' | 'guest';
  guest_token?: string;
  problem_group: ProblemGroup;
  problems: Problem[];
}

export interface GradeAnswer {
  problem_id: number;
  answer_body: string;
}

export interface GradeRequest {
  problem_group_id?: number;
  guest_token?: string;
  answers: GradeAnswer[];
}

export interface GradeResult {
  problem_ref: {
    problem_id: number;
    order_index: number;
  };
  problem_type: 'db' | 'api';
  grade: number; // 0: ×, 1: △, 2: ○
  grade_display: string;
  explanation: {
    version: number;
    explanation_body: string;
  };
  answer_id?: number;
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
  created_at: string;
  answer_summary: AnswerSummary;
}

export interface MyProblemGroupsResponse {
  items: ProblemGroupListItem[];
  next_cursor: string | null;
}

export interface MyProblemGroupsRequest {
  difficulty?: 'easy' | 'medium' | 'hard';
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

export interface ModelAnswer {
  problem_id: number;
  version: number;
  model_answer: string;
}

export interface ModelAnswersResponse {
  model_answers: ModelAnswer[];
}

// ダッシュボード用の型定義
export interface GradeDistribution {
  correct: number;
  partial: number;
  incorrect: number;
}

export interface DifficultyStats {
  count: number;
  average_grade: number;
}

export interface StreakData {
  current: number;
  longest: number;
}

export interface ActivityCalendarEntry {
  date: string;
  count: number;
  grade_sum: number;
}

export interface DashboardData {
  total_problem_groups: number;
  total_answers: number;
  average_grade: number;
  grade_distribution: GradeDistribution;
  difficulty_stats: Record<'easy' | 'medium' | 'hard', DifficultyStats>;
  streak: StreakData;
  activity_calendar: ActivityCalendarEntry[];
}
