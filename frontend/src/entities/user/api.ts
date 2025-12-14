/**
 * ユーザー関連のAPI関数
 */

import { apiClient } from '../../shared/api/client';
import type { User, UserResponse, RegisterRequest, LoginRequest } from './types';

/**
 * 現在のログインユーザー情報を取得
 */
export async function getCurrentUser(): Promise<User> {
  const response = await apiClient.get<UserResponse>('/auth/me');
  return response.user;
}

/**
 * ユーザー登録
 */
export async function registerUser(data: RegisterRequest): Promise<User> {
  const response = await apiClient.post<UserResponse>('/auth/register', data);
  return response.user;
}

/**
 * ログイン
 */
export async function loginUser(data: LoginRequest): Promise<User> {
  const response = await apiClient.post<UserResponse>('/auth/login', data);
  return response.user;
}

/**
 * ログアウト
 */
export async function logoutUser(): Promise<void> {
  await apiClient.post<{ ok: boolean }>('/auth/logout');
}
