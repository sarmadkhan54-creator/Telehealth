import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import axios from 'axios';
import './App.css';
import LoginPage from './components/LoginPage';
import Dashboard from './components/Dashboard';
import PatientForm from './components/PatientForm';
import DoctorDashboard from './components/DoctorDashboard';
import AdminDashboard from './components/AdminDashboard';
import PWAInstallPrompt from './components/PWAInstallPrompt';
import { pushNotificationManager } from './utils/pushNotifications';

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
    // FOR DEBUGGING: Uncomment the next lines to force logout on app start
    // localStorage.removeItem('authToken');
    // localStorage.removeItem('userData');
    // sessionStorage.clear();
    
    const token = localStorage.getItem('authToken');
    const userData = localStorage.getItem('userData');
    
    console.log('🔍 Checking existing authentication...');
    console.log('Token exists:', !!token);
    console.log('User data exists:', !!userData);
    
    if (token && userData) {
      try {
        const parsedUserData = JSON.parse(userData);
        console.log('👤 Auto-logging in user:', parsedUserData.username);
        setUser(parsedUserData);
        
        // Initialize push notifications for existing logged-in user
        pushNotificationManager.initialize(true).catch(error => {
          console.error('Failed to initialize push notifications:', error);
        });
      } catch (error) {
        console.error('Error parsing user data:', error);
        localStorage.removeItem('authToken');
        localStorage.removeItem('userData');
      }
    } else {
      console.log('🚪 No existing authentication found - showing login page');
    }
    setLoading(false);
  }, []);

  const handleLogin = async (token, userData) => {
    localStorage.setItem('authToken', token);
    localStorage.setItem('userData', JSON.stringify(userData));
    setUser(userData);
    
    // Initialize push notifications after successful login
    try {
      console.log('🔔 Initializing push notifications...');
      await pushNotificationManager.initialize(true);
    } catch (error) {
      console.error('Failed to initialize push notifications:', error);
    }
  };

  const handleLogout = () => {
    // Clear all authentication data
    localStorage.removeItem('authToken');
    localStorage.removeItem('userData');
    
    // Clear any push notification subscriptions
    if (pushNotificationManager) {
      pushNotificationManager.unsubscribe().catch(error => {
        console.error('Error unsubscribing from push notifications:', error);
      });
    }
    
    // Reset user state
    setUser(null);
    
    // Clear any browser cache/session storage as well
    sessionStorage.clear();
    
    console.log('🚪 User logged out and all data cleared');
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
                          Access Denied
                        </h2>
                        <p className="text-gray-600 mb-4">
                          Your account role ({user.role}) does not have access to any dashboard.
                        </p>
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

            </>
          ) : (
            <Route path="*" element={<Navigate to="/login" replace />} />
          )}
        </Routes>
        
        {/* PWA Install Prompt - only show for logged-in users */}
        {user && <PWAInstallPrompt />}
      </BrowserRouter>
    </div>
  );
}

export default App;