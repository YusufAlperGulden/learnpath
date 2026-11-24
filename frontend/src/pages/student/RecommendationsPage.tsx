import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  AlertCircle,
  Bookmark,
  CheckCircle2,
  ExternalLink,
  GraduationCap,
  Sparkles,
  Star,
} from 'lucide-react';
import { studentApi } from '../../api/student';
import { AppLayout } from '../../components/layout/AppLayout';
import {
  FeedbackModal,
  type FeedbackTarget,
} from '../../components/student/FeedbackModal';
import { Badge, Button, Card, cn } from '../../components/ui';
import type { RecommenderStrategy } from '../../types/api';

const VALID_STRATEGIES: RecommenderStrategy[] = [
  'hybrid',
  'cbf',
  'cf',
  'popularity',
  'rule_based',
];

function parseStrategyParam(raw: string | null): RecommenderStrategy {
  if (raw && (VALID_STRATEGIES as string[]).includes(raw)) {
    return raw as RecommenderStrategy;
  }
  return 'hybrid';
}

function describeFallbackReason(reason: string | null): string {
  if (reason === 'cold_start_insufficient_neighbors') {
    return 'Cold-Start Safeguard Active: Insufficient overlapping peer ratings exist for your profile yet, so rankings and explanations automatically switched to Content-Based TF-IDF and proficiency signals without fabricating peer claims.';
  }
  if (reason === 'preferred_format_relaxed') {
    return 'Fewer than 5 unseen resources matched your exact preferred format(s), so additional formats were transparently included and badged below.';
  }
  if (reason === 'prerequisite_not_mastered') {
    return 'The requested topic is currently locked because one or more prerequisite topics have not reached >= 70% MASTERED. Recommendations were automatically redirected to your unlocked prerequisite topic(s).';
  }
  return reason
    ? `Fallback applied (${reason}).`
    : 'Format, prerequisite, or cold-start fallback was applied to ensure relevant study options.';
}

