import { useEffect } from 'react';
import { AppLayout } from '../../components/layout/AppLayout';
import { Badge, Card } from '../../components/ui';

export function PlacementTestPage() {
  useEffect(() => {
    document.title = 'Diagnostic & Topic Assessments | LearnPath';
  }, []);

  return (
    <AppLayout
      pageTitle="Placement & Topic Assessments"
      pageSubtitle="Stateless signed session tokens, PrismJS syntax highlighting, skipped-question confirmation, and atomic submission."
    >
      <Card className="space-y-2">
        <Badge tone="info">Increment 3 Ready</Badge>
        <h2 className="text-base font-semibold text-slate-900">Atomic Assessment Engine Shell</h2>
        <p className="text-sm text-slate-600">
          Contracts locked for <code>GET /api/v1/assessments/questions</code> and{' '}
          <code>POST /api/v1/assessments/submit</code> without answer-key leakage.
        </p>
      </Card>
    </AppLayout>
  );
}
