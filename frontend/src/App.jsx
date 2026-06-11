import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Landing from './Landing'; 
import Register from './Register';
import Dashboard from './Dashboard'; 
import HelpButton from './HelpButton';

function App() {
  return (
    <Router>  
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/register" element={<Register />} />
        <Route path="/Dashboard" element={<Dashboard />} />
      </Routes>
      <HelpButton />
    </Router>
  );
}

export default App;
