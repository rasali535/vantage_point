import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// Production DevTools Console Cloaking & Security Hardening
// Ensure no credentials, API responses, or internal state are logged or accessible via DevTools Console
if (import.meta.env.PROD) {
  const noop = () => {};
  console.log = noop;
  console.info = noop;
  console.warn = noop;
  console.error = noop;
  console.debug = noop;
  console.trace = noop;
  console.dir = noop;
  console.table = noop;
  window.addEventListener('error', (e) => {
    e.preventDefault();
  });
  window.addEventListener('unhandledrejection', (e) => {
    e.preventDefault();
  });
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
