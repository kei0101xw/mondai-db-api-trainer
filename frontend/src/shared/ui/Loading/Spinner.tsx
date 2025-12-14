import styles from './Spinner.module.css';

interface SpinnerProps {
  /** スピナーのサイズ（デフォルト: 48px） */
  size?: number;
  /** スピナーの色（デフォルト: プライマリカラー） */
  color?: string;
  /** ボーダーの太さ（デフォルト: 4px） */
  borderWidth?: number;
}

/**
 * 汎用スピナーコンポーネント
 */
export const Spinner = ({ size = 48, color = '#3a4e72', borderWidth = 4 }: SpinnerProps) => {
  return (
    <div
      className={styles.spinner}
      style={{
        width: size,
        height: size,
        borderWidth: borderWidth,
        borderTopColor: color,
      }}
      role="status"
      aria-label="読み込み中"
    />
  );
};
