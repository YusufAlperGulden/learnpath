import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Cell, Pie, PieChart, ResponsiveContainer } from 'recharts';
import {
  AlertCircle,
  ArrowRight,
  Bookmark,
  CheckCircle2,
  Code2,
  ExternalLink,
  FileText,
  GraduationCap,
  PlayCircle,
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
import type { ContentType, MasteryStatus, RecommenderStrategy } from '../../types/api';

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

function FormatIcon({ type, className }: { type: ContentType; className?: string }) {
  if (type === 'VIDEO') return <PlayCircle aria-hidden="true" className={className} />;
  if (type === 'EXERCISE') return <Code2 aria-hidden="true" className={className} />;
  return <FileText aria-hidden="true" className={className} />;
}

export function RecommendationsPage() {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedTopicId = searchParams.get('topicId') || '';
  const selectedStrategy = parseStrategyParam(searchParams.get('strategy'));
  const includeCompleted = searchParams.get('revision') === '1';
  const requestedAttemptId = searchParams.get('attemptId');
  const keywordQuery = (searchParams.get('q') || '').trim();
  const [feedbackTarget, setFeedbackTarget] = useState<FeedbackTarget | null>(null);

  useEffect(() => {
    document.title = 'Placement Results & Recommendations | LearnPath';
  }, []);

  const { data: pathData } = useQuery({
    queryKey: ['learning-path'],
    queryFn: studentApi.getLearningPath,
  });

  const { data: attempts = [] } = useQuery({
    queryKey: ['attempts'],
    queryFn: studentApi.listAttempts,
  });

  const targetAttemptId = requestedAttemptId || attempts[0]?.attempt_id || '';

  const { data: attemptDetail } = useQuery({
    queryKey: ['attempt-detail', targetAttemptId],
    queryFn: () => studentApi.getAttemptDetail(targetAttemptId),
    enabled: Boolean(targetAttemptId),
  });

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['recommendations', selectedStrategy, selectedTopicId, includeCompleted],
    queryFn: () =>
      studentApi.getRecommendations({
        strategy: selectedStrategy,
        limit: 6,
        topic_id: selectedTopicId || undefined,
        include_completed: includeCompleted || undefined,
      }),
  });

  const updateFilterParams = (
    nextTopicId: string,
    nextStrategy: RecommenderStrategy,
    nextRevision: boolean = includeCompleted,
    nextQuery: string = keywordQuery,
  ) => {
    const next: Record<string, string> = {};
    if (nextTopicId) next.topicId = nextTopicId;
    if (nextStrategy !== 'hybrid') next.strategy = nextStrategy;
    if (nextRevision) next.revision = '1';
    if (requestedAttemptId) next.attemptId = requestedAttemptId;
    if (nextQuery) next.q = nextQuery;
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

  const overallScore = useMemo(() => {
    if (attemptDetail) return Math.round(attemptDetail.overall_score_percent);
    if (nodes.length > 0) {
      const mastered = nodes.filter((n) => n.mastery_status === 'MASTERED').length;
      return Math.round((mastered / nodes.length) * 100);
    }
    return 0;
  }, [attemptDetail, nodes]);

  const donutData = useMemo(
    () => [
      { name: 'Score', value: Math.max(overallScore, 0), color: '#14532d' },
      { name: 'Remaining', value: Math.max(100 - overallScore, 0), color: '#dfeae3' },
    ],
    [overallScore],
  );

  const topicBreakdown = useMemo(() => {
    const lockedById = new Map(nodes.map((n) => [n.topic_id, n.is_locked]));
    if (attemptDetail && attemptDetail.topic_scores.length > 0) {
      return attemptDetail.topic_scores.map((ts) => ({
        topic_id: ts.topic_id,
        name: ts.topic_name,
        percent: Math.round(ts.score_percent) as number | null,
        status: ts.mastery_status,
        isLocked: lockedById.get(ts.topic_id) ?? false,
      }));
    }
    return nodes.map((n) => ({
      topic_id: n.topic_id,
      name: n.name,
      percent: n.latest_score_percent === null ? null : Math.round(n.latest_score_percent),
      status: n.mastery_status as MasteryStatus,
      isLocked: n.is_locked,
    }));
  }, [attemptDetail, nodes]);

  const visibleItems = useMemo(() => {
    const items = data?.items ?? [];
    if (!keywordQuery) return items;
    const needle = keywordQuery.toLowerCase();
    return items.filter(
      (it) =>
        it.title.toLowerCase().includes(needle) ||
        it.description.toLowerCase().includes(needle) ||
        it.topic_name.toLowerCase().includes(needle),
    );
  }, [data?.items, keywordQuery]);

  return (
    <AppLayout
      variant="focused"
      showInlineNav
      eyebrow="Your Personalized Starting Point"
      pageTitle="A clearer path to Python confidence."
      pageSubtitle="Review your placement breakdown and study explainable resources tailored to your unlocked priority gaps."
    >
      {/* Top 2-Column Placement Results & Topic Breakdown Row (Figma Screen 6) */}
      <div className="mb-7 grid gap-5 lg:grid-cols-12">
        {/* Left Card: Placement Test Results Donut */}
        <Card className="flex flex-col justify-between rounded-2xl border-[#dce6df] p-6 lg:col-span-5">
          <div>
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-base font-bold text-slate-900">Placement Test Results</h2>
              {attemptDetail ? (
                <Badge tone={overallScore >= 70 ? 'success' : 'info'}>
                  {attemptDetail.test_type === 'DIAGNOSTIC' ? 'Placement' : 'Topic Quiz'}
                </Badge>
              ) : (
                <Badge tone="warning">No test taken yet</Badge>
              )}
            </div>
            <p className="mt-0.5 text-xs text-slate-500">
              {attemptDetail ? 'Overall Score: ' : 'Curriculum mastery (no placement test yet): '}
              <strong className="text-slate-800">{overallScore} / 100</strong>
            </p>
          </div>

          <figure className="my-4 flex flex-wrap items-center gap-5">
            <div className="relative h-28 w-28 shrink-0">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={donutData}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={36}
                    outerRadius={50}
                    startAngle={90}
                    endAngle={-270}
                    stroke="none"
                  >
                    {donutData.map((entry) => (
                      <Cell key={entry.name} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
                <span className="text-xl font-extrabold text-[#14532d]">{overallScore}%</span>
              </div>
            </div>

            <div className="min-w-[160px] flex-1 space-y-1.5">
              <span className="inline-flex items-center rounded-full bg-[#e6f2eb] px-2.5 py-0.5 text-xs font-semibold text-[#14532d]">
                {attemptDetail
                  ? overallScore >= 70
                    ? 'A strong foundation'
                    : 'Priority focus identified'
                  : 'Ready for calibration'}
              </span>
              <p className="text-xs leading-relaxed text-slate-600">
                {attemptDetail
                  ? 'Topics scoring >= 70% are mastered; unlocked gaps below 70% are prioritized first.'
                  : 'Take the diagnostic placement test anytime to calibrate your exact topic scores.'}
              </p>
            </div>
            <figcaption className="visually-hidden">
              Overall placement test score is {overallScore} percent.
            </figcaption>
          </figure>

          <div className="flex flex-wrap items-center gap-3 border-t border-slate-100 pt-3 text-xs">
            {attemptDetail ? (
              <Link
                to={`/assessment/attempts/${attemptDetail.attempt_id}`}
                className="font-semibold text-[#14532d] hover:underline"
              >
                Review detailed gap analysis &rarr;
              </Link>
            ) : (
              <Link
                to="/assessment"
                className="font-semibold text-[#14532d] hover:underline"
              >
                Take placement test &rarr;
              </Link>
            )}
          </div>
        </Card>

        {/* Right Card: Topic Based Breakdown Horizontal Bars */}
        <Card className="rounded-2xl border-[#dce6df] p-6 lg:col-span-7">
          <div className="mb-4 flex items-center justify-between gap-2">
            <div>
              <h2 className="text-base font-bold text-slate-900">Topic Based Breakdown</h2>
              <p className="text-xs text-slate-500">70% threshold required for exam mastery</p>
            </div>
            <Link
              to="/profile/setup"
              className="text-xs font-semibold text-[#14532d] hover:underline"
            >
              Adjust preferences
            </Link>
          </div>

          {topicBreakdown.length === 0 ? (
            <p className="py-6 text-sm text-slate-600">No curriculum topics available yet.</p>
          ) : (
            <ul className="space-y-3">
              {topicBreakdown.map((tb) => {
                const pct = tb.percent;
                const notAssessed = pct === null;
                const isMastered = !notAssessed && (tb.status === 'MASTERED' || pct >= 70);
                const isPriority = !notAssessed && pct < 50 && !isMastered;
                const barClass = isMastered
                  ? 'bg-[#14532d]'
                  : isPriority
                    ? 'bg-amber-500'
                    : 'bg-[#5c9a76]';
                const statusLabel = tb.isLocked
                  ? 'Locked'
                  : notAssessed
                    ? 'Not assessed yet'
                    : isMastered
                      ? 'Mastered'
                      : isPriority
                        ? 'Priority Focus'
                        : 'Needs Practice';

                return (
                  <li key={tb.topic_id} className="space-y-1">
                    <div className="flex items-center justify-between gap-2 text-xs">
                      <span className="font-semibold text-slate-800">{tb.name}</span>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-700">
                          {notAssessed ? '—' : `${pct}%`}
                        </span>
                        <span
                          className={cn(
                            'text-[11px] font-semibold',
                            isMastered
                              ? 'text-[#14532d]'
                              : isPriority
                                ? 'text-amber-700'
                                : 'text-slate-600',
                          )}
                        >
                          · {statusLabel}
                        </span>
                        {!tb.isLocked ? (
                          <Link
                            to={`/assessment?type=TOPIC_QUIZ&topicId=${tb.topic_id}`}
                            aria-label={`Start Topic Quiz for ${tb.name}`}
                            className="rounded bg-[#e6f2eb] px-2 py-0.5 text-[10px] font-bold text-[#14532d] hover:bg-[#d3e7db]"
                          >
                            Quiz
                          </Link>
                        ) : null}
                      </div>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-[#e3ece6]">
                      {!notAssessed ? (
                        <div
                          className={cn('h-full rounded-full transition-all', barClass)}
                          style={{ width: `${Math.min(Math.max(pct, 4), 100)}%` }}
                        />
                      ) : null}
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>
      </div>

      {/* Compact Strategy & Topic Controls Bar (Preserves 5-Method Selector & Revision Toggle) */}
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4 rounded-2xl border border-[#dce6df] bg-white p-4">
        <div className="flex flex-wrap items-end gap-4">
          <div className="flex flex-col gap-1">
            <label htmlFor="rec-topic-filter" className="text-xs font-semibold text-slate-700">
              Focus topic
            </label>
            <select
              id="rec-topic-filter"
              name="topic_id"
              value={selectedTopicId}
              onChange={(e) => updateFilterParams(e.target.value, selectedStrategy)}
              className="min-h-9 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-900"
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
              Ranking model (5-method engine)
            </label>
            <select
              id="rec-strategy-select"
              name="strategy"
              value={selectedStrategy}
              onChange={(e) =>
                updateFilterParams(selectedTopicId, e.target.value as RecommenderStrategy)
              }
              className="min-h-9 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-900"
            >
              <option value="hybrid">Weighted Hybrid (CBF + CF, Default)</option>
              <option value="cbf">Content-Based Filtering (TF-IDF)</option>
              <option value="cf">Collaborative Filtering (User-Resource Matrix)</option>
              <option value="popularity">Popularity Baseline (Empirical Ratings)</option>
              <option value="rule_based">Rule-Based Prototype (Heuristic)</option>
            </select>
          </div>

          <div className="flex items-center gap-2 pb-1.5">
            <input
              id="rec-include-completed"
              name="include_completed"
              type="checkbox"
              checked={includeCompleted}
              onChange={(e) =>
                updateFilterParams(selectedTopicId, selectedStrategy, e.target.checked)
              }
              className="h-4 w-4 cursor-pointer rounded border-slate-400 accent-[#14532d]"
            />
            <label
              htmlFor="rec-include-completed"
              className="cursor-pointer text-xs font-semibold text-slate-700"
            >
              Include completed for revision
            </label>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {keywordQuery ? (
            <button
              type="button"
              onClick={() => updateFilterParams(selectedTopicId, selectedStrategy, includeCompleted, '')}
              className="inline-flex items-center gap-1 rounded-full border border-[#9dc4ac] bg-[#e6f2eb] px-2.5 py-0.5 text-xs font-semibold text-[#14532d]"
            >
              <span>Search: &ldquo;{keywordQuery}&rdquo; &times;</span>
            </button>
          ) : null}
          <Badge tone="info">Served: {data?.strategy_used ?? selectedStrategy}</Badge>
          <Link
            to="/bookmarks"
            className="text-xs font-semibold text-[#14532d] hover:underline"
          >
            Saved library
          </Link>
        </div>
      </div>

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

      {/* Recommended Resources For You — 3-Column Card Grid (Figma Screen 6) */}
      <section aria-labelledby="rec-grid-heading" className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 id="rec-grid-heading" className="text-lg font-bold text-slate-900">
            Recommended Resources For You
          </h2>
          <span className="text-xs font-medium text-slate-500">
            {data?.items.length ? `Top ${data.items.length} matches` : ''}
          </span>
        </div>

        {isLoading ? (
          <Card className="p-10 text-center text-sm text-slate-600">
            Ranking personalized learning resources...
          </Card>
        ) : isError ? (
          <Card
            role="alert"
            className="space-y-3 border-red-200 bg-red-50 p-6 text-center text-sm text-red-900"
          >
            <p className="font-semibold">
              Could not load recommendations right now. Your saved assessments and progress are
              safe.
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
                className="inline-flex min-h-9 items-center rounded-lg bg-[#14532d] px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-[#0f3f22]"
              >
                Revise Profile Preferences
              </Link>
            </div>
          </Card>
        ) : visibleItems.length === 0 ? (
          <Card role="status" className="space-y-3 p-8 text-center text-sm text-slate-700">
            <p className="font-semibold text-slate-900">
              None of your current recommendations match &ldquo;{keywordQuery}&rdquo;.
            </p>
            <Button
              size="sm"
              variant="outline"
              onClick={() =>
                updateFilterParams(selectedTopicId, selectedStrategy, includeCompleted, '')
              }
            >
              Clear search
            </Button>
          </Card>
        ) : (
          <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
            {visibleItems.map((item) => {
              const bookmarked = Boolean(item.is_bookmarked);
              return (
                <Card
                  key={item.resource_id}
                  className="flex flex-col justify-between rounded-2xl border-[#dce6df] p-5 shadow-xs"
                >
                  <div className="space-y-3">
                    {/* Card Header: Green Icon Square + Format Badge */}
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#e6f2eb] text-[#14532d]">
                          <FormatIcon type={item.content_type} className="h-4 w-4" />
                        </span>
                        <div>
                          <p className="text-[11px] font-bold text-[#14532d]">{item.topic_name}</p>
                          <p className="text-[11px] text-slate-500">
                            #{item.rank} · {item.language.toUpperCase()}
                          </p>
                        </div>
                      </div>

                      <div className="flex flex-wrap justify-end gap-1">
                        <Badge tone="info">{item.content_type}</Badge>
                        {item.format_fallback_used ? (
                          <Badge tone="warning">Format Relaxed</Badge>
                        ) : null}
                      </div>
                    </div>

                    {/* Title & Description */}
                    <div>
                      <h3 className="text-base font-bold leading-snug text-slate-900">
                        {item.title}
                      </h3>
                      <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-slate-600">
                        {item.description}
                      </p>
                    </div>

                    {/* Metadata & Status Badges */}
                    <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                      <span>
                        {item.estimated_minutes ? `${item.estimated_minutes} min · ` : ''}
                        {item.difficulty.charAt(0) + item.difficulty.slice(1).toLowerCase()}
                      </span>
                      {item.progress_status === 'OPENED' ? (
                        <Badge tone="info">OPENED</Badge>
                      ) : item.progress_status === 'COMPLETED' ? (
                        <Badge tone="success">COMPLETED</Badge>
                      ) : null}
                      {item.my_rating ? <Badge tone="warning">{item.my_rating}★</Badge> : null}
                    </div>

                    {/* Action Row */}
                    <div className="flex flex-wrap items-center gap-1.5 pt-1">
                      <a
                        href={item.external_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        aria-label={`Study resource ${item.title}`}
                        onClick={() => openMutation.mutate(item.resource_id)}
                        className="inline-flex min-h-8 items-center gap-1 rounded-lg bg-[#14532d] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#0f3f22]"
                      >
                        <span>Open Resource</span>
                        <ExternalLink aria-hidden="true" className="h-3 w-3" />
                      </a>

                      <button
                        type="button"
                        aria-label={`Mark ${item.title} as completed`}
                        onClick={() => completeMutation.mutate(item.resource_id)}
                        className="inline-flex min-h-8 items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 hover:border-[#14532d]/40 hover:bg-[#f4f8f5]"
                      >
                        <CheckCircle2
                          aria-hidden="true"
                          className="h-3.5 w-3.5 text-[#14532d]"
                        />
                        <span>Done</span>
                      </button>

                      <button
                        type="button"
                        aria-pressed={bookmarked}
                        aria-label={`${bookmarked ? 'Remove bookmark' : 'Save bookmark'} for ${item.title}`}
                        onClick={() =>
                          bookmarkMutation.mutate({
                            resourceId: item.resource_id,
                            isBookmarked: bookmarked,
                          })
                        }
                        className="inline-flex min-h-8 items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 hover:border-[#14532d]/40 hover:bg-[#f4f8f5]"
                      >
                        <Bookmark
                          aria-hidden="true"
                          className={cn(
                            'h-3.5 w-3.5',
                            bookmarked ? 'fill-[#14532d] text-[#14532d]' : 'text-slate-500',
                          )}
                        />
                        <span>{bookmarked ? 'Saved' : 'Save'}</span>
                      </button>

                      <button
                        type="button"
                        aria-label={`Rate ${item.title}`}
                        onClick={() =>
                          setFeedbackTarget({
                            resource_id: item.resource_id,
                            title: item.title,
                            initialRating: item.my_rating,
                            initialComment: item.my_comment,
                          })
                        }
                        className="inline-flex min-h-8 items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 hover:border-[#14532d]/40 hover:bg-[#f4f8f5]"
                      >
                        <Star aria-hidden="true" className="h-3.5 w-3.5 text-amber-500" />
                        <span>{item.my_rating ? `${item.my_rating}★` : 'Rate'}</span>
                      </button>

                      <Link
                        to={`/assessment?type=TOPIC_QUIZ&topicId=${item.topic_id}`}
                        aria-label={`Verify mastery quiz for ${item.topic_name}`}
                        className="inline-flex min-h-8 items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 hover:border-[#14532d]/40 hover:bg-[#f4f8f5]"
                      >
                        <GraduationCap aria-hidden="true" className="h-3.5 w-3.5" />
                        <span>Quiz</span>
                      </Link>
                    </div>
                  </div>

                  {/* Green Rationale Footer Box (Figma Screen 6) */}
                  <div className="mt-4 flex items-start gap-2 rounded-xl border border-[#b9d8c5] bg-[#edf6f0] p-3 text-xs text-slate-800">
                    <Sparkles
                      aria-hidden="true"
                      className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#14532d]"
                    />
                    <p className="leading-relaxed">
                      <strong className="font-semibold text-[#14532d]">Why recommended: </strong>
                      {item.rationale}
                    </p>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </section>

      {/* Bottom Mint Learning Path CTA Banner (Figma Screen 6) */}
      <div className="mt-8 flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-[#c6ded0] bg-[#e6f2eb] px-6 py-4">
        <div>
          <p className="text-sm font-bold text-[#14532d]">Your learning path is ready.</p>
          <p className="text-xs text-slate-700">
            Explore your prerequisite-aware Python curriculum graph and track dual progress.
          </p>
        </div>
        <Link
          to="/roadmap"
          className="inline-flex min-h-10 items-center gap-2 rounded-xl bg-[#14532d] px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-[#0f3f22]"
        >
          <span>View Learning Path</span>
          <ArrowRight aria-hidden="true" className="h-4 w-4" />
        </Link>
      </div>

      <FeedbackModal target={feedbackTarget} onClose={() => setFeedbackTarget(null)} />
    </AppLayout>
  );
}
