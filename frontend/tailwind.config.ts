import type { Config } from 'tailwindcss';

/**
 * Colours are declared once as "R G B" custom properties in
 * src/styles/tokens.css (light = Greenhouse Daylight, dark = Field Console) and
 * only referenced here via rgb(var(--token) / <alpha-value>), which lets every
 * opacity modifier (bg-brand-700/30 …) work. Brand green is structure/action
 * only — never a status encoding.
 */
const rgb = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: ['selector', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        bg: rgb('bg'),
        surface: rgb('surface'),
        'surface-sunken': rgb('surface-sunken'),
        'surface-raised': rgb('surface-raised'),
        hairline: rgb('border-hairline'),
        ink: rgb('ink'),
        body: rgb('body'),
        muted: rgb('muted'),
        brand: {
          DEFAULT: rgb('brand-700'),
          900: rgb('brand-900'),
          700: rgb('brand-700'),
          tint: rgb('brand-tint'),
        },
        gold: {
          DEFAULT: rgb('accent-gold'),
          soft: rgb('accent-gold-soft'),
        },
        'sev-low': rgb('sev-low'),
        'sev-moderate': rgb('sev-moderate'),
        'sev-high': rgb('sev-high'),
        'sev-critical': rgb('sev-critical'),
        'feas-pass': rgb('feas-pass'),
        'feas-fail': rgb('feas-fail'),
        modeled: rgb('modeled-blue'),
      },
      fontFamily: {
        display: ['Fraunces', 'Georgia', 'serif'],
        sans: ['Lexend', 'system-ui', 'sans-serif'],
        body: ['"Source Sans 3"', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        xs: ['0.75rem', { lineHeight: '1.4' }],
        sm: ['0.875rem', { lineHeight: '1.45' }],
        base: ['1rem', { lineHeight: '1.5' }],
        lg: ['1.25rem', { lineHeight: '1.4' }],
        xl: ['1.5625rem', { lineHeight: '1.3' }],
        '2xl': ['1.9375rem', { lineHeight: '1.2' }],
        '3xl': ['2.4375rem', { lineHeight: '1.1' }],
        '4xl': ['3.0625rem', { lineHeight: '1.05' }],
      },
      spacing: {
        1: '4px',
        2: '8px',
        3: '12px',
        4: '16px',
        6: '24px',
        8: '32px',
        12: '48px',
        16: '64px',
        24: '96px',
      },
      borderRadius: {
        sm: '6px',
        DEFAULT: '10px',
        lg: '14px',
        pill: '999px',
      },
      boxShadow: {
        card: 'var(--shadow-card)',
        lift: 'var(--shadow-lift)',
      },
      maxWidth: {
        content: '1280px',
      },
      keyframes: {
        'pulse-once': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.55' },
        },
      },
      animation: {
        'pulse-once': 'pulse-once 2.4s ease-in-out 1',
      },
    },
  },
  plugins: [],
};

export default config;
