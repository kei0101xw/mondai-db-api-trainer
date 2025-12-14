import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts';
import { registerUser } from '../../entities/user/api';
import styles from './Register.module.css';

const RegisterUser = () => {
  const navigate = useNavigate();
  const { refreshUser } = useAuth();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');

    // パスワード確認
    if (password !== passwordConfirm) {
      setError('パスワードが一致しません');
      return;
    }

    setIsLoading(true);

    try {
      await registerUser({ name, email, password });
      await refreshUser();
      navigate('/');
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('登録に失敗しました');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.formWrapper}>
        <h1 className={styles.title}>新規登録</h1>
        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.formGroup}>
            <label htmlFor="name" className={styles.label}>
              名前
            </label>
            <input
              id="name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className={styles.input}
              placeholder="山田太郎"
              disabled={isLoading}
              autoComplete="name"
            />
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="email" className={styles.label}>
              メールアドレス
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className={styles.input}
              placeholder="example@email.com"
              disabled={isLoading}
              autoComplete="email"
            />
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="password" className={styles.label}>
              パスワード
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className={styles.input}
              placeholder="8文字以上のパスワード"
              minLength={8}
              disabled={isLoading}
              autoComplete="new-password"
            />
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="passwordConfirm" className={styles.label}>
              パスワード（確認）
            </label>
            <input
              id="passwordConfirm"
              type="password"
              value={passwordConfirm}
              onChange={(e) => setPasswordConfirm(e.target.value)}
              required
              className={styles.input}
              placeholder="パスワードを再入力"
              minLength={8}
              disabled={isLoading}
              autoComplete="new-password"
            />
          </div>

          {error && <div className={styles.error}>{error}</div>}

          <button type="submit" disabled={isLoading} className={styles.submitButton}>
            {isLoading ? '登録中...' : '登録'}
          </button>
        </form>

        <div className={styles.footer}>
          <p>
            既にアカウントをお持ちの方は
            <button
              onClick={() => navigate('/login')}
              className={styles.linkButton}
              disabled={isLoading}
            >
              ログイン
            </button>
          </p>
        </div>
      </div>
    </div>
  );
};

export default RegisterUser;
