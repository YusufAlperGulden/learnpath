import { useEffect } from 'react';
import { AppLayout } from '../../components/layout/AppLayout';
import { Badge, Card } from '../../components/ui';

export function ResourceManagerPage() {
  useEffect(() => {
    document.title = 'Admin Resource Catalog | LearnPath';
  }, []);

  return (
    <AppLayout
      pageTitle="Admin Resource Catalog Management"
      pageSubtitle="Create, validate, and soft-deactivate Python learning resources with TF-IDF descriptions."
    >
      <Card className="space-y-2">
        <Badge tone="warning">ADMIN ONLY</Badge>
        <p className="text-sm text-slate-600">
          Connected to RBAC-protected <code>/api/v1/admin/resources</code>. Full CRUD table UI
          expands in Increment 2.
        </p>
      </Card>
    </AppLayout>
  );
}
