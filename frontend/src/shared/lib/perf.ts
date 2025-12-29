import { clearProblemCache } from '../api/client';

type PerfStartPayload = {
  difficulty: 'easy' | 'medium' | 'hard';
  user_type: 'user' | 'guest';
  user_id?: number | null;
};

type PerfRecord = PerfStartPayload & {
  id: string;
  start_ms: number;
  start_iso: string;
};

const PERF_STORAGE_KEY = 'mondai_perf_current';
const isPerfEnabled: boolean = import.meta.env.VITE_ENABLE_GENERATE_PERF === 'true';

function nowIso(): string {
  return new Date().toISOString();
}

function genId(): string {
  return `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function saveCsv(content: string, filename: string): void {
  try {
    const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch (e) {
    // CSV保存に失敗してもUIは変えない
    console.warn('CSV 自動保存に失敗しました', e);
  }
}

export function startGeneratePerf(payload: PerfStartPayload): void {
  if (!isPerfEnabled) return;

  // 既存の問題キャッシュをクリアして、API呼び出しを計測対象にする
  clearProblemCache();

  const record: PerfRecord = {
    id: genId(),
    start_ms: Date.now(),
    start_iso: nowIso(),
    ...payload,
  };
  sessionStorage.setItem(PERF_STORAGE_KEY, JSON.stringify(record));
}

export function completeGeneratePerf(resultKind: 'persisted' | 'guest'): void {
  if (!isPerfEnabled) return;

  const raw = sessionStorage.getItem(PERF_STORAGE_KEY);
  if (!raw) return; // 計測対象外の遷移

  let record: PerfRecord | null = null;
  try {
    record = JSON.parse(raw) as PerfRecord;
  } catch {
    // 破損していたら諦める
    sessionStorage.removeItem(PERF_STORAGE_KEY);
    return;
  }

  // 計測完了
  const endMs = Date.now();
  const durationMs = endMs - record.start_ms;
  const endIso = nowIso();

  // CSV内容（ヘッダ + 1行）
  const header = [
    'id',
    'timestamp',
    'user_type',
    'user_id',
    'difficulty',
    'result_kind',
    'start_iso',
    'end_iso',
    'duration_ms',
  ].join(',');

  const row = [
    record.id,
    // ダウンロードファイル名に近い形の人間可読な時刻
    new Date().toLocaleString(),
    record.user_type,
    record.user_id ?? '',
    record.difficulty,
    resultKind,
    record.start_iso,
    endIso,
    durationMs,
  ]
    .map((v) => String(v).replace(/\n|\r|,/g, ' '))
    .join(',');

  const csv = `${header}\n${row}\n`;
  const filename = `mondai-generate-perf-${new Date().toISOString().replace(/[:.]/g, '-')}.csv`;

  // 自動ダウンロード（UI変更なし）
  saveCsv(csv, filename);

  // 計測完了後はクリアして再発火を防ぐ
  sessionStorage.removeItem(PERF_STORAGE_KEY);
}
