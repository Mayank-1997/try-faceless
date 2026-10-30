/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: [
    '@ai-video-studio/shared-types',
    '@ai-video-studio/shared-utils',
    '@ai-video-studio/shared-hooks',
    '@ai-video-studio/theme',
    '@ai-video-studio/icons',
    '@ai-video-studio/design-system',
    '@ai-video-studio/platform-sdk',
    '@ai-video-studio/platform-kernel',
  ],
  experimental: {
    optimizePackageImports: ['@ai-video-studio/icons'],
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
}

module.exports = nextConfig
