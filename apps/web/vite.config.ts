import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    globals: true,
  },
  server: {
    host: true,
    proxy: { '/api': process.env.VITE_API_ORIGIN ?? 'http://localhost:8000' },
  },
})
