import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  base: process.env.GITHUB_ACTIONS === 'true' ? '/Crypto_Audit/' : '/',
  plugins: [react()],
  server: {
    // The CryptoAudit API (cryptoaudit serve) runs on :8000; proxying keeps the site same-origin so the
    // session cookie and the GitHub sign-in callback (http://localhost:5173/api/auth/github/callback) work.
    proxy: {
      '/api': {
        target: process.env.CRYPTOAUDIT_API_URL || 'http://localhost:8000',
        changeOrigin: false,
      },
    },
  },
})
