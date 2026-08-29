import { Outlet } from 'react-router-dom';
import { AppShell } from './AppShell';

/** Layout for non-run routes (run switcher, knowledge base, about). */
export function GlobalLayout() {
  return (
    <AppShell>
      <Outlet />
    </AppShell>
  );
}