export function RecommendationsPage() {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedTopicId = searchParams.get('topicId') || '';
  const selectedStrategy = parseStrategyParam(searchParams.get('strategy'));
  const includeCompleted = searchParams.get('revision') === '1';
  const [feedbackTarget, setFeedbackTarget] = useState<FeedbackTarget | null>(null);

  useEffect(() => {
    document.title = 'Explainable Recommendations | LearnPath';
  }, []);

  const { data: pathData } = useQuery({
    queryKey: ['learning-path'],
    queryFn: studentApi.getLearningPath,
  });

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['recommendations', selectedStrategy, selectedTopicId, includeCompleted],
    queryFn: () =>
      studentApi.getRecommendations({
        strategy: selectedStrategy,
        limit: 5,
        topic_id: selectedTopicId || undefined,
        include_completed: includeCompleted || undefined,
      }),
  });

  const updateFilterParams = (
    nextTopicId: string,
    nextStrategy: RecommenderStrategy,
    nextRevision: boolean = includeCompleted,
  ) => {
    const next: Record<string, string> = {};
    if (nextTopicId) next.topicId = nextTopicId;
    if (nextStrategy !== 'hybrid') next.strategy = nextStrategy;
    if (nextRevision) next.revision = '1';
    setSearchParams(next);
  };

  const invalidateAfterInteraction = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['recommendations'] }),
      queryClient.invalidateQueries({ queryKey: ['bookmarks'] }),
      queryClient.invalidateQueries({ queryKey: ['resource-history'] }),
    ]);
  };

  const openMutation = useMutation({
    mutationFn: (resourceId: string) => studentApi.recordResourceOpen(resourceId),
    onSuccess: invalidateAfterInteraction,
  });

  const completeMutation = useMutation({
    mutationFn: (resourceId: string) => studentApi.setResourceProgress(resourceId, 'COMPLETED'),
    onSuccess: invalidateAfterInteraction,
  });

  const bookmarkMutation = useMutation({
    mutationFn: async ({
      resourceId,
      isBookmarked,
    }: {
      resourceId: string;
      isBookmarked: boolean;
    }) => {
      if (isBookmarked) {
        await studentApi.removeBookmark(resourceId);
      } else {
        await studentApi.saveBookmark(resourceId);
      }
    },
    onSuccess: invalidateAfterInteraction,
  });

  const nodes = pathData?.nodes ?? [];
  const priorityChartData = (data?.priority_topics ?? []).map((pt) => ({
    name: pt.name,
    score_percent: pt.score_percent ?? 0,
  }));

  return (
    <AppLayout
      pageTitle="Personalized Resource Recommendations"
      pageSubtitle="Prerequisite-aware study resources ranked with transparent explanations, bookmarking, completion tracking, and 1–5 ratings (FR05–FR09)."
    >
      <Card className="mb-6 flex flex-wrap items-end justify-between gap-4 p-4">
        <div className="flex flex-wrap items-end gap-4">
          <div className="flex flex-col gap-1">
            <label htmlFor="rec-topic-filter" className="text-xs font-semibold text-slate-700">
              Focus topic (or automatic gap priority)
            </label>
            <select
              id="rec-topic-filter"
              name="topic_id"
              value={selectedTopicId}
              onChange={(e) => updateFilterParams(e.target.value, selectedStrategy)}
              className="min-h-10 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900"
            >
              <option value="">Automatic Priority Topics (Recommended)</option>
              {nodes.map((n) => (
                <option key={n.topic_id} value={n.topic_id}>
                  {n.display_order}. {n.name} {n.is_locked ? '(LOCKED)' : `(${n.mastery_status})`}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-1">
            <label htmlFor="rec-strategy-select" className="text-xs font-semibold text-slate-700">
              Ranking model (5-method architecture)
            </label>
            <select
              id="rec-strategy-select"
              name="strategy"
              value={selectedStrategy}
              onChange={(e) =>
                updateFilterParams(selectedTopicId, e.target.value as RecommenderStrategy)
              }
              className="min-h-10 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900"
            >
              <option value="hybrid">Weighted Hybrid (CBF + CF, Default)</option>
              <option value="cbf">Content-Based Filtering (TF-IDF)</option>
              <option value="cf">Collaborative Filtering (User-Resource Matrix)</option>
              <option value="popularity">Popularity Baseline (Empirical Ratings)</option>
              <option value="rule_based">Rule-Based Prototype (Heuristic)</option>
            </select>
          </div>

          <div className="flex items-center gap-2 pb-1">
            <Badge tone="info">Served Strategy: {data?.strategy_used ?? selectedStrategy}</Badge>
          </div>

          <div className="flex items-center gap-2 pb-1">
            <input
              id="rec-include-completed"
              name="include_completed"
              type="checkbox"
              checked={includeCompleted}
              onChange={(e) =>
                updateFilterParams(selectedTopicId, selectedStrategy, e.target.checked)
              }
              className="h-4 w-4 cursor-pointer rounded border-slate-400 accent-blue-600"
            />
            <label
              htmlFor="rec-include-completed"
              className="cursor-pointer text-xs font-semibold text-slate-700"
            >
              Include completed for revision
            </label>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-4">
          <Link
            to="/bookmarks"
            className="text-xs font-semibold text-slate-700 hover:text-slate-900 hover:underline"
          >
            Open Saved &amp; Study History
          </Link>
          <Link
            to="/profile/setup"
            className="text-xs font-semibold text-blue-600 hover:underline"
          >
            Adjust preferences
          </Link>
        </div>
      </Card>

      {data?.fallback_applied ? (
        <div
          role="status"
          className="mb-6 flex items-start gap-3 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3.5 text-sm text-amber-950"
        >
          <AlertCircle aria-hidden="true" className="mt-0.5 h-5 w-5 shrink-0 text-amber-700" />
          <div>
            <p className="font-semibold">Transparent Recommendation Fallback Applied</p>
            <p className="mt-0.5 text-xs text-amber-900">
              {describeFallbackReason(data.fallback_reason)}
            </p>
          </div>
        </div>
      ) : null}

      {data && data.priority_topics.length > 0 ? (
        <div className="mb-6 grid gap-6 lg:grid-cols-3">
          <Card className="space-y-3">
            <h2 className="text-sm font-semibold text-slate-900">Current Priority Topics</h2>
            <ul className="space-y-2.5">
              {data.priority_topics.map((pt) => (
                <li
                  key={pt.topic_id}
                  className="flex items-center justify-between gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs"
                >
                  <div>
                    <p className="font-semibold text-slate-900">{pt.name}</p>
                    <p className="text-slate-600">
                      Latest score:{' '}
                      {pt.score_percent !== null ? `${pt.score_percent.toFixed(0)}%` : 'Unassessed'}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge tone={pt.mastery_status === 'MASTERED' ? 'success' : 'warning'}>
                      {pt.mastery_status}
                    </Badge>
                    <Link
                      to={`/assessment?type=TOPIC_QUIZ&topicId=${pt.topic_id}`}
                      aria-label={`Start Topic Quiz for ${pt.name}`}
                      className="rounded bg-blue-600 px-2.5 py-1 font-semibold text-white hover:bg-blue-700"
                    >
                      Quiz
                    </Link>
                  </div>
                </li>
              ))}
            </ul>
          </Card>

          <Card className="lg:col-span-2">
            <figure>
              <figcaption className="mb-2 text-sm font-semibold text-slate-900">
                Priority Topic Proficiency vs. 70% Mastery Gate
              </figcaption>
              <div className="h-44 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={priorityChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} unit="%" />
                    <Tooltip />
                    <ReferenceLine y={70} stroke="#059669" strokeDasharray="4 4" />
                    <Bar dataKey="score_percent" name="Score %" fill="#2563eb" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </figure>
          </Card>
        </div>
      ) : null}

      {isLoading ? (
        <Card className="p-8 text-center text-sm text-slate-600">
          Ranking personalized learning resources...
        </Card>
      ) : isError ? (
        <Card role="alert" className="space-y-3 border-red-200 bg-red-50 p-6 text-center text-sm text-red-900">
          <p className="font-semibold">
            Could not load recommendations right now. Your saved assessments and progress are safe.
          </p>
          <div>
            <Button size="sm" variant="primary" onClick={() => void refetch()}>
              Retry Recommendations
            </Button>
          </div>
        </Card>
      ) : !data || data.items.length === 0 ? (
        <Card className="space-y-3 p-8 text-center text-sm text-slate-700">
          <p className="font-semibold text-slate-900">
            No unseen active resources remain for your current filter and language preference.
          </p>
          <div className="flex flex-wrap justify-center gap-3 pt-1">
            {!includeCompleted ? (
              <Button
                size="sm"
                variant="outline"
                onClick={() => updateFilterParams(selectedTopicId, selectedStrategy, true)}
              >
                Offer Completed Resources for Revision
              </Button>
            ) : null}
            <Link
              to="/profile/setup"
              className="inline-flex min-h-9 items-center rounded-lg bg-blue-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-blue-700"
            >
              Revise Profile Preferences
            </Link>
          </div>
        </Card>
      ) : (
        <div className="space-y-4">
          {data.items.map((item) => {
            const bookmarked = Boolean(item.is_bookmarked);
            return (
              <Card key={item.resource_id} className="space-y-3.5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone="neutral">#{item.rank}</Badge>
                    <Badge tone="info">{item.topic_name}</Badge>
                    <Badge tone="neutral">{item.content_type}</Badge>
                    <Badge
                      tone={
                        item.difficulty === 'BEGINNER'
                          ? 'success'
                          : item.difficulty === 'INTERMEDIATE'
                            ? 'info'
                            : 'warning'
                      }
                    >
                      {item.difficulty}
                    </Badge>
                    <span className="text-xs font-medium text-slate-500">
                      {item.language.toUpperCase()}
                      {item.estimated_minutes ? ` · ${item.estimated_minutes} min` : ''}
                    </span>
                    {item.progress_status === 'OPENED' ? (
                      <Badge tone="info">OPENED</Badge>
                    ) : item.progress_status === 'COMPLETED' ? (
                      <Badge tone="success">COMPLETED · Revision</Badge>
                    ) : null}
                    {item.format_fallback_used ? (
                      <Badge tone="warning">Format Relaxed</Badge>
                    ) : null}
                    {item.my_rating ? (
                      <Badge tone="warning">{item.my_rating}/5 ★</Badge>
                    ) : null}
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <a
                      href={item.external_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label={`Study resource ${item.title}`}
                      onClick={() => openMutation.mutate(item.resource_id)}
                      className="inline-flex min-h-9 items-center gap-1.5 rounded-lg bg-blue-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-blue-700"
                    >
                      Study Resource
                      <ExternalLink aria-hidden="true" className="h-3.5 w-3.5" />
                    </a>

                    <Button
                      variant="outline"
                      size="sm"
                      aria-label={`Mark ${item.title} as completed`}
                      onClick={() => completeMutation.mutate(item.resource_id)}
                    >
                      <CheckCircle2 aria-hidden="true" className="h-3.5 w-3.5 text-emerald-600" />
                      Mark Completed
                    </Button>

                    <Button
                      variant="outline"
                      size="sm"
                      aria-pressed={bookmarked}
                      aria-label={`${bookmarked ? 'Remove bookmark' : 'Save bookmark'} for ${item.title}`}
                      onClick={() =>
                        bookmarkMutation.mutate({
                          resourceId: item.resource_id,
                          isBookmarked: bookmarked,
                        })
                      }
                    >
                      <Bookmark
                        aria-hidden="true"
                        className={cn(
                          'h-3.5 w-3.5',
                          bookmarked ? 'fill-blue-600 text-blue-600' : 'text-slate-600',
                        )}
                      />
                      {bookmarked ? 'Saved' : 'Save'}
                    </Button>

                    <Button
                      variant="outline"
                      size="sm"
                      aria-label={`Rate ${item.title}`}
                      onClick={() =>
                        setFeedbackTarget({
                          resource_id: item.resource_id,
                          title: item.title,
                          initialRating: item.my_rating,
                          initialComment: item.my_comment,
                        })
                      }
                    >
                      <Star aria-hidden="true" className="h-3.5 w-3.5 text-amber-500" />
                      {item.my_rating ? `${item.my_rating}★` : 'Rate'}
                    </Button>

                    <Link
                      to={`/assessment?type=TOPIC_QUIZ&topicId=${item.topic_id}`}
                      aria-label={`Verify mastery quiz for ${item.topic_name}`}
                      className="inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-800 hover:bg-slate-50"
                    >
                      <GraduationCap aria-hidden="true" className="h-3.5 w-3.5" />
                      Quiz
                    </Link>
                  </div>
                </div>

                <div>
                  <h3 className="text-base font-bold text-slate-900">{item.title}</h3>
                  <p className="mt-1 text-sm text-slate-600">{item.description}</p>
                </div>

                <div className="flex items-start gap-2.5 rounded-xl border border-blue-200 bg-blue-50/70 px-4 py-3 text-xs text-slate-800">
                  <Sparkles aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0 text-blue-700" />
                  <div>
                    <span className="font-semibold text-blue-950">Why this was recommended: </span>
                    {item.rationale}
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      <FeedbackModal target={feedbackTarget} onClose={() => setFeedbackTarget(null)} />
    </AppLayout>
  );
}
