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
    <div className="min-h-screen flex">
      {/* LEFT SIDE - Green Gradient with Greenstar General Hospital Logo */}
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden"
           style={{
             background: 'linear-gradient(135deg, #004d2c 0%, #006838 50%, #008844 100%)'
           }}>
        {/* Decorative circles */}
        <div className="absolute top-20 left-20 w-96 h-96 bg-white/5 rounded-full filter blur-3xl"></div>
        <div className="absolute bottom-20 right-20 w-80 h-80 bg-white/5 rounded-full filter blur-3xl"></div>
        
        {/* Content */}
        <div className="relative z-10 flex flex-col items-center justify-center w-full p-12">
          {/* Greenstar General Hospital Logo */}
          <div className="mb-8 bg-white rounded-2xl p-4">
            <img 
              src="/hospital-logo.jpg" 
              alt="Greenstar General Hospital" 
              className="h-32 w-auto object-contain"
              style={{
                mixBlendMode: 'multiply'
              }}
            />
          </div>
          
          {/* Welcome Text */}
          <div className="text-center text-white space-y-6 max-w-md">
            <h1 className="text-4xl lg:text-5xl font-bold leading-tight">
              Welcome to Digital Healthcare
            </h1>
            <p className="text-lg text-white/90 leading-relaxed">
              Empowering healthcare professionals with seamless telehealth solutions
            </p>
            <div className="pt-8 flex items-center justify-center gap-3">
              <div className="h-1 w-12 bg-white/80 rounded-full"></div>
              <div className="h-1 w-8 bg-white/60 rounded-full"></div>
              <div className="h-1 w-4 bg-white/40 rounded-full"></div>
            </div>
          </div>
        </div>
      </div>

      {/* RIGHT SIDE - White Background with Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center bg-white py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md w-full space-y-8">
          <div className="text-center">
            {/* Main GSM Logo */}
            <div className="mx-auto mb-6 flex justify-center transform hover:scale-105 transition-transform duration-300">
              <img 
                src="/gsm-logo.jpg" 
                alt="Greenstar Social Marketing" 
                className="h-40 w-auto object-contain drop-shadow-xl"
              />
            </div>
            
            {/* Elegant Divider */}
            <div className="flex items-center justify-center my-6">
              <div className="h-px bg-gradient-to-r from-transparent via-green-300 to-transparent w-full max-w-xs"></div>
            </div>
            
            {/* Title in Dark Green with Shadow - Single Line */}
            <h2 className="text-2xl md:text-3xl font-bold mb-3 tracking-tight whitespace-nowrap" 
                style={{
                  color: '#006838',
                  textShadow: '0 2px 4px rgba(0,104,56,0.1)'
                }}>
              Greenstar Digital Health Solutions
            </h2>
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
              className="w-full text-white font-bold py-4 px-6 rounded-xl transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-2xl transform hover:scale-[1.02] active:scale-[0.98] relative overflow-hidden group"
              style={{
                background: 'linear-gradient(135deg, #006838 0%, #005030 100%)',
              }}
            >
              <span className="relative z-10">
                {loading ? (
                  <div className="flex items-center justify-center">
                    <div className="loading-spinner mr-2"></div>
                    Signing in...
                  </div>
                ) : (
                  <span className="flex items-center justify-center gap-2">
                    Sign In
                    <svg className="w-5 h-5 transform group-hover:translate-x-1 transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                    </svg>
                  </span>
                )}
              </span>
              {/* Shine effect on hover */}
              <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white to-transparent opacity-0 group-hover:opacity-10 transform -translate-x-full group-hover:translate-x-full transition-all duration-1000"></span>
            </button>
          </form>

          <div className="mt-8 text-center">
            <div className="flex items-center justify-center mb-4">
              <div className="h-px bg-gradient-to-r from-transparent via-gray-300 to-transparent w-full"></div>
            </div>
            <p className="text-sm text-gray-600 px-4">
              🔒 Only pre-registered healthcare professionals can access this platform
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;