/**
 * API Configuration
 * 
 * In development, we use the local FastAPI server (http://localhost:8000).
 * In production (Vercel), we use the relative path /api which is proxied 
 * to the Python serverless function via vercel.json rewrites.
 */

const getApiBaseUrl = () => {
  // Check if we are in development mode
  const isDev = import.meta.env.DEV;
  
  // Use VITE_API_URL if provided in .env, otherwise fallback to defaults
  const envUrl = import.meta.env.VITE_API_URL;
  
  if (envUrl) return envUrl;
  
  // Default fallback
  return isDev ? 'http://localhost:8000' : '';
};

export const API_BASE_URL = getApiBaseUrl();

// Helper to construct API endpoints
export const apiPath = (path: string) => {
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  
  // If we're using a relative path (production), we need to ensure it's /api/...
  // but the backend routes already include /api in many cases.
  // Let's check the backend routes in main.py.
  // app.include_router(..., prefix="/api/meetings")
  // So a call to '/api/meetings/upload' is already correct.
  
  return `${API_BASE_URL}${cleanPath}`;
};
