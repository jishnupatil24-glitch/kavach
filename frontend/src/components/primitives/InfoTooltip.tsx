import type { ReactNode } from 'react';
import * as Tooltip from '@radix-ui/react-tooltip';
import { Info } from 'lucide-react';
import { cn } from '@/lib/cn';

interface Props {
  /** Plain-language content shown in the tooltip. */
  content: ReactNode;
  /** Optional trigger; defaults to a small info icon button. */
  children?: ReactNode;
  label?: string;
  className?: string;
}

/**
 * Keyboard-accessible tooltip (Radix): focusable trigger, Esc to dismiss,
 * content mirrored in aria via the trigger's accessible name.
 */
export function InfoTooltip({ content, children, label = 'More information', className }: Props) {
  return (
    <Tooltip.Provider delayDuration={150}>
      <Tooltip.Root>
        <Tooltip.Trigger asChild>
          {children ?? (
            <button
              type="button"
              aria-label={label}
              className={cn(
                'inline-flex h-5 w-5 items-center justify-center rounded-full text-muted hover:text-ink',
                className,
              )}
            >
              <Info size={14} aria-hidden />
            </button>
          )}
        </Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content
            sideOffset={6}
            className="z-50 max-w-xs rounded-lg border border-hairline bg-surface px-3 py-2 text-sm text-body shadow-lift"
          >
            {content}
            <Tooltip.Arrow className="fill-surface" />
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    </Tooltip.Provider>
  );
}
