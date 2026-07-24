import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules')) {
            if (id.includes('react-router-dom')) return 'router'
            if (id.includes('recharts')) return 'charts'
            if (id.includes('date-fns')) return 'dates'
            return 'vendor'
          }
        },
      },
    },
  },
  server: {
    port: 5173,
    host: true,
  },
})
