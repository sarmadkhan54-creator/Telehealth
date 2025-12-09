// Backend URL configuration that works for all environments
// Automatically detects the correct backend URL based on current domain

const getBackendURL = () => {
  // If explicitly set in environment, use it (for local development)
  if (process.env.REACT_APP_BACKEND_URL) {
    return process.env.REACT_APP_BACKEND_URL;
  }

  // Get current hostname
  const hostname = window.location.hostname;
  
  // For custom domains, use the Emergent production URL
  // Custom domains only serve frontend, backend is on emergent.host
  if (!hostname.includes('emergentagent.com') && !hostname.includes('emergent.host') && !hostname.includes('localhost')) {
    console.log('🔧 Custom domain detected, using Emergent backend');
    return 'https://medconnect-live-1.emergent.host';
  }
  
  // For preview and production emergent domains, use the same origin
  const currentOrigin = window.location.origin;
  
  console.log('🔧 Auto-detected backend URL:', currentOrigin);
  
  return currentOrigin;
};

export const BACKEND_URL = getBackendURL();
export const API_URL = `${BACKEND_URL}/api`;

console.log('🌐 Frontend running on:', window.location.origin);
console.log('🔌 Backend configured at:', BACKEND_URL);
