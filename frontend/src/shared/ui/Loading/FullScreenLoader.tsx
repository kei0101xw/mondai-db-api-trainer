import { Spinner } from './Spinner';
import styles from './FullScreenLoader.module.css';

interface FullScreenLoaderProps {
  /** ローディング中かどうか */
  isLoading: boolean;
  /** 表示するメッセージ */
  message?: string;
}

/**
 * 全画面オーバーレイローディング
 * 問題生成中や採点中など、長時間の処理時に使用
 */
export const FullScreenLoader = ({
  isLoading,
  message = '読み込み中...',
}: FullScreenLoaderProps) => {
  if (!isLoading) {
    return null;
  }

  return (
    <div className={styles.overlay} role="dialog" aria-modal="true" aria-label={message}>
      <div className={styles.content}>
        <Spinner size={64} borderWidth={5} />
        <p className={styles.message} aria-live="polite">
          {message}
        </p>
      </div>
    </div>
  );
};
