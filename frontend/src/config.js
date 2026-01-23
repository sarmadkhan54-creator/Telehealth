// Backend URL configuration that works for all environments
// Automatically detects the correct backend URL based on current domain

const getBackendURL = () => {
  // Get current hostname
  const hostname = window.location.hostname;
  
  // PRIORITY 1: Custom domains (like telehealthapp.online) MUST use production backend
  // Custom domains only serve frontend, backend is always on emergent.host
  if (!hostname.includes('emergentagent.com') && 
      !hostname.includes('emergent.host') && 
      !hostname.includes('localhost') &&
      !hostname.includes('127.0.0.1') &&
      !hostname.includes('preview.')) {
    console.log('🔧 Custom domain detected:', hostname);
    console.log('🔧 Using production Emergent backend');
    return 'https://medconnect-live-1.emergent.host';
  }
  
  // PRIORITY 2: For preview/dev environments, use env variable or same origin
  if (process.env.REACT_APP_BACKEND_URL) {
    console.log('🔧 Using environment variable REACT_APP_BACKEND_URL');
    return process.env.REACT_APP_BACKEND_URL;
  }
  
  // PRIORITY 3: Fallback to same origin for emergent domains
  const currentOrigin = window.location.origin;
  console.log('🔧 Auto-detected backend URL:', currentOrigin);
  
  return currentOrigin;
};

export const BACKEND_URL = getBackendURL();
export const API_URL = `${BACKEND_URL}/api`;

console.log('🌐 Frontend running on:', window.location.origin);
console.log('🔌 Backend configured at:', BACKEND_URL);
