/**
 * API通信の共通クライアント
 * 統一レスポンス形式に対応
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

/**
 * SessionStorageから問題キャッシュをクリアする
 */
export function clearProblemCache(): void {
  const keys = Object.keys(sessionStorage);
  keys.forEach((key) => {
    if (key.startsWith('mondai_problem_')) {
      sessionStorage.removeItem(key);
    }
  });
}

export interface ApiResponse<T> {
  data: T | null;
  error: {
    code: string;
    message: string;
    details?: unknown;
  } | null;
}

export class ApiError extends Error {
  code: string;
  details?: unknown;
  status?: number;

  constructor(code: string, message: string, details?: unknown, status?: number) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.details = details;
    this.status = status;
  }
}

interface RequestOptions extends RequestInit {
  data?: unknown;
}

/**
 * API リクエストを送信する共通関数
 */
async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { data, ...fetchOptions } = options;

  // デフォルト設定
  const config: RequestInit = {
    ...fetchOptions,
    credentials: 'include', // セッションCookieを含める
    headers: {
      'Content-Type': 'application/json',
      ...fetchOptions.headers,
    },
  };

  // リクエストボディの設定
  if (data) {
    config.body = JSON.stringify(data);
  }

  // CSRFトークンをCookieから取得して設定（POST/PUT/DELETE時）
  if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(config.method || '')) {
    const csrfToken = getCsrfToken();
    if (csrfToken) {
      config.headers = {
        ...config.headers,
        'X-CSRFToken': csrfToken,
      };
    }
  }

  const url = `${API_BASE_URL}${endpoint}`;

  try {
    const response = await fetch(url, config);
    const json: ApiResponse<T> = await response.json();

    // エラーレスポンスの場合
    if (!response.ok || json.error) {
      throw new ApiError(
        json.error?.code || 'UNKNOWN_ERROR',
        json.error?.message || 'An unknown error occurred',
        json.error?.details,
        response.status,
      );
    }

    // 成功時はdataを返す
    return json.data as T;
  } catch (error) {
    // ApiErrorの場合はそのまま再スロー
    if (error instanceof ApiError) {
      throw error;
    }

    // ネットワークエラー等の場合
    throw new ApiError('NETWORK_ERROR', 'Network error occurred', error, undefined);
  }
}

/**
 * CookieからCSRFトークンを取得
 */
function getCsrfToken(): string | null {
  const name = 'csrftoken';
  const cookies = document.cookie.split(';');
  for (const cookie of cookies) {
    const [key, value] = cookie.trim().split('=');
    if (key === name) {
      return decodeURIComponent(value);
    }
  }
  return null;
}

/**
 * CSRFトークンを取得する（初回のみ実行推奨）
 */
export async function fetchCsrfToken(): Promise<void> {
  await request('/auth/csrf');
}

// HTTPメソッド別のヘルパー関数
export const apiClient = {
  get: <T>(endpoint: string, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: 'GET' }),

  post: <T>(endpoint: string, data?: unknown, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: 'POST', data }),

  put: <T>(endpoint: string, data?: unknown, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: 'PUT', data }),

  delete: <T>(endpoint: string, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: 'DELETE' }),

  patch: <T>(endpoint: string, data?: unknown, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: 'PATCH', data }),
};
