import { useEffect } from 'react';
import { AppLayout } from '../../components/layout/AppLayout';
import { Badge, Card } from '../../components/ui';

export function RecommendationsPage() {
  useEffect(() => {
    document.title = 'Explainable Recommendations | LearnPath';
  }, []);

  return (
    <AppLayout
      pageTitle="Personalized Resource Recommendations"
      pageSubtitle="Ranked resources with transparent rationale strings across Rule-Based, Popularity, CBF, CF, and Hybrid strategies."
    >
      <Card className="space-y-2">
        <Badge tone="info">Increment 3 &amp; 5 Ready</Badge>
        <h2 className="text-base font-semibold text-slate-900">
          Explainable Recommendation Cards Shell
        </h2>
        <p className="text-sm text-slate-600">
          API contract locked at <code>GET /api/v1/recommendations</code>. Full interactive cards,
          Recharts topic breakdown, bookmarking, and 1–5 star ratings plug in during Increments 3–4.
        </p>
      </Card>
    </AppLayout>
  );
}
