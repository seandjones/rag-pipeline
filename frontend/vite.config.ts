import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tsconfigPaths from 'vite-tsconfig-paths'

export default defineConfig({
  plugins: [react(), tsconfigPaths()],
  server: {
    host: true, // bind to 0.0.0.0 so Docker can expose the port
    proxy: {
      '/api': {
        // In docker-compose dev: VITE_BACKEND_URL=http://backend:8002
        // Locally without Docker: leave unset, falls back to localhost:8002
        target: process.env.VITE_BACKEND_URL ?? 'http://localhost:8002',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
