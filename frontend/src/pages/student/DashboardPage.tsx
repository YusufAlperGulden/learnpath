import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { AppLayout } from '../../components/layout/AppLayout';
import { Badge, Card, ProgressBar } from '../../components/ui';
import type { LearningPathResponse, StudentProfile } from '../../types/api';

export function DashboardPage() {
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
    queryFn: async () => (await apiClient.get<LearningPathResponse>('/learning-path')).data,
  });

  const nodes = pathData?.nodes ?? [];
  const masteredCount = nodes.filter((n) => n.mastery_status === 'MASTERED').length;
  const manualCompletedCount = nodes.filter((n) => n.is_manually_completed).length;

  return (
    <AppLayout
      pageTitle={profile ? `Welcome back, ${profile.display_name}` : 'Student Overview'}
      pageSubtitle="Track your Python topic mastery, manual study completion, and next recommended steps."
    >
      <div className="grid gap-6 md:grid-cols-2">
        <Card className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-slate-900">Curriculum Progress</h2>
            <Badge tone="info">{nodes.length} Topics</Badge>
          </div>
          <ProgressBar
            label="Exam-Verified Mastery (>= 70%)"
            value={masteredCount}
            max={Math.max(nodes.length, 1)}
          />
          <ProgressBar
            label="Self-Reported Study Completion"
            value={manualCompletedCount}
            max={Math.max(nodes.length, 1)}
          />
          <div className="flex flex-wrap gap-3 pt-2">
            <Link
              to="/roadmap"
              className="inline-flex min-h-10 items-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Open Prerequisite Roadmap
            </Link>
            <Link
              to="/assessment"
              className="inline-flex min-h-10 items-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50"
            >
              Start Placement Exam
            </Link>
          </div>
        </Card>

        <Card className="space-y-3">
          <h2 className="text-base font-semibold text-slate-900">Active Profile Preferences</h2>
          {profile ? (
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-slate-500">Goal</dt>
                <dd className="font-medium text-slate-900">{profile.learning_goal}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Experience</dt>
                <dd className="font-medium text-slate-900">{profile.experience_level}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Formats</dt>
                <dd className="font-medium text-slate-900">
                  {profile.preferred_formats.join(', ')}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">Language</dt>
                <dd className="font-medium text-slate-900">{profile.preferred_language}</dd>
              </div>
            </dl>
          ) : (
            <p className="text-sm text-slate-600">
              Configure your profile preferences to personalize resource rankings.{' '}
              <Link to="/profile/setup" className="font-semibold text-blue-600 hover:underline">
                Set up profile
              </Link>
            </p>
          )}
        </Card>
      </div>
    </AppLayout>
  );
}
