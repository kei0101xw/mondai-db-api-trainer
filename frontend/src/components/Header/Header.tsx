import styles from './Header.module.css';
import { useNavigate } from 'react-router-dom';
import logo from '../../assets/logo.png';

const Header = () => {
  const navigate = useNavigate();

  const goToHome = () => {
    navigate('/');
  };

  const goToLogin = () => {
    navigate('/login');
  };

  const goToRegister = () => {
    navigate('/register');
  };

  return (
    <header className={styles.header}>
      <img src={logo} alt="mondAI" onClick={goToHome} className={styles.logo} />
      <div className={styles.buttonContainer}>
        <button onClick={goToLogin} className={`${styles.button} ${styles.loginButton}`}>
          ログイン
        </button>
        <button onClick={goToRegister} className={`${styles.button} ${styles.registerButton}`}>
          新規登録
        </button>
      </div>
    </header>
  );
};

export default Header;
