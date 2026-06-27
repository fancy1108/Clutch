import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import { defineConfig } from 'vitest/config';

export default defineConfig(({ command }) => {
  const isDevServer = command === 'serve';
  return {
    // Dev (tauri dev + vite) must use absolute paths; production DMG needs relative assets.
    base: isDevServer ? '/' : './',
    plugins: [react(), tailwindcss()],
    test: {
      environment: 'node',
      include: ['src/**/*.test.ts'],
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src'),
      },
    },
    server: {
      port: 3000,
      strictPort: true,
      host: '0.0.0.0',
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8124',
          changeOrigin: true,
        },
        '/ws': {
          target: 'ws://127.0.0.1:8124',
          ws: true,
        },
      },
      hmr: process.env.DISABLE_HMR !== 'true',
      watch:
        process.env.DISABLE_HMR === 'true'
          ? null
          : {
              ignored: ['**/src-tauri/**'],
            },
    },
  };
});
