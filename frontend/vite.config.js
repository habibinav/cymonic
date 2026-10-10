import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Forward /api calls to the backend during dev (change port if needed)
    proxy: { '/api': 'http://localhost:8000' },
  },
})
