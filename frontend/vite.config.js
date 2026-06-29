import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: '/static/',
  build: {
    outDir: '../app/static',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/v1': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
});
