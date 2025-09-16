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
    // FOR DEBUGGING: Force clear storage on app start to prevent auto-login issues
    localStorage.removeItem('authToken');
    localStorage.removeItem('userData');
    sessionStorage.clear();
    
    // Set loading to false immediately - no dependencies needed
    setLoading(false);
    
    console.log('🚪 App loaded - showing login page');
    
    // Failsafe: Ensure loading is set to false after maximum 2 seconds
    const failsafeTimeout = setTimeout(() => {
      setLoading(false);
      console.log('🔧 Failsafe: Forced loading to false');
    }, 2000);
    
    return () => clearTimeout(failsafeTimeout);
  }, []);

  const handleLogin = async (token, userData) => {
    localStorage.setItem('authToken', token);
    localStorage.setItem('userData', JSON.stringify(userData));
    setUser(userData);
    
    // Initialize push notifications after successful login
    // try {
    //   console.log('🔔 Initializing push notifications...');
    //   await pushNotificationManager.initialize(true);
    // } catch (error) {
    //   console.error('Failed to initialize push notifications:', error);
    // }
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
      <div className="min-h-screen bg-gradient-to-br from-green-600 to-green-800 flex items-center justify-center">
        <div className="glass-card text-center max-w-md">
          <div className="loading-spinner mx-auto mb-4"></div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Loading Greenstar Health</h2>
          <p className="text-gray-600">Please wait while we prepare your healthcare dashboard...</p>
        </div>
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