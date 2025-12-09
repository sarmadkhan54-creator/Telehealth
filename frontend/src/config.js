// Backend URL configuration that works for all environments
// Automatically detects the correct backend URL based on current domain

const getBackendURL = () => {
  // If explicitly set in environment, use it (for local development)
  if (process.env.REACT_APP_BACKEND_URL) {
    return process.env.REACT_APP_BACKEND_URL;
  }

  // For production deployments, use the same origin (custom domain or emergent domain)
  // This makes it work automatically with any domain pointing to the app
  const currentOrigin = window.location.origin;
  
  console.log('🔧 Auto-detected backend URL:', currentOrigin);
  
  return currentOrigin;
};

export const BACKEND_URL = getBackendURL();
export const API_URL = `${BACKEND_URL}/api`;
