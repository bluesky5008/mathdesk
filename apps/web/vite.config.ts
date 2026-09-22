import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    proxy: { '/api': process.env.VITE_API_ORIGIN ?? 'http://localhost:8000' },
  },
})
