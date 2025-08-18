import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import axios from 'axios';
import './App.css';
import LoginPage from './components/LoginPage';
import Dashboard from './components/Dashboard';
import PatientForm from './components/PatientForm';
import DoctorDashboard from './components/DoctorDashboard';
import VideoCall from './components/VideoCall';
import AdminDashboard from './components/AdminDashboard';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Axios interceptor to add auth token
axios.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('authToken');
    const userData = localStorage.getItem('userData');
    
    if (token && userData) {
      try {
        setUser(JSON.parse(userData));
      } catch (error) {
        console.error('Error parsing user data:', error);
        localStorage.removeItem('authToken');
        localStorage.removeItem('userData');
      }
    }
    setLoading(false);
  }, []);

  const handleLogin = (token, userData) => {
    localStorage.setItem('authToken', token);
    localStorage.setItem('userData', JSON.stringify(userData));
    setUser(userData);
  };

  const handleLogout = () => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('userData');
    setUser(null);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route 
            path="/login" 
            element={
              user ? (
                <Navigate to="/" replace />
              ) : (
                <LoginPage onLogin={handleLogin} />
              )
            } 
          />
          
          {user ? (
            <>
              <Route 
                path="/" 
                element={
                  user.role === 'provider' ? (
                    <Dashboard user={user} onLogout={handleLogout} />
                  ) : user.role === 'doctor' ? (
                    <DoctorDashboard user={user} onLogout={handleLogout} />
                  ) : user.role === 'admin' ? (
                    <AdminDashboard user={user} onLogout={handleLogout} />
                  ) : (
                    <div className="min-h-screen flex items-center justify-center">
                      <div className="text-center">
                        <h2 className="text-2xl font-bold text-gray-900 mb-4">
                          Invalid user role
                        </h2>
                        <button
                          onClick={handleLogout}
                          className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                        >
                          Logout
                        </button>
                      </div>
                    </div>
                  )
                } 
              />
              <Route 
                path="/patient-form" 
                element={
                  user.role === 'provider' ? (
                    <PatientForm user={user} />
                  ) : (
                    <Navigate to="/" replace />
                  )
                } 
              />
              <Route 
                path="/video-call/:sessionToken" 
                element={<VideoCall user={user} />} 
              />
            </>
          ) : (
            <Route path="*" element={<Navigate to="/login" replace />} />
          )}
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;