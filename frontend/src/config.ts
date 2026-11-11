/**
 * API Configuration
 *
 * Production API requests use the same-origin Vercel backend service.
 * Local development can use VITE_API_URL or the local FastAPI server.
 */

const getApiBaseUrl = () => {
  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl) return envUrl;

  if (import.meta.env.DEV) return 'http://localhost:8000';

  // Same-origin routing: Vercel sends /api/* to the FastAPI service.
  return '';
};

export const API_BASE_URL = getApiBaseUrl();

export const apiPath = (path: string) => {
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${cleanPath}`;
};
