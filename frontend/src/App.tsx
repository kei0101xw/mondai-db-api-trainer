import { Route, Routes } from 'react-router-dom';
import Header from './components/Header/Header';
import Home from './pages/Home/Home';
import Solve from './pages/Solve/Solve';

function App() {
  return (
    <>
      <Header />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/solve" element={<Solve />} />
      </Routes>
    </>
  );
}

export default App;
