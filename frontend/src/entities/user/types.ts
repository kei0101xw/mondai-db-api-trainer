/**
 * ユーザー関連の型定義
 */

export interface User {
  user_id: number;
  email: string;
  name: string;
  icon_url?: string;
  created_at?: string;
  updated_at?: string;
  current_problem_group_id?: number | null;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface UserResponse {
  user: Omit<User, 'current_problem_group_id'>;
  current_problem_group_id?: number | null;
}
