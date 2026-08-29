import { Monitor, Moon, Sun } from 'lucide-react';
import { useTheme } from '@/context/ThemeContext';
import { cn } from '@/lib/cn';

const ORDER = ['light', 'dark', 'system'] as const;
const ICON = { light: Sun, dark: Moon, system: Monitor };
const NEXT_LABEL = { light: 'dark', dark: 'system', system: 'light' };

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const Icon = ICON[theme];
  return (
    <button
      type="button"
      onClick={() => setTheme(ORDER[(ORDER.indexOf(theme) + 1) % ORDER.length])}
      className={cn(
        'flex h-9 w-9 items-center justify-center rounded-full border border-hairline text-muted hover:text-ink',
      )}
      aria-label={`Theme: ${theme}. Switch to ${NEXT_LABEL[theme]}.`}
      title={`Theme: ${theme}`}
    >
      <Icon size={16} aria-hidden />
    </button>
  );
}
