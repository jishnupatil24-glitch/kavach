import type { ReactNode } from 'react';
import * as RTabs from '@radix-ui/react-tabs';
import { cn } from '@/lib/cn';

export function Tabs({
  tabs,
  defaultValue,
  ariaLabel,
}: {
  tabs: { value: string; label: string; content: ReactNode }[];
  defaultValue?: string;
  ariaLabel: string;
}) {
  return (
    <RTabs.Root defaultValue={defaultValue ?? tabs[0]?.value}>
      <RTabs.List
        aria-label={ariaLabel}
        className="mb-6 flex gap-1 border-b border-hairline"
      >
        {tabs.map((t) => (
          <RTabs.Trigger
            key={t.value}
            value={t.value}
            className={cn(
              'min-h-[44px] px-4 font-sans text-sm font-medium text-muted',
              'border-b-2 border-transparent hover:text-ink',
              'data-[state=active]:border-brand-700 data-[state=active]:text-ink',
            )}
          >
            {t.label}
          </RTabs.Trigger>
        ))}
      </RTabs.List>
      {tabs.map((t) => (
        <RTabs.Content key={t.value} value={t.value} className="focus:outline-none">
          {t.content}
        </RTabs.Content>
      ))}
    </RTabs.Root>
  );
}
