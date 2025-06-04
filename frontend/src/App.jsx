import React from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import BpmnCanvas from './BpmnCanvas'; // Assuming BpmnCanvas is in the same directory
import LogUploadPage from './pages/LogUploadPage'; // Path to the new LogUploadPage

function App() {
  return (
    <Router>
      <div className="app-container">
        <nav className="app-nav">
          <NavLink to="/" className="nav-link">BPMN Canvas</NavLink>
          <NavLink to="/upload-logs" className="nav-link">Upload Logs</NavLink>
        </nav>

        <main className="app-content">
          <Routes>
            <Route path="/" element={<BpmnCanvas />} />
            <Route path="/upload-logs" element={<LogUploadPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App; 