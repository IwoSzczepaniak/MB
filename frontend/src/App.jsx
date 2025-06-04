import React from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import BpmnCanvas from './BpmnCanvas';
import LogUploadPage from './pages/LogUploadPage';

function App() {
  return (
    <Router>
      <div className="app-container">
        <nav className="app-nav">
          <NavLink to="/" className="nav-link">Upload Logs</NavLink>
          <NavLink to="/visualize" className="nav-link">BPMN Canvas</NavLink>
        </nav>

        <main className="app-content">
          <Routes>
            <Route path="/" element={<LogUploadPage />} />
            <Route path="/visualize" element={<BpmnCanvas />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App; 