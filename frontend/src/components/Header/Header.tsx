import styles from './Header.module.css';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts';
import logo from '../../assets/logo.png';

const Header = () => {
  const navigate = useNavigate();
  const { isAuthenticated, isLoading, logout, user } = useAuth();

  const goToHome = () => {
    navigate('/');
  };

  const goToLogin = () => {
    navigate('/login');
  };

  const goToRegister = () => {
    navigate('/register');
  };

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  return (
    <header className={styles.header}>
      <img src={logo} alt="mondAI" onClick={goToHome} className={styles.logo} />
      <div className={`${styles.buttonContainer} ${isLoading ? styles.loading : ''}`}>
        {isAuthenticated ? (
          <>
            <span className={styles.userName}>{user?.name} さん</span>
            <button
              onClick={handleLogout}
              className={`${styles.button} ${styles.logoutButton}`}
              disabled={isLoading}
            >
              ログアウト
            </button>
          </>
        ) : (
          <>
            <button
              onClick={goToLogin}
              className={`${styles.button} ${styles.loginButton}`}
              disabled={isLoading}
            >
              ログイン
            </button>
            <button
              onClick={goToRegister}
              className={`${styles.button} ${styles.registerButton}`}
              disabled={isLoading}
            >
              新規登録
            </button>
          </>
        )}
      </div>
    </header>
  );
};

export default Header;
