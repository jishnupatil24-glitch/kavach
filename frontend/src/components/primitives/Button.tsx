import { forwardRef } from 'react';
import type { ButtonHTMLAttributes } from 'react';
import { cn } from '@/lib/cn';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';
type Size = 'sm' | 'md';

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

const base =
  'inline-flex items-center justify-center gap-2 rounded font-sans font-medium transition-colors ' +
  'disabled:opacity-50 disabled:pointer-events-none focus-visible:outline-2';

const variants: Record<Variant, string> = {
  primary: 'bg-brand-700 text-white hover:brightness-110',
  secondary: 'border border-hairline bg-surface text-ink hover:bg-surface-sunken',
  ghost: 'text-brand-700 hover:bg-brand-tint',
  danger: 'border border-feas-fail text-feas-fail hover:bg-feas-fail/10',
};

const sizes: Record<Size, string> = {
  sm: 'min-h-[36px] px-3 text-sm',
  md: 'min-h-[44px] px-4 text-base',
};

export const Button = forwardRef<HTMLButtonElement, Props>(function Button(
  { variant = 'secondary', size = 'md', className, type = 'button', ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={cn(base, variants[variant], sizes[size], className)}
      {...rest}
    />
  );
});
