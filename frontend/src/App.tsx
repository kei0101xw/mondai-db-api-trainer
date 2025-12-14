import { Route, Routes } from 'react-router-dom';
import { AuthProvider } from './contexts';
import Header from './components/Header/Header';
import Home from './pages/Home/Home';
import Solve from './pages/Solve/Solve';
import Result from './pages/Result/Result';
import LoginUser from './pages/LoginUser/LoginUser';
import RegisterUser from './pages/RegisterUser/RegisterUser';

function App() {
  return (
    <AuthProvider>
      <Header />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/solve" element={<Solve />} />
        <Route path="/result" element={<Result />} />
        <Route path="/login" element={<LoginUser />} />
        <Route path="/register" element={<RegisterUser />} />
      </Routes>
    </AuthProvider>
  );
}

export default App;
