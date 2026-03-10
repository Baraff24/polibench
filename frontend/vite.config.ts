/// <reference types="vitest" />

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // React core — cambia raramente, va in cache a lungo
          'vendor-react': ['react', 'react-dom'],
          // Router
          'vendor-router': ['react-router'],
          // Recharts è la libreria più pesante (~400 KB)
          'vendor-recharts': ['recharts'],
          // Form handling
          'vendor-forms': ['react-hook-form'],
          // HTTP client
          'vendor-axios': ['axios'],
        },
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['src/setupTest.ts'],
    coverage: {
      reporter: ['text', 'json', 'html', 'cobertura'],
    },
  },
})
