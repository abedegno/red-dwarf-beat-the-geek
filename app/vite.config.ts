import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import integration from './test/integration-files.json' with { type: 'json' };
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  publicDir: process.env.BTG_BUNDLE_ONLY === '1' ? false : 'public',
  test: {
    environment: 'node',
    include: mode === 'integration' ? integration : ['src/**/*.test.ts'],
    exclude: mode === 'all' || mode === 'integration' ? [] : integration,
  },
}));
