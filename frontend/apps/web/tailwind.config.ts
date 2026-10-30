import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
    '../../packages/design-system/src/**/*.{js,ts,jsx,tsx}',
    '../../packages/platform-kernel/src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        border: 'var(--border-default)',
        background: 'var(--bg-base)',
        foreground: 'var(--fg-default)',
        brand: {
          DEFAULT: 'var(--brand-default)',
          hover: 'var(--brand-hover)',
          active: 'var(--brand-active)',
        },
      },
    },
  },
  plugins: [],
}

export default config
