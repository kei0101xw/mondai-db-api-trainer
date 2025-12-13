import { Route, Routes } from 'react-router-dom';
import Header from './components/Header/Header';
import Home from './pages/Home/Home';
import Solve from './pages/Solve/Solve';
import LoginUser from './pages/LoginUser/LoginUser';
import RegisterUser from './pages/RegisterUser/RegisterUser';

function App() {
  return (
    <>
      <Header />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/solve" element={<Solve />} />
        <Route path="/login" element={<LoginUser />} />
        <Route path="/register" element={<RegisterUser />} />
      </Routes>
    </>
  );
}

export default App;
