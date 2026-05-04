import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
  build: {
    chunkSizeWarningLimit: 2600,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react':  ['react', 'react-dom', 'react-router-dom'],
          'vendor-mapbox': ['mapbox-gl', 'react-map-gl'],
          'vendor-charts': ['recharts'],
          'vendor-auth':   ['@azure/msal-browser', '@azure/msal-react', '@react-oauth/google'],
          'vendor-utils':  ['axios', 'date-fns', 'lucide-react'],
        },
      },
    },
  },
});
