import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    // Disable sourcemaps completely in production builds so code and variables cannot be inspected via DevTools Sources
    sourcemap: false,
  },
})
