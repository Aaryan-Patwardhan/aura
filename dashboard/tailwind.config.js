/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        aura: {
          bg:        '#0c0f1a',
          surface:   '#131929',
          border:    '#1e2d45',
          accent:    '#3b82f6',
          accentGlow:'#60a5fa',
          green:     '#22c55e',
          yellow:    '#eab308',
          red:       '#ef4444',
          muted:     '#64748b',
          text:      '#e2e8f0',
          textDim:   '#94a3b8',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in':    'fadeIn 0.3s ease-out',
        'slide-up':   'slideUp 0.4s ease-out',
      },
      keyframes: {
        fadeIn:  { '0%': { opacity: 0 }, '100%': { opacity: 1 } },
        slideUp: { '0%': { transform: 'translateY(12px)', opacity: 0 }, '100%': { transform: 'translateY(0)', opacity: 1 } },
      },
      backdropBlur: { xs: '2px' },
    },
  },
  plugins: [],
}
