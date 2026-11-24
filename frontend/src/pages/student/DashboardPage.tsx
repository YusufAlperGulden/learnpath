import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowRight, Bookmark, CheckCircle2, ExternalLink, GraduationCap, Sparkles } from 'lucide-react';
import { apiClient } from '../../api/client';
import { studentApi } from '../../api/student';
import { AppLayout } from '../../components/layout/AppLayout';
import { Badge, Card, ProgressBar, ResponsiveTable } from '../../components/ui';
import type { StudentProfile } from '../../types/api';

export function DashboardPage() {
  const queryClient = useQueryClient();

  useEffect(() => {
    document.title = 'Student Dashboard | LearnPath';
  }, []);

  const { data: profile } = useQuery({
    queryKey: ['profile'],
    queryFn: async () => (await apiClient.get<StudentProfile>('/profile')).data,
    retry: false,
  });

  const { data: pathData } = useQuery({
    queryKey: ['learning-path'],
    queryFn: studentApi.getLearningPath,
  });

  const { data: attempts = [] } = useQuery({
    queryKey: ['attempts'],
    queryFn: studentApi.listAttempts,
  });

  const { data: bookmarks = [] } = useQuery({
    queryKey: ['bookmarks'],
    queryFn: studentApi.listBookmarks,
  });

  const { data: history = [] } = useQuery({
    queryKey: ['resource-history'],
    queryFn: studentApi.listResourceHistory,
  });

  const { data: recPreview } = useQuery({
    queryKey: ['recommendations', 'dashboard-preview'],
    queryFn: () => studentApi.getRecommendations({ strategy: 'hybrid', limit: 3 }),
  });

  const openResourceMutation = useMutation({
    mutationFn: (resourceId: string) => studentApi.recordResourceOpen(resourceId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['resource-history'] }),
        queryClient.invalidateQueries({ queryKey: ['recommendations'] }),
      ]);
    },
  });

  const nodes = pathData?.nodes ?? [];
  const masteredCount = nodes.filter((n) => n.mastery_status === 'MASTERED').length;
  const manualCompletedCount = nodes.filter((n) => n.is_manually_completed).length;
  const nextTopic = nodes.find((n) => n.topic_id === pathData?.recommended_next_topic_id);
  const completedResourcesCount = history.filter((h) => h.status === 'COMPLETED').length;

  return (
    <AppLayout
      pageTitle={profile ? `Welcome back, ${profile.display_name}` : 'Student Overview'}
      pageSubtitle="Monitor dual curriculum progress, saved resources, assessment history, and explainable study picks."
    >
      <div className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-4">
          <Card className="p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Exam Mastered
            </p>
            <p className="mt-1 text-2xl font-bold text-emerald-700">
              {masteredCount} / {nodes.length}
            </p>
          </Card>
          <Card className="p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Self-Studied Topics
            </p>
            <p className="mt-1 text-2xl font-bold text-blue-700">
              {manualCompletedCount} / {nodes.length}
            </p>
          </Card>
          <Card className="p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Completed Resources
            </p>
            <p className="mt-1 flex items-center gap-1.5 text-2xl font-bold text-slate-900">
              <CheckCircle2 aria-hidden="true" className="h-5 w-5 text-emerald-600" />
              {completedResourcesCount}
            </p>
          </Card>
          <Card className="p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Saved Bookmarks
            </p>
            <div className="mt-1 flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-2xl font-bold text-slate-900">
                <Bookmark aria-hidden="true" className="h-5 w-5 text-blue-600" />
                {bookmarks.length}
              </span>
              <Link to="/bookmarks" className="text-xs font-semibold text-blue-600 hover:underline">
                Open library
              </Link>
            </div>
          </Card>
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          <Card className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-slate-900">Dual Curriculum Progress</h2>
              <Badge tone="info">6-Topic DAG</Badge>
            </div>
            <ProgressBar
              label="Exam-Verified Mastery (>= 70% Gate)"
              value={masteredCount}
              max={Math.max(nodes.length, 1)}
            />
            <ProgressBar
              label="Self-Reported Study Checklist"
              value={manualCompletedCount}
              max={Math.max(nodes.length, 1)}
            />
            <div className="flex flex-wrap gap-3 pt-1">
              <Link
                to="/assessment"
                className="inline-flex min-h-10 items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
              >
                <GraduationCap aria-hidden="true" className="h-4 w-4" />
                {attempts.length === 0 ? 'Take Placement Exam' : 'Retake Diagnostic'}
              </Link>
              <Link
                to="/roadmap"
                className="inline-flex min-h-10 items-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50"
              >
                Open Prerequisite Roadmap
              </Link>
            </div>
          </Card>

          <Card className="flex flex-col justify-between space-y-4">
            <div>
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-base font-semibold text-slate-900">Next Recommended Focus</h2>
                {nextTopic ? (
                  <Badge tone={nextTopic.mastery_status === 'NEEDS_PRACTICE' ? 'warning' : 'info'}>
                    {nextTopic.mastery_status}
                  </Badge>
                ) : null}
              </div>
              {nextTopic ? (
                <div className="mt-2">
                  <p className="text-lg font-bold text-slate-900">
                    {nextTopic.display_order}. {nextTopic.name}
                  </p>
                  <p className="mt-1 text-xs text-slate-600">{nextTopic.description}</p>
                  {nextTopic.latest_score_percent !== null ? (
                    <p className="mt-2 text-xs font-semibold text-amber-800">
                      Latest exam score: {nextTopic.latest_score_percent.toFixed(0)}% (Target: 70%+)
                    </p>
                  ) : null}
                </div>
              ) : (
                <p className="mt-2 text-sm text-slate-600">
                  All seeded topics reached MASTERED, or curriculum topics have not been seeded yet.
                </p>
              )}
            </div>

            {nextTopic ? (
              <div className="flex flex-wrap gap-2.5 pt-1">
                <Link
                  to={`/recommendations?topicId=${nextTopic.topic_id}`}
                  className="inline-flex min-h-9 items-center gap-1.5 rounded-lg bg-slate-900 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-slate-800"
                >
                  Study Topic Resources
                  <ArrowRight aria-hidden="true" className="h-3.5 w-3.5" />
                </Link>
                <Link
                  to={`/assessment?type=TOPIC_QUIZ&topicId=${nextTopic.topic_id}`}
                  className="inline-flex min-h-9 items-center rounded-lg border border-slate-300 bg-white px-3.5 py-1.5 text-xs font-semibold text-slate-800 hover:bg-slate-50"
                >
                  Take Topic Mastery Quiz
                </Link>
              </div>
            ) : null}
          </Card>
        </div>

        {recPreview && recPreview.items.length > 0 ? (
          <Card className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-slate-900">
                Top Personalized Study Picks
              </h2>
              <Link
                to="/recommendations"
                className="text-xs font-semibold text-blue-600 hover:underline"
              >
                View all recommendations
              </Link>
            </div>
            <div className="grid gap-4 md:grid-cols-3">
              {recPreview.items.map((item) => (
                <div
                  key={item.resource_id}
                  className="flex flex-col justify-between rounded-xl border border-slate-200 bg-slate-50/70 p-4"
                >
                  <div>
                    <div className="flex flex-wrap items-center gap-1.5">
                      <Badge tone="info">{item.topic_name}</Badge>
                      <Badge tone="neutral">{item.content_type}</Badge>
                      {item.progress_status === 'OPENED' ? (
                        <Badge tone="info">OPENED</Badge>
                      ) : null}
                    </div>
                    <h3 className="mt-2 text-sm font-bold text-slate-900">{item.title}</h3>
                    <p className="mt-2 flex items-start gap-1.5 text-xs text-slate-600">
                      <Sparkles
                        aria-hidden="true"
                        className="mt-0.5 h-3.5 w-3.5 shrink-0 text-blue-600"
                      />
                      <span>{item.rationale}</span>
                    </p>
                  </div>
                  <a
                    href={item.external_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={`Open recommended resource ${item.title}`}
                    onClick={() => openResourceMutation.mutate(item.resource_id)}
                    className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:underline"
                  >
                    Open resource
                    <ExternalLink aria-hidden="true" className="h-3 w-3" />
                  </a>
                </div>
              ))}
            </div>
          </Card>
        ) : null}

        {attempts.length > 0 ? (
          <ResponsiveTable
            caption="Recent assessment attempts"
            hideCaptionVisually={false}
            headers={['Assessment Type', 'Overall Score', 'Submitted At', 'Review']}
          >
            {attempts.slice(0, 5).map((att) => (
              <tr key={att.attempt_id}>
                <th scope="row" className="px-4 py-3 font-semibold text-slate-900">
                  {att.test_type}
                </th>
                <td className="px-4 py-3">
                  <Badge tone={att.overall_score_percent >= 70 ? 'success' : 'warning'}>
                    {att.overall_score_percent.toFixed(1)}%
                  </Badge>
                </td>
                <td className="px-4 py-3 text-xs text-slate-600">
                  {new Date(att.submitted_at).toLocaleString()}
                </td>
                <td className="px-4 py-3">
                  <Link
                    to={`/assessment/attempts/${att.attempt_id}`}
                    aria-label={`Review solutions for ${att.test_type} scored ${att.overall_score_percent.toFixed(1)}%`}
                    className="text-xs font-semibold text-blue-600 hover:underline"
                  >
                    Solution Review
                  </Link>
                </td>
              </tr>
            ))}
          </ResponsiveTable>
        ) : null}
      </div>
    </AppLayout>
  );
}
