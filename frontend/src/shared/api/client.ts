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
 * CSRFエラーかどうかを判定
 * 明確にCSRF関連のエラーコードの場合、またはエラーコードがない403の場合にtrue
 */
function isCsrfError(status: number, errorCode?: string): boolean {
  if (status !== 403) {
    return false;
  }

  // 明確にCSRF関連のエラーコードの場合
  if (errorCode === 'CSRF_TOKEN_MISSING' || errorCode === 'CSRF_TOKEN_INVALID') {
    return true;
  }

  // エラーコードがない場合はDjangoのデフォルトCSRFエラーの可能性
  // 他の明確なエラーコード（GUEST_LIMIT_REACHED等）はCSRFエラーではない
  if (!errorCode || errorCode === 'UNKNOWN_ERROR') {
    return true;
  }

  return false;
}

/**
 * API リクエストを送信する共通関数
 * CSRFエラー時は自動的にトークンを再取得してリトライする
 */
async function request<T>(
  endpoint: string,
  options: RequestOptions = {},
  isRetry: boolean = false,
): Promise<T> {
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

  // CSRFトークンを設定（POST/PUT/DELETE/PATCH時）
  if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(config.method || '')) {
    if (!isRetry) {
      csrfToken = await fetchCsrfTokenDirect();
    }

    const token = getCsrfToken();
    if (token) {
      config.headers = {
        ...config.headers,
        'X-CSRFToken': token,
      };
    }
  }

  const url = `${API_BASE_URL}${endpoint}`;

  try {
    const response = await fetch(url, config);

    // 204 No Content の場合は空データを返す
    if (response.status === 204) {
      return null as T;
    }

    // Content-Type をチェック
    const contentType = response.headers.get('content-type');
    if (!contentType || !contentType.includes('application/json')) {
      // 非JSONレスポンスの場合
      const text = await response.text();

      // CSRFエラーの可能性がある403で、まだリトライしていない場合
      if (response.status === 403 && !isRetry) {
        // CSRFトークンを再取得してリトライ
        csrfToken = await fetchCsrfTokenDirect();
        return request<T>(endpoint, options, true);
      }

      throw new ApiError(
        'INVALID_RESPONSE',
        `Expected JSON response but got ${contentType || 'unknown'}`,
        { status: response.status, body: text.substring(0, 500) },
        response.status,
      );
    }

    const json: ApiResponse<T> = await response.json();

    // エラーレスポンスの場合
    if (!response.ok || json.error) {
      // CSRFエラーでまだリトライしていない場合、トークンを再取得してリトライ
      if (!isRetry && isCsrfError(response.status, json.error?.code)) {
        csrfToken = await fetchCsrfTokenDirect();
        return request<T>(endpoint, options, true);
      }

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
 * CSRFトークンをメモリに保持
 * クロスオリジン環境ではCookieからトークンを読み取れないため、
 * レスポンスボディから取得したトークンをメモリに保存する
 */
let csrfToken: string | null = null;

/**
 * メモリからCSRFトークンを取得
 */
function getCsrfToken(): string | null {
  return csrfToken;
}

/**
 * CSRFトークンを直接取得する内部関数（リトライ用）
 * request関数を使わず直接fetchしてCSRFトークンを取得する
 */
async function fetchCsrfTokenDirect(): Promise<string> {
  const url = `${API_BASE_URL}/auth/csrf`;
  const response = await fetch(url, {
    method: 'GET',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new ApiError(
      'CSRF_FETCH_FAILED',
      'Failed to fetch CSRF token',
      undefined,
      response.status,
    );
  }

  const json: ApiResponse<{ csrfToken: string }> = await response.json();
  if (!json.data?.csrfToken) {
    throw new ApiError('CSRF_FETCH_FAILED', 'CSRF token not found in response');
  }

  return json.data.csrfToken;
}

/**
 * CSRFトークンを取得してメモリに保存する（初回のみ実行推奨）
 * クロスオリジン環境ではCookieからトークンを読み取れないため、
 * レスポンスボディから取得してメモリに保存する
 */
export async function fetchCsrfToken(): Promise<void> {
  csrfToken = await fetchCsrfTokenDirect();
}

/**
 * CSRFトークンを更新してメモリに保存する
 * セッション変更後などにトークンが無効になった場合に使用
 */
export async function refreshCsrfToken(): Promise<void> {
  csrfToken = await fetchCsrfTokenDirect();
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
