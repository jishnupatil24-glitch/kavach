import { createBrowserRouter, Navigate } from 'react-router-dom';
import { GlobalLayout } from '@/components/layout/GlobalLayout';
import { RunLayout } from '@/components/layout/RunLayout';
import { RunSwitcherPage } from '@/features/runs/RunSwitcherPage';
import { OverviewPage } from '@/features/overview/OverviewPage';
import { FarmStatePage } from '@/features/farm-state/FarmStatePage';
import { ProblemsPage } from '@/features/problems/ProblemsPage';
import { RecommendationsPage } from '@/features/recommendations/RecommendationsPage';
import { OptimizationPage } from '@/features/optimization/OptimizationPage';
import { FarmSetupPage } from '@/features/optimization/FarmSetupPage';
import { KnowledgeBasePage } from '@/features/knowledge/KnowledgeBasePage';
import { SensorsPage } from '@/features/knowledge/SensorsPage';
import { AboutPage } from '@/features/knowledge/AboutPage';
import { NotFound } from '@/pages/NotFound';

export const router = createBrowserRouter([
  {
    element: <GlobalLayout />,
    children: [
      { path: '/', element: <RunSwitcherPage /> },
      { path: '/knowledge', element: <KnowledgeBasePage /> },
      { path: '/about', element: <AboutPage /> },
    ],
  },
  {
    path: '/runs/:id',
    element: <RunLayout />,
    children: [
      { index: true, element: <OverviewPage /> },
      { path: 'state', element: <FarmStatePage /> },
      { path: 'problems', element: <ProblemsPage /> },
      { path: 'recommendations', element: <RecommendationsPage /> },
      { path: 'optimization', element: <OptimizationPage /> },
      { path: 'farm-config', element: <FarmSetupPage /> },
      { path: 'sensors', element: <SensorsPage /> },
      { path: '*', element: <Navigate to="." replace /> },
    ],
  },
  { path: '*', element: <NotFound /> },
]);
