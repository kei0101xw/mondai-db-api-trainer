import styles from './Header.module.css';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts';
import logo from '../../assets/logo.png';

const Header = () => {
  const navigate = useNavigate();
  const location = useLocation();
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

  const goToHistory = () => {
    navigate('/history');
  };

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  const isActive = (path: string) => location.pathname === path;

  return (
    <header className={styles.header}>
      <div className={styles.leftSection}>
        <img src={logo} alt="mondAI" onClick={goToHome} className={styles.logo} />
        {isAuthenticated && (
          <nav className={styles.nav}>
            <button
              onClick={goToHome}
              className={`${styles.navLink} ${isActive('/') ? styles.navLinkActive : ''}`}
            >
              ホーム
            </button>
            <button
              onClick={goToHistory}
              className={`${styles.navLink} ${location.pathname.startsWith('/history') ? styles.navLinkActive : ''}`}
            >
              復習
            </button>
          </nav>
        )}
      </div>
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
