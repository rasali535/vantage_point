/**
 * API Configuration
 *
 * Production uses the dedicated Render FastAPI service. Local development
 * can override VITE_API_URL or use the local FastAPI server.
 */

const getApiBaseUrl = () => {
  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl) return envUrl.replace(/\/$/, '');

  if (import.meta.env.DEV) return 'http://localhost:8000';

  return 'https://vantage-point-1qv7.onrender.com';
};

export const API_BASE_URL = getApiBaseUrl();

export const apiPath = (path: string) => {
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${cleanPath}`;
};
