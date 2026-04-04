import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    // 固定 IPv4，避免 Windows 上 localhost 走 IPv6 导致 ERR_CONNECTION_REFUSED
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        timeout: 300000,
        proxyTimeout: 300000,
      },
    },
  },
})
