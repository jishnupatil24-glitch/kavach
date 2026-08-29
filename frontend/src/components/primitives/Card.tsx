import type { HTMLAttributes, ReactNode } from 'react';
import { cn } from '@/lib/cn';

export function Card({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('card p-6', className)} {...rest} />;
}

interface SectionCardProps extends Omit<HTMLAttributes<HTMLElement>, 'title'> {
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
}

export function SectionCard({
  title,
  subtitle,
  actions,
  children,
  className,
  ...rest
}: SectionCardProps) {
  return (
    <section className={cn('card p-6', className)} {...rest}>
      <header className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-sans">{title}</h2>
          {subtitle ? <p className="mt-1 text-sm text-muted">{subtitle}</p> : null}
        </div>
        {actions ? <div className="shrink-0">{actions}</div> : null}
      </header>
      {children}
    </section>
  );
}
