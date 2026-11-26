import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ArrowRight,
  Bookmark,
  Code2,
  ExternalLink,
  FileText,
  GraduationCap,
  PlayCircle,
  Sparkles,
  Star,
} from 'lucide-react';
import {
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
} from 'recharts';
import { apiClient } from '../../api/client';
import { studentApi } from '../../api/student';
import { AppLayout } from '../../components/layout/AppLayout';
import { Badge, Card, InlineCodeText, ProgressBar, cn } from '../../components/ui';
import type { ContentType, StudentProfile } from '../../types/api';

function FormatIcon({ type, className }: { type: ContentType; className?: string }) {
  if (type === 'VIDEO') return <PlayCircle aria-hidden="true" className={className} />;
  if (type === 'EXERCISE') return <Code2 aria-hidden="true" className={className} />;
  return <FileText aria-hidden="true" className={className} />;
}

const BANNER_TONES = [
  'bg-[#dceee3] text-[#14532d]',
  'bg-[#d5e5dc] text-[#14532d]',
  'bg-[#e6f1ea] text-[#14532d]',
];

export function DashboardPage() {
  const queryClient = useQueryClient();
  const [selectedTopicFilter, setSelectedTopicFilter] = useState<string>('ALL');

  useEffect(() => {
    document.title = 'Student Overview | LearnPath';
  }, []);

  const { data: profile } = useQuery({
    queryKey: ['profile'],
    queryFn: async () => (await apiClient.get<StudentProfile>('/profile')).data,
    retry: false,
  });

  const { data: pathData, isLoading: isLoadingPath } = useQuery({
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
    queryFn: () => studentApi.getRecommendations({ strategy: 'hybrid', limit: 6 }),
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

  const toggleBookmarkMutation = useMutation({
    mutationFn: async ({
      resourceId,
      currentlySaved,
    }: {
      resourceId: string;
      currentlySaved: boolean;
    }) => {
      if (currentlySaved) {
        await studentApi.removeBookmark(resourceId);
      } else {
        await studentApi.saveBookmark(resourceId);
      }
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['bookmarks'] }),
        queryClient.invalidateQueries({ queryKey: ['recommendations'] }),
      ]);
    },
  });

  const nodes = pathData?.nodes ?? [];
  const totalTopics = Math.max(nodes.length, 1);
  const masteredCount = nodes.filter((n) => n.mastery_status === 'MASTERED').length;
  const manualCompletedCount = nodes.filter((n) => n.is_manually_completed).length;
  const nextTopic = nodes.find((n) => n.topic_id === pathData?.recommended_next_topic_id);
  const completedResourcesCount = history.filter((h) => h.status === 'COMPLETED').length;
  const overallPercent = Math.round((masteredCount / totalTopics) * 100);

  const bookmarkedIds = useMemo(
    () => new Set(bookmarks.map((b) => b.resource_id)),
    [bookmarks],
  );

  const allPicks = recPreview?.items ?? [];
  const topicPills = useMemo(() => {
    const map = new Map<string, string>();
    for (const item of allPicks) {
      map.set(item.topic_id, item.topic_name);
    }
    return Array.from(map.entries());
  }, [allPicks]);

  const visiblePicks = useMemo(() => {
    const filtered =
      selectedTopicFilter === 'ALL'
        ? allPicks
        : allPicks.filter((i) => i.topic_id === selectedTopicFilter);
    return filtered.slice(0, 3);
  }, [allPicks, selectedTopicFilter]);

  const gaugeData = useMemo(
    () => [
      { name: 'Mastered', value: Math.max(overallPercent, 0), color: '#14532d' },
      { name: 'Remaining', value: Math.max(100 - overallPercent, 0), color: '#dfeae3' },
    ],
    [overallPercent],
  );

  const activityBars = useMemo(() => {
    if (nodes.length > 0) {
      // Only show real exam scores; never-assessed topics render as 0 (no invented values)
      return nodes.map((n) => ({
        label: `T${n.display_order}`,
        topic: n.latest_score_percent === null ? `${n.name} (not assessed yet)` : n.name,
        score: n.latest_score_percent === null ? 0 : Math.round(n.latest_score_percent),
      }));
    }
    return [{ label: 'Start', topic: 'Placement', score: 0 }];
  }, [nodes]);

  const latestInProgressResource = useMemo(
    () => history.find((h) => h.status === 'OPENED') ?? history[0] ?? null,
    [history],
  );

  return (
    <AppLayout variant="sidebar" hidePageHeader customH1 pageTitle="Overview">
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main Left Column (2/3 width — Figma Screen 2) */}
        <div className="space-y-6 lg:col-span-2">
          <div>
            <h1
              id="main-heading"
              tabIndex={-1}
              className="text-2xl font-bold tracking-tight text-slate-900 outline-none sm:text-[26px]"
            >
              A little progress. A world of possibilities.
            </h1>
            <p className="mt-1 text-sm text-slate-600">
              Welcome back{profile?.display_name ? `, ${profile.display_name}` : ''}. Let&apos;s
              find what moves you forward.
            </p>
          </div>

          {/* Mint-Green Hero Banner with 1-2-3 Stepper Card */}
          <div className="grid items-center gap-5 rounded-2xl border border-[#cce0d3] bg-[#e6f2eb] p-6 sm:grid-cols-5">
            <div className="sm:col-span-3">
              <p className="text-[10px] font-bold uppercase tracking-widest text-[#14532d]">
                Made for your next step
              </p>
              <h3 className="mt-1 text-lg font-bold leading-snug text-slate-900 sm:text-xl">
                Your future in Python starts here.
              </h3>
              <p className="mt-1.5 text-xs leading-relaxed text-slate-600">
                {nextTopic
                  ? `Up next in your DAG curriculum: ${nextTopic.display_order}. ${nextTopic.name}.`
                  : 'Explore your prerequisite-aware Python roadmap and keep building momentum.'}
              </p>
              <div className="mt-4 flex flex-wrap items-center gap-2.5">
                <Link
                  to="/roadmap"
                  className="inline-flex min-h-9 items-center gap-1.5 rounded-lg bg-[#14532d] px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-[#0f3f22]"
                >
                  <span>View learning path</span>
                  <ArrowRight aria-hidden="true" className="h-3.5 w-3.5" />
                </Link>
                {attempts.length === 0 ? (
                  <Link
                    to="/assessment"
                    className="inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-[#14532d]/30 bg-white px-3.5 py-2 text-xs font-semibold text-[#14532d] hover:bg-[#f2f8f4]"
                  >
                    Take placement test
                  </Link>
                ) : null}
              </div>
            </div>

            <div className="rounded-xl border border-[#d4e5da] bg-white p-4 shadow-xs sm:col-span-2">
              <p className="text-[11px] font-semibold text-slate-500">Guided Learning Cycle</p>
              <ol className="mt-3 flex items-center justify-between text-[11px] font-semibold">
                <li className="flex flex-col items-center gap-1 text-[#14532d]">
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[#14532d] text-[10px] font-bold text-white">
                    1
                  </span>
                  <span>Learn</span>
                </li>
                <li aria-hidden="true" className="mb-4 h-0.5 flex-1 bg-[#b8d4c2]" />
                <li className="flex flex-col items-center gap-1 text-[#14532d]">
                  <span className="flex h-6 w-6 items-center justify-center rounded-full border-2 border-[#14532d] bg-[#e6f2eb] text-[10px] font-bold text-[#14532d]">
                    2
                  </span>
                  <span>Practice</span>
                </li>
                <li aria-hidden="true" className="mb-4 h-0.5 flex-1 bg-[#dce7e0]" />
                <li className="flex flex-col items-center gap-1 text-slate-500">
                  <span className="flex h-6 w-6 items-center justify-center rounded-full border border-slate-300 bg-slate-50 text-[10px] font-bold">
                    3
                  </span>
                  <span>Build</span>
                </li>
              </ol>
              <p className="mt-3 truncate border-t border-slate-100 pt-2 text-[11px] text-slate-600">
                Focus:{' '}
                <strong className="text-slate-900">
                  {nextTopic
                    ? nextTopic.name
                    : isLoadingPath && nodes.length === 0
                      ? 'Loading curriculum...'
                      : 'All Topics Mastered'}
                </strong>
              </p>
            </div>
          </div>

          {/* Picked for your potential (Topic Pills + Featured Strip + 3 Visual Cards) */}
          <section aria-labelledby="picked-heading" className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 id="picked-heading" className="text-base font-bold text-slate-900">
                Picked for your potential
              </h3>
              <Link
                to="/recommendations"
                className="inline-flex items-center gap-1 text-xs font-semibold text-[#14532d] hover:underline"
              >
                <span>Explore all recommendations</span>
                <ArrowRight aria-hidden="true" className="h-3.5 w-3.5" />
              </Link>
            </div>

            {topicPills.length > 0 ? (
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  aria-pressed={selectedTopicFilter === 'ALL'}
                  onClick={() => setSelectedTopicFilter('ALL')}
                  className={cn(
                    'rounded-full px-3 py-1 text-xs font-semibold transition-colors',
                    selectedTopicFilter === 'ALL'
                      ? 'bg-[#14532d] text-white'
                      : 'border border-slate-200 bg-white text-slate-600 hover:bg-[#edf5f0]',
                  )}
                >
                  All picks
                </button>
                {topicPills.map(([topicId, topicName]) => (
                  <button
                    key={topicId}
                    type="button"
                    aria-pressed={selectedTopicFilter === topicId}
                    onClick={() => setSelectedTopicFilter(topicId)}
                    className={cn(
                      'rounded-full px-3 py-1 text-xs font-semibold transition-colors',
                      selectedTopicFilter === topicId
                        ? 'bg-[#14532d] text-white'
                        : 'border border-slate-200 bg-white text-slate-600 hover:bg-[#edf5f0]',
                    )}
                  >
                    {topicName}
                  </button>
                ))}
              </div>
            ) : null}

            {/* Spotlight Topic Card */}
            {nextTopic ? (
              <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-[#d6e5dc] bg-[#f2f8f4] p-4">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <Badge tone="info">Priority Topic #{nextTopic.display_order}</Badge>
                    {nextTopic.latest_score_percent !== null ? (
                      <span className="text-xs font-semibold text-amber-800">
                        Score: {nextTopic.latest_score_percent.toFixed(0)}% (70% to master)
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-1.5 text-sm font-bold text-slate-900">{nextTopic.name}</p>
                  <p className="mt-0.5 line-clamp-1 text-xs text-slate-600">
                    {nextTopic.description}
                  </p>
                </div>
                <Link
                  to={`/recommendations?topicId=${nextTopic.topic_id}`}
                  className="inline-flex min-h-9 shrink-0 items-center gap-1.5 rounded-lg bg-[#14532d] px-3.5 py-2 text-xs font-semibold text-white hover:bg-[#0f3f22]"
                >
                  <span>Start topic</span>
                  <ArrowRight aria-hidden="true" className="h-3.5 w-3.5" />
                </Link>
              </div>
            ) : null}

            {/* 3-Column Visual Study Cards */}
            {visiblePicks.length > 0 ? (
              <div className="grid gap-4 sm:grid-cols-3">
                {visiblePicks.map((item, idx) => {
                  const isSaved = Boolean(item.is_bookmarked || bookmarkedIds.has(item.resource_id));
                  const bannerTone = BANNER_TONES[idx % BANNER_TONES.length];
                  return (
                    <article
                      key={item.resource_id}
                      className="flex flex-col justify-between overflow-hidden rounded-xl border border-[#dce6df] bg-white shadow-xs transition-shadow hover:shadow-sm"
                    >
                      <div>
                        <div
                          className={cn(
                            'relative flex h-24 items-end justify-between p-3',
                            bannerTone,
                          )}
                        >
                          <span className="inline-flex items-center gap-1 rounded-md bg-white/90 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-[#14532d]">
                            <FormatIcon type={item.content_type} className="h-3 w-3" />
                            {item.content_type}
                          </span>
                          <FormatIcon
                            type={item.content_type}
                            className="h-10 w-10 opacity-25"
                          />
                          <button
                            type="button"
                            aria-pressed={isSaved}
                            aria-label={
                              isSaved
                                ? `Remove ${item.title} from bookmarks`
                                : `Bookmark ${item.title}`
                            }
                            onClick={() =>
                              toggleBookmarkMutation.mutate({
                                resourceId: item.resource_id,
                                currentlySaved: isSaved,
                              })
                            }
                            className="absolute right-2.5 top-2.5 flex h-7 w-7 items-center justify-center rounded-full bg-white/90 text-slate-600 shadow-xs hover:text-[#14532d]"
                          >
                            <Bookmark
                              aria-hidden="true"
                              className={cn(
                                'h-3.5 w-3.5',
                                isSaved ? 'fill-[#14532d] text-[#14532d]' : '',
                              )}
                            />
                          </button>
                        </div>

                        <div className="p-3.5">
                          <p className="text-[11px] font-semibold text-[#14532d]">
                            {item.topic_name}
                          </p>
                          <h4 className="mt-0.5 line-clamp-2 text-sm font-bold leading-snug text-slate-900">
                            <InlineCodeText text={item.title} />
                          </h4>
                          <p className="mt-1.5 line-clamp-2 flex items-start gap-1 text-[11px] text-slate-600">
                            <Sparkles
                              aria-hidden="true"
                              className="mt-0.5 h-3 w-3 shrink-0 text-[#14532d]"
                            />
                            <span>
                              <InlineCodeText text={item.rationale} />
                            </span>
                          </p>
                        </div>
                      </div>

                      <div className="border-t border-slate-100 px-3.5 py-2.5">
                        <div className="flex items-center justify-between text-[11px] text-slate-500">
                          <span>
                            {item.estimated_minutes ? `${item.estimated_minutes} min · ` : ''}
                            {item.difficulty.charAt(0) + item.difficulty.slice(1).toLowerCase()}
                          </span>
                          <span className="inline-flex items-center gap-0.5 font-semibold text-amber-600">
                            <Star aria-hidden="true" className="h-3 w-3 fill-amber-400 text-amber-400" />
                            {item.my_rating ? `${item.my_rating}.0` : 'Top pick'}
                          </span>
                        </div>
                        <a
                          href={item.external_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          aria-label={`Open recommended resource ${item.title}`}
                          onClick={() => openResourceMutation.mutate(item.resource_id)}
                          className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-[#14532d] hover:underline"
                        >
                          <span>Open course</span>
                          <ExternalLink aria-hidden="true" className="h-3 w-3" />
                        </a>
                      </div>
                    </article>
                  );
                })}
              </div>
            ) : (
              <Card className="p-5 text-sm text-slate-600">
                Complete your placement diagnostic to unlock personalized study picks.
              </Card>
            )}
          </section>

          {/* Pick up where you left off (Bottom Resume Card — Figma Screen 2) */}
          <Card className="border-[#dce6df] p-5">
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-sm font-bold text-slate-900">Pick up where you left off</h3>
              <Link
                to="/bookmarks"
                className="text-xs font-semibold text-[#14532d] hover:underline"
              >
                My learning library
              </Link>
            </div>

            <div className="mt-3 flex flex-wrap items-center justify-between gap-4 rounded-xl border border-[#e3ece6] bg-[#f8fbf9] p-4">
              <div className="flex min-w-[220px] flex-1 items-center gap-3.5">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-[#e6f2eb] text-[#14532d]">
                  <GraduationCap aria-hidden="true" className="h-6 w-6" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-bold text-slate-900">
                    {latestInProgressResource
                      ? latestInProgressResource.title
                      : nextTopic
                        ? `${nextTopic.display_order}. ${nextTopic.name}`
                        : 'Python Curriculum Path'}
                  </p>
                  <p className="mt-0.5 text-xs text-slate-600">
                    {latestInProgressResource
                      ? `${latestInProgressResource.topic_name} · ${latestInProgressResource.status}`
                      : 'Dual curriculum tracking (Exam Verified + Self-Studied)'}
                  </p>
                  <div className="mt-2 max-w-xs">
                    <ProgressBar
                      label="Curriculum mastery"
                      value={masteredCount}
                      max={totalTopics}
                    />
                  </div>
                </div>
              </div>

              <Link
                to={
                  nextTopic
                    ? `/assessment?type=TOPIC_QUIZ&topicId=${nextTopic.topic_id}`
                    : '/roadmap'
                }
                className="inline-flex min-h-9 shrink-0 items-center gap-1.5 rounded-lg bg-[#14532d] px-4 py-2 text-xs font-semibold text-white hover:bg-[#0f3f22]"
              >
                <span>Resume learning</span>
                <ArrowRight aria-hidden="true" className="h-3.5 w-3.5" />
              </Link>
            </div>
          </Card>
        </div>

        {/* Right Rail (1/3 width — Progress Gauge, Activity Chart & Sand Callout) */}
        <aside aria-label="Progress and skill summary" className="space-y-5">
          {/* Progress Dashboard Card with Semi-Circular Gauge */}
          <Card className="border-[#dce6df] p-5">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-900">Progress dashboard</h3>
              <Badge tone="info">
                {isLoadingPath && nodes.length === 0 ? 'DAG' : `${nodes.length}-Topic DAG`}
              </Badge>
            </div>

            <div className="mt-3 grid grid-cols-3 gap-2 text-center">
              <div className="rounded-lg bg-[#f4f8f5] p-2">
                <p className="text-base font-bold text-[#14532d]">
                  {isLoadingPath && nodes.length === 0 ? '—' : `${masteredCount}/${nodes.length}`}
                </p>
                <p className="text-[10px] font-medium text-slate-500">Mastered</p>
              </div>
              <div className="rounded-lg bg-[#f4f8f5] p-2">
                <p className="text-base font-bold text-slate-900">{completedResourcesCount}</p>
                <p className="text-[10px] font-medium text-slate-500">Completed</p>
              </div>
              <div className="rounded-lg bg-[#f4f8f5] p-2">
                <p className="text-base font-bold text-slate-900">{bookmarks.length}</p>
                <p className="text-[10px] font-medium text-slate-500">Saved</p>
              </div>
            </div>

            <div className="mt-3">
              <ProgressBar
                label={`Self-studied checklist (${manualCompletedCount}/${nodes.length})`}
                value={manualCompletedCount}
                max={totalTopics}
              />
            </div>

            <figure className="mt-4 border-t border-slate-100 pt-3">
              <div className="relative mx-auto h-32 w-full max-w-[210px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={gaugeData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="82%"
                      startAngle={180}
                      endAngle={0}
                      innerRadius={56}
                      outerRadius={74}
                      stroke="none"
                    >
                      {gaugeData.map((entry) => (
                        <Cell key={entry.name} fill={entry.color} />
                      ))}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
                <div className="pointer-events-none absolute inset-x-0 bottom-3 text-center">
                  <p className="text-2xl font-extrabold text-[#14532d]">{overallPercent}%</p>
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                    Overall Progress
                  </p>
                </div>
              </div>
              <figcaption className="visually-hidden">
                Overall exam-verified curriculum progress is {overallPercent} percent ({masteredCount}{' '}
                of {nodes.length} topics mastered).
              </figcaption>
            </figure>
          </Card>

          {/* Learning Activity Card */}
          <Card className="border-[#dce6df] p-5">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-900">Learning activity</h3>
              <span className="text-[11px] font-medium text-slate-500">Topic scores</span>
            </div>

            <figure className="mt-3">
              <div className="h-32 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={activityBars}>
                    <XAxis
                      dataKey="label"
                      axisLine={false}
                      tickLine={false}
                      tick={{ fontSize: 10, fill: '#64748b' }}
                    />
                    <Tooltip
                      formatter={(val: number) => [`${val}%`, 'Mastery']}
                      labelFormatter={(_label, payload) =>
                        payload?.[0]?.payload?.topic ?? String(_label)
                      }
                    />
                    <Bar dataKey="score" fill="#14532d" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <figcaption className="visually-hidden">
                Bar chart of latest mastery percentage across Python topics.
              </figcaption>
            </figure>

            {attempts.length > 0 ? (
              <div className="mt-3 space-y-1.5 border-t border-slate-100 pt-3">
                <p className="text-[11px] font-semibold text-slate-600">Recent test reviews</p>
                {attempts.slice(0, 3).map((att) => (
                  <div
                    key={att.attempt_id}
                    className="flex items-center justify-between rounded-lg bg-[#f8faf9] px-2.5 py-1.5 text-xs"
                  >
                    <span className="font-medium text-slate-700">
                      {att.test_type === 'DIAGNOSTIC' ? 'Placement Test' : 'Topic Quiz'} ·{' '}
                      <strong>{att.overall_score_percent.toFixed(0)}%</strong>
                    </span>
                    <Link
                      to={`/assessment/attempts/${att.attempt_id}`}
                      aria-label={`Review solutions for ${att.test_type} scored ${att.overall_score_percent.toFixed(1)}%`}
                      className="font-semibold text-[#14532d] hover:underline"
                    >
                      Review
                    </Link>
                  </div>
                ))}
              </div>
            ) : null}
          </Card>

          {/* Warm Sand Skill Check Card (Figma Screen 2 Bottom-Right) */}
          <div className="rounded-2xl border border-[#e5dbcb] bg-[#f5efe6] p-5">
            <p className="text-[10px] font-bold uppercase tracking-widest text-amber-900">
              Grow your skill set
            </p>
            <h3 className="mt-1 text-base font-bold leading-snug text-slate-900">
              Make your next move a confident one.
            </h3>
            <p className="mt-1.5 text-xs leading-relaxed text-slate-700">
              Take a quick diagnostic or topic quiz to verify your Python mastery and unlock new
              modules.
            </p>
            <Link
              to="/assessment"
              className="mt-3.5 inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-amber-900/25 bg-white px-3.5 py-1.5 text-xs font-semibold text-slate-900 shadow-2xs hover:bg-amber-50/50"
            >
              <span>Check my skills</span>
              <ArrowRight aria-hidden="true" className="h-3.5 w-3.5" />
            </Link>
          </div>
        </aside>
      </div>
    </AppLayout>
  );
}
