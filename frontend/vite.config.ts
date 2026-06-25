import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          three: ['three'],
          r3f: ['@react-three/fiber', '@react-three/drei'],
          postprocessing: ['@react-three/postprocessing', 'postprocessing'],
          react: ['react', 'react-dom'],
          gsap: ['gsap'],
        },
      },
    },
    target: 'esnext',
    minify: 'esbuild',
  },
  server: {
    port: 5173,
    host: '127.0.0.1',
  },
});
