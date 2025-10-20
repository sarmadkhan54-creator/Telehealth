import React, { useState } from 'react';
import axios from 'axios';
import { Eye, EyeOff, UserCheck, Shield } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const LoginPage = ({ onLogin }) => {
  const [formData, setFormData] = useState({
    username: '',
    password: ''
  });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      console.log('🔐 Attempting login for:', formData.username);
      
      // Clear any existing authentication data first
      localStorage.removeItem('authToken');
      localStorage.removeItem('userData');
      sessionStorage.clear();
      
      const response = await axios.post(`${API}/login`, formData, {
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        timeout: 10000, // 10 second timeout for slow connections
      });
      
      const { access_token, user } = response.data;
      
      console.log('✅ Login successful for user:', user.username, 'Role:', user.role);
      
      // Store authentication data with additional metadata for cross-device tracking
      const authData = {
        ...user,
        loginTime: new Date().toISOString(),
        deviceInfo: navigator.userAgent,
        lastActivity: new Date().toISOString()
      };
      
      onLogin(access_token, authData);
      
    } catch (error) {
      console.error('❌ Login failed:', error);
      
      let errorMessage = 'Login failed. Please check your credentials.';
      
      if (error.code === 'ECONNABORTED') {
        errorMessage = 'Connection timeout. Please check your internet connection and try again.';
      } else if (error.code === 'ERR_NETWORK') {
        errorMessage = 'Network error. Please check your internet connection.';
      } else if (error.response?.status === 401) {
        errorMessage = 'Invalid username or password. Please check your credentials.';
      } else if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      }
      
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8 bg-white relative overflow-hidden">
      {/* Background Logo - Large and Faded */}
      <div className="absolute inset-0 flex items-center justify-center opacity-5 pointer-events-none">
        <img 
          src="/greenstar-logo.jpg" 
          alt="Background" 
          className="w-full h-full object-contain max-w-4xl"
        />
      </div>

      <div className="max-w-md w-full space-y-8 relative z-10">
        <div className="bg-white rounded-2xl shadow-2xl border-2 border-gray-100 p-8 md:p-10">
          <div className="text-center mb-8">
            {/* Greenstar Logo - Your Uploaded Logo */}
            <div className="mx-auto mb-6 flex justify-center">
              <img 
                src="/greenstar-logo.jpg" 
                alt="Greenstar Healthcare" 
                className="h-32 w-auto object-contain drop-shadow-lg"
              />
            </div>
            {/* Title in Dark Green */}
            <h2 className="text-3xl md:text-4xl font-bold mb-2" style={{color: '#006838'}}>
              Greenstar Digital Health Solution
            </h2>
            <p className="text-gray-600 font-medium text-sm md:text-base">
              health • prosperity • future
            </p>
          </div>

          {error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="form-group">
              <label htmlFor="username" className="form-label" style={{color: '#006838', fontWeight: '600'}}>
                Username
              </label>
              <div className="relative">
                <UserCheck className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5" style={{color: '#006838'}} />
                <input
                  id="username"
                  name="username"
                  type="text"
                  required
                  className="form-input pl-12 border-2 focus:border-green-600 focus:ring-2 focus:ring-green-200"
                  placeholder="Enter your username"
                  value={formData.username}
                  onChange={handleChange}
                />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="password" className="form-label" style={{color: '#006838', fontWeight: '600'}}>
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  className="form-input pr-12 border-2 focus:border-green-600 focus:ring-2 focus:ring-green-200"
                  placeholder="Enter your password"
                  value={formData.password}
                  onChange={handleChange}
                />
                <button
                  type="button"
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 hover:opacity-70"
                  style={{color: '#006838'}}
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? (
                    <EyeOff className="w-5 h-5" />
                  ) : (
                    <Eye className="w-5 h-5" />
                  )}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full text-white font-semibold py-3 px-4 rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl transform hover:scale-105"
              style={{
                backgroundColor: '#006838',
                ':hover': {backgroundColor: '#005030'}
              }}
              onMouseEnter={(e) => e.target.style.backgroundColor = '#005030'}
              onMouseLeave={(e) => e.target.style.backgroundColor = '#006838'}
            >
              {loading ? (
                <div className="flex items-center justify-center">
                  <div className="loading-spinner mr-2"></div>
                  Signing in...
                </div>
              ) : (
                'Sign In'
              )}
            </button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-sm text-gray-600">
              Only pre-registered healthcare professionals can access this platform
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;