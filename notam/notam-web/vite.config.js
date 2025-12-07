import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api/proxy': {
        target: 'https://b5hg4r5aoqoit35vhxzo2v75wi0vryxq.lambda-url.ap-southeast-2.on.aws',
        changeOrigin: true,
        rewrite: (path) => {
          const url = new URL(path, 'http://localhost')
          return url.searchParams.get('path') || '/health'
        }
      }
    }
  }
})
