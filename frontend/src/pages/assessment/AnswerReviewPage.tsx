import { useEffect } from 'react';
import { AppLayout } from '../../components/layout/AppLayout';
import { Card } from '../../components/ui';

export function AnswerReviewPage() {
  useEffect(() => {
    document.title = 'Detailed Answer Review | LearnPath';
  }, []);

  return (
    <AppLayout
      pageTitle="Detailed Answer & Solution Review"
      pageSubtitle="Review correct, incorrect, and skipped questions with post-submission explanations."
    >
      <Card>
        <p className="text-sm text-slate-600">
          Post-submission solution review view wired for Increment 3.
        </p>
      </Card>
    </AppLayout>
  );
}
