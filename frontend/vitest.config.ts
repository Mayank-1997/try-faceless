import { defineConfig } from 'vitest/config'
import path from 'path'

export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    include: ['**/*.test.{ts,tsx}'],
  },
  resolve: {
    alias: {
      '@ai-video-studio/shared-types': path.resolve(__dirname, 'packages/shared-types/src'),
      '@ai-video-studio/shared-utils': path.resolve(__dirname, 'packages/shared-utils/src'),
      '@ai-video-studio/shared-hooks': path.resolve(__dirname, 'packages/shared-hooks/src'),
      '@ai-video-studio/theme': path.resolve(__dirname, 'packages/theme/src'),
      '@ai-video-studio/icons': path.resolve(__dirname, 'packages/icons/src'),
      '@ai-video-studio/design-system': path.resolve(__dirname, 'packages/design-system/src'),
      '@ai-video-studio/platform-sdk': path.resolve(__dirname, 'packages/platform-sdk/src'),
      '@ai-video-studio/platform-kernel': path.resolve(__dirname, 'packages/platform-kernel/src'),
    },
  },
})
