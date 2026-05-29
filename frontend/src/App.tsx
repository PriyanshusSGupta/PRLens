import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import LoginPage from './pages/LoginPage';
import Dashboard from './pages/Dashboard';
import PRList from './pages/PRList';
import PRDetail from './pages/PRDetail';
import Evaluation from './pages/Evaluation';
import AuthCallback from './pages/AuthCallback';
import RepoPicker from './pages/RepoPicker';
import AISettings from './pages/AISettings';

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/auth/success" element={<AuthCallback />} />
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/prs" element={<PRList />} />
        <Route path="/prs/:id" element={<PRDetail />} />
        <Route path="/evaluations" element={<Evaluation />} />
        <Route path="/repos" element={<RepoPicker />} />
        <Route path="/ai" element={<AISettings />} />
      </Route>
    </Routes>
  );
}

export default App;
