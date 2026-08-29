import type { LucideIcon } from 'lucide-react';
import {
  Activity,
  BookOpen,
  ClipboardList,
  Info,
  LayoutGrid,
  ListChecks,
  Radio,
  Sprout,
} from 'lucide-react';

export interface FunnelNode {
  key: string;
  marker: string;
  label: string;
  icon: LucideIcon;
  to: (runId: number) => string;
  /** which route path segment marks this node active */
  match: string;
}

/** The decision funnel — the primary navigation and the product's spine. */
export const FUNNEL: FunnelNode[] = [
  {
    key: 'overview',
    marker: '◆',
    label: 'Overview',
    icon: LayoutGrid,
    to: (id) => `/runs/${id}`,
    match: 'overview',
  },
  {
    key: 'state',
    marker: '1',
    label: 'Farm State',
    icon: Activity,
    to: (id) => `/runs/${id}/state`,
    match: 'state',
  },
  {
    key: 'problems',
    marker: '2',
    label: 'Problems',
    icon: ClipboardList,
    to: (id) => `/runs/${id}/problems`,
    match: 'problems',
  },
  {
    key: 'recommendations',
    marker: '3',
    label: 'Recommendations',
    icon: ListChecks,
    to: (id) => `/runs/${id}/recommendations`,
    match: 'recommendations',
  },
  {
    key: 'optimization',
    marker: '4',
    label: 'Optimized Plan',
    icon: Sprout,
    to: (id) => `/runs/${id}/optimization`,
    match: 'optimization',
  },
];

export interface ReferenceLink {
  key: string;
  label: string;
  icon: LucideIcon;
  to: (runId: number | null) => string;
  runScoped: boolean;
}

export const REFERENCE_LINKS: ReferenceLink[] = [
  {
    key: 'knowledge',
    label: 'Knowledge Base',
    icon: BookOpen,
    to: () => '/knowledge',
    runScoped: false,
  },
  {
    key: 'sensors',
    label: 'Raw Sensor Readings',
    icon: Radio,
    to: (id) => (id != null ? `/runs/${id}/sensors` : '/knowledge'),
    runScoped: true,
  },
  {
    key: 'about',
    label: 'About / Legend',
    icon: Info,
    to: () => '/about',
    runScoped: false,
  },
];
