import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts';
import { loginUser } from '../../entities/user/api';
import styles from './LoginUser.module.css';

const LoginUser = () => {
  const navigate = useNavigate();
  const { refreshUser } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await loginUser({ email, password });
      await refreshUser();
      navigate('/');
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('ログインに失敗しました');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.formWrapper}>
        <h1 className={styles.title}>ログイン</h1>
        <form onSubmit={handleSubmit} className={styles.form}>
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
              placeholder="パスワードを入力"
              disabled={isLoading}
            />
          </div>

          {error && <div className={styles.error}>{error}</div>}

          <button type="submit" disabled={isLoading} className={styles.submitButton}>
            {isLoading ? 'ログイン中...' : 'ログイン'}
          </button>
        </form>

        <div className={styles.footer}>
          <p>
            アカウントをお持ちでない方は
            <button
              onClick={() => navigate('/register')}
              className={styles.linkButton}
              disabled={isLoading}
            >
              新規登録
            </button>
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginUser;
