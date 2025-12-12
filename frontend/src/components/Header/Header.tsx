import styles from './Header.module.css';
import { useNavigate } from 'react-router-dom';

const Header = () => {
  const navigate = useNavigate();

  const goToHome = () => {
    navigate('/');
  };

  return (
    <header className={styles.header}>
      <button onClick={goToHome}>mondAI</button>
    </header>
  );
};

export default Header;
