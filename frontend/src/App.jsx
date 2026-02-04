import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import AppShell from './components/layout/AppShell';
import Dashboard from './pages/Dashboard';
import ScanDetails from './pages/ScanDetails';
import History from './pages/History';

function App() {
  return (
    <Router>
      <AppShell>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/scan/:id" element={<ScanDetails />} />
          <Route path="/history" element={<History />} />
        </Routes>
      </AppShell>
    </Router>
  );
}

export default App;
