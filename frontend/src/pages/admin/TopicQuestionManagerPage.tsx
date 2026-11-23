import { useEffect } from 'react';
import { AppLayout } from '../../components/layout/AppLayout';
import { Badge, Card } from '../../components/ui';

export function TopicQuestionManagerPage() {
  useEffect(() => {
    document.title = 'Admin DAG & Question Bank | LearnPath';
  }, []);

  return (
    <AppLayout
      pageTitle="Curriculum DAG & Versioned Question Bank"
      pageSubtitle="Manage Python topics, cycle-checked prerequisites, and immutable question versioning."
    >
      <Card className="space-y-2">
        <Badge tone="warning">ADMIN ONLY</Badge>
        <p className="text-sm text-slate-600">
          Connected to RBAC-protected <code>/api/v1/admin/topics</code> and{' '}
          <code>/api/v1/admin/questions</code>.
        </p>
      </Card>
    </AppLayout>
  );
}
