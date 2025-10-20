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
    <div className="min-h-screen flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8 relative overflow-hidden" 
         style={{
           background: 'linear-gradient(135deg, #f8fffe 0%, #e8f5f0 50%, #f8fffe 100%)'
         }}>
      
      {/* Background Watermark - Greenstar General Hospital Logo */}
      <div className="absolute inset-0 flex items-center justify-center opacity-8 pointer-events-none">
        <img 
          src="/hospital-logo.jpg" 
          alt="Background" 
          className="w-full h-full object-contain max-w-5xl"
          style={{filter: 'blur(0.5px)'}}
        />
      </div>

      {/* Decorative Elements */}
      <div className="absolute top-0 left-0 w-64 h-64 bg-green-100 rounded-full filter blur-3xl opacity-20 -translate-x-1/2 -translate-y-1/2"></div>
      <div className="absolute bottom-0 right-0 w-64 h-64 bg-green-100 rounded-full filter blur-3xl opacity-20 translate-x-1/2 translate-y-1/2"></div>

      <div className="max-w-md w-full space-y-8 relative z-10">
        <div className="bg-white/95 backdrop-blur-sm rounded-3xl shadow-2xl border border-green-100 p-8 md:p-12 hover:shadow-green-200/50 transition-all duration-300">
          <div className="text-center mb-8">
            {/* Main GSM Logo */}
            <div className="mx-auto mb-6 flex justify-center transform hover:scale-105 transition-transform duration-300">
              <img 
                src="/gsm-logo.jpg" 
                alt="Greenstar Social Marketing" 
                className="h-44 w-auto object-contain drop-shadow-2xl filter brightness-105"
              />
            </div>
            
            {/* Elegant Divider */}
            <div className="flex items-center justify-center my-6">
              <div className="h-px bg-gradient-to-r from-transparent via-green-300 to-transparent w-full max-w-xs"></div>
            </div>
            
            {/* Title in Dark Green with Shadow */}
            <h2 className="text-3xl md:text-4xl font-bold mb-4 tracking-tight" 
                style={{
                  color: '#006838',
                  textShadow: '0 2px 4px rgba(0,104,56,0.1)'
                }}>
              Greenstar Digital Health Solution
            </h2>
            
            {/* Subtitle */}
            <p className="text-gray-600 font-medium text-sm md:text-base tracking-wide">
              Connecting Care, Empowering Health
            </p>
          </div>

          {error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="form-group">
              <label htmlFor="username" className="form-label font-semibold text-sm mb-2 block" 
                     style={{color: '#006838'}}>
                Username
              </label>
              <div className="relative group">
                <UserCheck className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 transition-colors duration-200" 
                          style={{color: '#006838'}} />
                <input
                  id="username"
                  name="username"
                  type="text"
                  required
                  className="w-full pl-12 pr-4 py-3 border-2 border-gray-200 rounded-xl focus:border-green-500 focus:ring-4 focus:ring-green-100 outline-none transition-all duration-300 bg-gray-50 hover:bg-white group-hover:border-green-300"
                  placeholder="Enter your username"
                  value={formData.username}
                  onChange={handleChange}
                />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="password" className="form-label font-semibold text-sm mb-2 block" 
                     style={{color: '#006838'}}>
                Password
              </label>
              <div className="relative group">
                <input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  className="w-full px-4 py-3 pr-12 border-2 border-gray-200 rounded-xl focus:border-green-500 focus:ring-4 focus:ring-green-100 outline-none transition-all duration-300 bg-gray-50 hover:bg-white group-hover:border-green-300"
                  placeholder="Enter your password"
                  value={formData.password}
                  onChange={handleChange}
                />
                <button
                  type="button"
                  className="absolute right-4 top-1/2 transform -translate-y-1/2 hover:opacity-70 transition-opacity duration-200"
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