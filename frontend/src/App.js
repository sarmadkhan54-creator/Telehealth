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
import { requestNotificationPermission, onMessageListener, listenForNotificationClicks } from './fcmService';

// Cross-device compatible backend URL configuration
const getBackendURL = () => {
  // If environment variable is set and not empty, use it
  if (process.env.REACT_APP_BACKEND_URL && process.env.REACT_APP_BACKEND_URL.trim() !== '') {
    console.log('🔗 Using configured backend URL:', process.env.REACT_APP_BACKEND_URL);
    return process.env.REACT_APP_BACKEND_URL;
  }
  
  // Use current domain (works for any deployment)
  const currentOrigin = window.location.origin;
  console.log('🌐 Using dynamic backend URL (same origin):', currentOrigin);
  return currentOrigin;
};

const BACKEND_URL = getBackendURL();
const API = `${BACKEND_URL}/api`;

console.log('✅ Final Backend URL:', BACKEND_URL);
console.log('✅ Final API URL:', API);

// Enhanced Axios interceptor for cross-device compatibility
axios.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
      // Add additional headers for better cross-device compatibility
      config.headers['Content-Type'] = 'application/json';
      config.headers['Accept'] = 'application/json';
      config.headers['Cache-Control'] = 'no-cache';
    }
    return config;
  },
  (error) => {
    console.error('🔧 Request interceptor error:', error);
    return Promise.reject(error);
  }
);

// Enhanced response interceptor for better error handling
axios.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    console.error('🔧 Response error:', {
      status: error.response?.status,
      statusText: error.response?.statusText,
      message: error.message,
      url: error.config?.url
    });

    if (error.response && error.response.status === 401) {
      console.log('🔐 Authentication failed - clearing credentials and redirecting');
      // Clear all authentication data from different storage locations
      localStorage.removeItem('authToken');
      localStorage.removeItem('userData');
      sessionStorage.clear();
      
      // Clear cookies if any (cross-device compatibility)
      document.cookie.split(";").forEach((c) => { 
        document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/"); 
      });
      
      // Force reload to clear any cached state
      setTimeout(() => {
        window.location.href = '/login';
      }, 100);
    }
    
    // Handle CORS and network errors for cross-device access
    if (error.code === 'ERR_NETWORK' || !error.response) {
      console.error('🌐 Network error - possible CORS or connectivity issue');
    }
    
    return Promise.reject(error);
  }
);

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Initialize FCM when user logs in
  useEffect(() => {
    if (user && user.id) {
      console.log('🔔 Initializing Firebase Cloud Messaging for user:', user.id);
      
      // Request FCM permission and get token
      requestNotificationPermission(user.id).then(token => {
        if (token) {
          console.log('✅ FCM initialized successfully');
        }
      });
      
      // Listen for foreground messages
      onMessageListener((payload) => {
        console.log('📨 [App] Foreground notification received:', payload);
        
        // You can show custom UI notifications here
        // Or let the service worker handle it
      });
      
      // Listen for notification clicks (from service worker)
      listenForNotificationClicks((data) => {
        console.log('🖱️ [App] Notification clicked, handling action:', data);
        
        // Handle different notification types
        if (data.type === 'video_call' && data.jitsi_url) {
          window.open(data.jitsi_url, '_blank');
        } else if (data.appointment_id) {
          // Navigate to appointment or trigger action
          console.log('📋 Opening appointment:', data.appointment_id);
        }
      });
    }
  }, [user]);

  useEffect(() => {
    // Enhanced authentication check for cross-device compatibility
    const checkAuthStatus = async () => {
      try {
        const token = localStorage.getItem('authToken');
        const userData = localStorage.getItem('userData');
        
        if (token && userData) {
          console.log('🔍 Found stored credentials, validating...');
          
          try {
            const parsedUser = JSON.parse(userData);
            
            // Validate token with backend (cross-device verification)
            const response = await axios.get(`${API}/users/profile`, {
              headers: { Authorization: `Bearer ${token}` }
            });
            
            if (response.status === 200) {
              setUser(parsedUser);
              console.log('✅ Cross-device authentication successful:', parsedUser.username);
            } else {
              throw new Error('Token validation failed');
            }
            
          } catch (validationError) {
            console.warn('⚠️ Token validation failed, clearing credentials:', validationError.message);
            localStorage.removeItem('authToken');
            localStorage.removeItem('userData');
            sessionStorage.clear();
          }
        } else {
          console.log('🚪 No stored credentials found - showing login page');
        }
      } catch (error) {
        console.error('🔧 Auth check error:', error);
        // Clear potentially corrupted data
        localStorage.removeItem('authToken');
        localStorage.removeItem('userData');
      } finally {
        setLoading(false);
      }
    };
    
    checkAuthStatus();
    
    // Failsafe timeout for slow network conditions
    const failsafeTimeout = setTimeout(() => {
      if (loading) {
        setLoading(false);
        console.log('⏰ Failsafe timeout - forced loading complete');
      }
    }, 5000); // Increased to 5 seconds for cross-device scenarios
    
    return () => clearTimeout(failsafeTimeout);
  }, []);

  const handleLogin = async (token, userData) => {
    try {
      // Store authentication data with enhanced cross-device compatibility
      localStorage.setItem('authToken', token);
      localStorage.setItem('userData', JSON.stringify(userData));
      
      // Also store in sessionStorage as backup for some devices
      sessionStorage.setItem('authToken', token);
      sessionStorage.setItem('userData', JSON.stringify(userData));
      
      console.log('💾 Authentication data stored for user:', userData.username);
      
      setUser(userData);
      
      // Set up activity tracking for session management
      const updateLastActivity = () => {
        const updatedUserData = {
          ...userData,
          lastActivity: new Date().toISOString()
        };
        localStorage.setItem('userData', JSON.stringify(updatedUserData));
      };
      
      // Update activity every 30 seconds
      const activityInterval = setInterval(updateLastActivity, 30000);
      
      // Store interval ID to clear on logout
      window.activityTracker = activityInterval;
      
      console.log('✅ Login completed successfully');
      
    } catch (error) {
      console.error('🔧 Error during login setup:', error);
    }
  };

  const handleLogout = () => {
    try {
      console.log('🚪 Starting logout process...');
      
      // Clear all authentication data from multiple storage locations
      localStorage.removeItem('authToken');
      localStorage.removeItem('userData');
      sessionStorage.removeItem('authToken');
      sessionStorage.removeItem('userData');
      
      // Clear any push notification subscriptions
      if (pushNotificationManager) {
        pushNotificationManager.unsubscribe().catch(error => {
          console.error('Error unsubscribing from push notifications:', error);
        });
      }
      
      // Clear activity tracker
      if (window.activityTracker) {
        clearInterval(window.activityTracker);
        delete window.activityTracker;
      }
      
      // Clear all session storage and local storage
      sessionStorage.clear();
      
      // Clear any cached API responses
      if (window.caches) {
        caches.keys().then(names => {
          names.forEach(name => caches.delete(name));
        });
      }
      
      // Reset user state
      setUser(null);
      
      console.log('✅ Logout completed - all data cleared');
      
    } catch (error) {
      console.error('🔧 Error during logout:', error);
      // Force reset even if there's an error
      setUser(null);
    }
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