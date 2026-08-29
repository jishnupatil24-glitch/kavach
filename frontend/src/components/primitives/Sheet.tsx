import type { ReactNode } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
import { cn } from '@/lib/cn';

/**
 * Right slide-over on desktop, full-height bottom sheet on small screens.
 * Radix Dialog gives focus trap, Esc, scroll lock and aria wiring for free.
 */
export function Sheet({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
  size = 'md',
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  title: ReactNode;
  description?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  size?: 'md' | 'lg';
}) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/30 data-[state=open]:animate-[fade_150ms_ease]" />
        <Dialog.Content
          className={cn(
            'fixed z-50 flex flex-col bg-surface shadow-lift focus:outline-none',
            'inset-x-0 bottom-0 max-h-[92vh] rounded-t-lg',
            'sm:inset-y-0 sm:right-0 sm:bottom-auto sm:max-h-none sm:rounded-t-none sm:border-l sm:border-hairline',
            size === 'lg' ? 'sm:w-[560px]' : 'sm:w-[460px]',
          )}
        >
          <div className="flex items-start justify-between gap-4 border-b border-hairline px-6 py-4">
            <div>
              <Dialog.Title className="font-sans text-lg text-ink">{title}</Dialog.Title>
              {description ? (
                <Dialog.Description className="mt-1 text-sm text-muted">
                  {description}
                </Dialog.Description>
              ) : (
                <Dialog.Description className="sr-only">{title}</Dialog.Description>
              )}
            </div>
            <Dialog.Close
              className="rounded p-1 text-muted hover:bg-surface-sunken hover:text-ink"
              aria-label="Close"
            >
              <X size={18} aria-hidden />
            </Dialog.Close>
          </div>
          <div className="flex-1 overflow-y-auto px-6 py-5">{children}</div>
          {footer ? <div className="border-t border-hairline px-6 py-4">{footer}</div> : null}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
