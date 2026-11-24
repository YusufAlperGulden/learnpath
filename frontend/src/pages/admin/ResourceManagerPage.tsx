import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Code2,
  ExternalLink,
  FileText,
  GitBranch,
  Layers,
  Pencil,
  PlayCircle,
  Plus,
  RotateCcw,
  Search,
  Trash2,
} from 'lucide-react';
import { adminApi, extractApiErrorMessage } from '../../api/admin';
import { AppLayout } from '../../components/layout/AppLayout';
import { Badge, Button, Card, Modal, ResponsiveTable, cn } from '../../components/ui';
import type {
  ContentType,
  DifficultyLevel,
  ResourceAdminRead,
  SupportedLanguage,
} from '../../types/api';

type StatusFilter = 'ALL' | 'ACTIVE' | 'INACTIVE';

interface ResourceFormState {
  topic_id: string;
  title: string;
  description: string;
  external_url: string;
  content_type: ContentType;
  difficulty: DifficultyLevel;
  language: SupportedLanguage;
  estimated_minutes: string;
}

const EMPTY_FORM: ResourceFormState = {
  topic_id: '',
  title: '',
  description: '',
  external_url: '',
  content_type: 'VIDEO',
  difficulty: 'BEGINNER',
  language: 'en',
  estimated_minutes: '20',
};

const PAGE_SIZE = 8;

function FormatIcon({ type }: { type: ContentType }) {
  if (type === 'VIDEO') return <PlayCircle aria-hidden="true" className="h-4 w-4" />;
  if (type === 'EXERCISE') return <Code2 aria-hidden="true" className="h-4 w-4" />;
  return <FileText aria-hidden="true" className="h-4 w-4" />;
}

export function ResourceManagerPage() {
  const queryClient = useQueryClient();

  const [searchQuery, setSearchQuery] = useState('');
  const [topicFilter, setTopicFilter] = useState('');
  const [formatFilter, setFormatFilter] = useState<ContentType | ''>('');
  const [difficultyFilter, setDifficultyFilter] = useState<DifficultyLevel | ''>('');
  const [languageFilter, setLanguageFilter] = useState<SupportedLanguage | ''>('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('ALL');
  const [currentPage, setCurrentPage] = useState(1);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingResource, setEditingResource] = useState<ResourceAdminRead | null>(null);
  const [formState, setFormState] = useState<ResourceFormState>(EMPTY_FORM);
  const [formError, setFormError] = useState<string | null>(null);
  const [duplicateResourceId, setDuplicateResourceId] = useState<string | null>(null);
  const [pendingToggleId, setPendingToggleId] = useState<string | null>(null);

  useEffect(() => {
    document.title = 'Learning Resource Management | LearnPath Admin';
  }, []);

  const { data: topics = [] } = useQuery({
    queryKey: ['admin', 'topics'],
    queryFn: adminApi.listTopics,
  });

  const apiFilters = useMemo(
    () => ({
      topic_id: topicFilter || undefined,
      content_type: formatFilter || undefined,
      difficulty: difficultyFilter || undefined,
      language: languageFilter || undefined,
      is_active:
        statusFilter === 'ALL' ? undefined : statusFilter === 'ACTIVE' ? true : false,
      search: searchQuery.trim() || undefined,
    }),
    [topicFilter, formatFilter, difficultyFilter, languageFilter, statusFilter, searchQuery],
  );

  useEffect(() => {
    setCurrentPage(1);
  }, [apiFilters]);

  const { data: resources = [], isLoading } = useQuery({
    queryKey: ['admin', 'resources', apiFilters],
    queryFn: () => adminApi.listResources(apiFilters),
  });

  const activeCount = useMemo(
    () => resources.filter((r) => r.is_active).length,
    [resources],
  );

  const formatVarietyCount = useMemo(() => {
    const distinct = new Set(resources.map((r) => r.content_type));
    return distinct.size || 3;
  }, [resources]);

  const totalPages = Math.max(Math.ceil(resources.length / PAGE_SIZE), 1);
  const safePage = Math.min(currentPage, totalPages);
  const paginatedResources = useMemo(() => {
    const start = (safePage - 1) * PAGE_SIZE;
    return resources.slice(start, start + PAGE_SIZE);
  }, [resources, safePage]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      const parsedMinutes = formState.estimated_minutes.trim()
        ? Number.parseInt(formState.estimated_minutes.trim(), 10)
        : null;

      if (parsedMinutes !== null && (Number.isNaN(parsedMinutes) || parsedMinutes <= 0)) {
        throw new Error('Estimated minutes must be a positive integer or left blank.');
      }

      const payload = {
        topic_id: formState.topic_id,
        title: formState.title.trim(),
        description: formState.description.trim(),
        external_url: formState.external_url.trim(),
        content_type: formState.content_type,
        difficulty: formState.difficulty,
        language: formState.language,
        estimated_minutes: parsedMinutes,
      };

      if (editingResource) {
        return adminApi.updateResource(editingResource.resource_id, payload);
      }
      return adminApi.createResource(payload);
    },
    onSuccess: async () => {
      setIsModalOpen(false);
      setEditingResource(null);
      setFormError(null);
      setDuplicateResourceId(null);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['admin', 'resources'] }),
        queryClient.invalidateQueries({ queryKey: ['admin', 'topics'] }),
      ]);
    },
    onError: (err: unknown) => {
      if (err instanceof Error && !('response' in err)) {
        setDuplicateResourceId(null);
        setFormError(err.message);
        return;
      }
      const msg = extractApiErrorMessage(
        err,
        'Could not save resource. Check URL format and mandatory TF-IDF description.',
      );
      const idMatch = msg.match(/resource_id=([0-9a-f-]{36})/i);
      setDuplicateResourceId(idMatch ? idMatch[1] : null);
      setFormError(msg);
    },
  });

  const toggleStatusMutation = useMutation({
    mutationFn: async ({ resourceId, nextActive }: { resourceId: string; nextActive: boolean }) => {
      setPendingToggleId(resourceId);
      return adminApi.setResourceActive(resourceId, nextActive);
    },
    onSettled: async () => {
      setPendingToggleId(null);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['admin', 'resources'] }),
        queryClient.invalidateQueries({ queryKey: ['admin', 'topics'] }),
      ]);
    },
  });

  const openCreateModal = () => {
    setEditingResource(null);
    setFormError(null);
    setDuplicateResourceId(null);
    setFormState({
      ...EMPTY_FORM,
      topic_id: topicFilter || topics[0]?.topic_id || '',
    });
    setIsModalOpen(true);
  };

  const openEditModal = (res: ResourceAdminRead) => {
    setEditingResource(res);
    setFormError(null);
    setDuplicateResourceId(null);
    setFormState({
      topic_id: res.topic_id,
      title: res.title,
      description: res.description,
      external_url: res.external_url,
      content_type: res.content_type,
      difficulty: res.difficulty,
      language: res.language,
      estimated_minutes: res.estimated_minutes !== null ? String(res.estimated_minutes) : '',
    });
    setIsModalOpen(true);
  };

  const handleFormSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!formState.topic_id) {
      setFormError('Select a curriculum topic before saving.');
      return;
    }
    if (formState.description.trim().length < 10) {
      setFormError('Description must be at least 10 characters to feed TF-IDF indexing.');
      return;
    }
    setFormError(null);
    saveMutation.mutate();
  };

  const startIdx = resources.length === 0 ? 0 : (safePage - 1) * PAGE_SIZE + 1;
  const endIdx = Math.min(safePage * PAGE_SIZE, resources.length);

  return (
    <AppLayout
      variant="sidebar"
      eyebrow="Content Library"
      pageTitle="Learning Resource Management"
      pageSubtitle="Manage TF-IDF indexed Python resources with duplicate-URL detection and FK-safe soft deactivation."
      headerActions={
        <>
          <Button onClick={openCreateModal} disabled={topics.length === 0}>
            <Plus aria-hidden="true" className="h-4 w-4" />
            <span>Add New Resource</span>
          </Button>
          <Link
            to="/admin/topics-questions?tab=questions&new=1"
            className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-[#14532d] px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-[#0f3f22]"
          >
            <Plus aria-hidden="true" className="h-4 w-4" />
            <span>Add Test Question</span>
          </Link>
        </>
      }
    >
      {/* 3 KPI Summary Cards (Figma Screen 7) */}
      <div className="mb-6 grid gap-4 sm:grid-cols-3">
        <Card className="flex items-center gap-3.5 rounded-2xl border-[#dce6df] p-5">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#e6f2eb] text-[#14532d]">
            <BookOpen aria-hidden="true" className="h-5 w-5" />
          </div>
          <div>
            <p className="text-2xl font-extrabold text-slate-900">{activeCount}</p>
            <p className="text-xs font-medium text-slate-500">
              Published resources ({resources.length - activeCount} inactive)
            </p>
          </div>
        </Card>

        <Card className="flex items-center gap-3.5 rounded-2xl border-[#dce6df] p-5">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#e6f2eb] text-[#14532d]">
            <GitBranch aria-hidden="true" className="h-5 w-5" />
          </div>
          <div>
            <p className="text-2xl font-extrabold text-slate-900">{topics.length}</p>
            <p className="text-xs font-medium text-slate-500">Python curriculum topics</p>
          </div>
        </Card>

        <Card className="flex items-center gap-3.5 rounded-2xl border-[#dce6df] p-5">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#e6f2eb] text-[#14532d]">
            <Layers aria-hidden="true" className="h-5 w-5" />
          </div>
          <div>
            <p className="text-2xl font-extrabold text-slate-900">{formatVarietyCount}</p>
            <p className="text-xs font-medium text-slate-500">
              Resource formats (Video · Article · Exercise)
            </p>
          </div>
        </Card>
      </div>

      {/* Unified Resource Library Card (Figma Screen 7) */}
      <Card className="overflow-hidden rounded-2xl border-[#dce6df] p-0">
        {/* Search & Secondary Filters Header */}
        <div className="border-b border-[#e5ede8] p-5">
          <search>
            <form
              method="get"
              action="/admin/resources"
              onSubmit={(e) => e.preventDefault()}
              className="flex flex-wrap items-center justify-between gap-3"
            >
              <h2 className="text-base font-bold text-slate-900">Resource library</h2>

              <div className="flex flex-wrap items-center gap-2.5">
                <div className="relative">
                  <label htmlFor="res-search" className="visually-hidden">
                    Search title, TF-IDF description, or URL
                  </label>
                  <Search
                    aria-hidden="true"
                    className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400"
                  />
                  <input
                    id="res-search"
                    name="search"
                    type="search"
                    spellCheck={false}
                    autoCorrect="off"
                    autoCapitalize="none"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search resources..."
                    className="h-9 w-56 rounded-lg border border-slate-300 bg-[#f8faf9] pl-8 pr-3 text-xs text-slate-900 focus:bg-white"
                  />
                </div>

                <div>
                  <label htmlFor="res-format-filter" className="visually-hidden">
                    Format
                  </label>
                  <select
                    id="res-format-filter"
                    name="content_type"
                    value={formatFilter}
                    onChange={(e) => setFormatFilter(e.target.value as ContentType | '')}
                    className="h-9 rounded-lg border border-slate-300 bg-white px-2.5 text-xs font-medium text-slate-800"
                  >
                    <option value="">All formats</option>
                    <option value="VIDEO">Video</option>
                    <option value="ARTICLE">Article</option>
                    <option value="EXERCISE">Exercise</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="res-difficulty-filter" className="visually-hidden">
                    Difficulty
                  </label>
                  <select
                    id="res-difficulty-filter"
                    name="difficulty"
                    value={difficultyFilter}
                    onChange={(e) => setDifficultyFilter(e.target.value as DifficultyLevel | '')}
                    className="h-9 rounded-lg border border-slate-300 bg-white px-2.5 text-xs font-medium text-slate-800"
                  >
                    <option value="">All levels</option>
                    <option value="BEGINNER">Beginner</option>
                    <option value="INTERMEDIATE">Intermediate</option>
                    <option value="ADVANCED">Advanced</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="res-lang-filter" className="visually-hidden">
                    Language
                  </label>
                  <select
                    id="res-lang-filter"
                    name="language"
                    value={languageFilter}
                    onChange={(e) => setLanguageFilter(e.target.value as SupportedLanguage | '')}
                    className="h-9 rounded-lg border border-slate-300 bg-white px-2.5 text-xs font-medium text-slate-800"
                  >
                    <option value="">All langs</option>
                    <option value="en">EN</option>
                    <option value="tr">TR</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="res-status-filter" className="visually-hidden">
                    Status
                  </label>
                  <select
                    id="res-status-filter"
                    name="status"
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
                    className="h-9 rounded-lg border border-slate-300 bg-white px-2.5 text-xs font-medium text-slate-800"
                  >
                    <option value="ALL">All status</option>
                    <option value="ACTIVE">Active</option>
                    <option value="INACTIVE">Inactive</option>
                  </select>
                </div>
              </div>
            </form>
          </search>

          {/* Single-Row Horizontal Scrolling Topic Filter Pills (Figma Screen 7) */}
          <div
            role="group"
            aria-label="Filter resources by Python topic"
            className="lp-tab-scroller mt-4 gap-2 pb-1"
          >
            <button
              type="button"
              aria-pressed={topicFilter === ''}
              onClick={() => setTopicFilter('')}
              className={cn(
                'flex-none rounded-full px-3.5 py-1.5 text-xs font-semibold transition-colors',
                topicFilter === ''
                  ? 'bg-[#e6f2eb] text-[#14532d] ring-1 ring-[#9dc4ac]'
                  : 'bg-slate-100 text-slate-600 hover:bg-[#f1f6f3] hover:text-slate-900',
              )}
            >
              All Topics
            </button>
            {topics.map((t) => (
              <button
                key={t.topic_id}
                type="button"
                aria-pressed={topicFilter === t.topic_id}
                onClick={(e) => {
                  setTopicFilter(t.topic_id);
                  e.currentTarget.scrollIntoView({ block: 'nearest', inline: 'nearest' });
                }}
                className={cn(
                  'flex-none rounded-full px-3.5 py-1.5 text-xs font-semibold transition-colors',
                  topicFilter === t.topic_id
                    ? 'bg-[#e6f2eb] text-[#14532d] ring-1 ring-[#9dc4ac]'
                    : 'bg-slate-100 text-slate-600 hover:bg-[#f1f6f3] hover:text-slate-900',
                )}
              >
                {t.name}
              </button>
            ))}
          </div>
        </div>

        {/* Resource Table */}
        {isLoading ? (
          <div className="p-10 text-center text-sm text-slate-600">Loading resource catalog...</div>
        ) : resources.length === 0 ? (
          <div className="p-10 text-center text-sm text-slate-600">
            No resources match the selected filters.
          </div>
        ) : (
          <>
            <ResponsiveTable
              caption="Python learning resource catalog"
              headers={['Title', 'Type', 'Difficulty', 'Topic', 'URL / Status', 'Actions']}
              className="rounded-none border-0 shadow-none"
            >
              {paginatedResources.map((res) => (
                <tr
                  key={res.resource_id}
                  className={!res.is_active ? 'bg-slate-50/80 opacity-80' : undefined}
                >
                  <th scope="row" className="max-w-md px-5 py-3.5 align-top font-normal">
                    <div className="flex items-start gap-3">
                      <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#e8f3ec] text-[#14532d]">
                        <FormatIcon type={res.content_type} />
                      </span>
                      <div className="min-w-0">
                        <div className="font-semibold text-slate-900">{res.title}</div>
                        <p className="mt-0.5 line-clamp-1 text-xs text-slate-500">
                          {res.description}
                        </p>
                      </div>
                    </div>
                  </th>

                  <td className="px-4 py-3.5 align-middle">
                    <Badge tone="neutral">{res.content_type}</Badge>
                  </td>

                  <td className="px-4 py-3.5 align-middle">
                    <Badge
                      tone={
                        res.difficulty === 'BEGINNER'
                          ? 'success'
                          : res.difficulty === 'INTERMEDIATE'
                            ? 'info'
                            : 'warning'
                      }
                    >
                      {res.difficulty.charAt(0) + res.difficulty.slice(1).toLowerCase()}
                    </Badge>
                  </td>

                  <td className="px-4 py-3.5 align-middle text-xs font-medium text-slate-700">
                    {res.topic_name ?? 'Topic'}
                  </td>

                  <td className="px-4 py-3.5 align-middle">
                    <div className="flex flex-col gap-1">
                      <a
                        href={res.external_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        aria-label={`Open external URL for ${res.title}`}
                        className="inline-flex items-center gap-1 text-xs font-medium text-[#14532d] hover:underline"
                      >
                        <span className="max-w-[190px] truncate">{res.external_url}</span>
                        <ExternalLink aria-hidden="true" className="h-3 w-3 shrink-0" />
                      </a>
                      <span className="text-[11px] text-slate-500">
                        {res.language.toUpperCase()}
                        {res.estimated_minutes ? ` · ${res.estimated_minutes}m` : ''} ·{' '}
                        <strong className={res.is_active ? 'text-[#14532d]' : 'text-amber-700'}>
                          {res.is_active ? 'Active' : 'Inactive'}
                        </strong>
                      </span>
                    </div>
                  </td>

                  <td className="px-4 py-3.5 align-middle">
                    <div className="flex items-center gap-1.5">
                      <button
                        type="button"
                        aria-label={`Edit ${res.title}`}
                        onClick={() => openEditModal(res)}
                        className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 hover:border-[#14532d]/40 hover:bg-[#f2f7f4] hover:text-[#14532d]"
                      >
                        <Pencil aria-hidden="true" className="h-3.5 w-3.5" />
                      </button>

                      <button
                        type="button"
                        disabled={pendingToggleId === res.resource_id}
                        aria-label={`${res.is_active ? 'Deactivate' : 'Reactivate'} ${res.title}`}
                        onClick={() =>
                          toggleStatusMutation.mutate({
                            resourceId: res.resource_id,
                            nextActive: !res.is_active,
                          })
                        }
                        className={cn(
                          'inline-flex h-8 w-8 items-center justify-center rounded-lg border transition-colors',
                          res.is_active
                            ? 'border-slate-200 bg-white text-red-600 hover:border-red-200 hover:bg-red-50'
                            : 'border-[#9dc4ac] bg-[#e6f2eb] text-[#14532d] hover:bg-[#d5e8dd]',
                        )}
                      >
                        {res.is_active ? (
                          <Trash2 aria-hidden="true" className="h-3.5 w-3.5" />
                        ) : (
                          <RotateCcw aria-hidden="true" className="h-3.5 w-3.5" />
                        )}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </ResponsiveTable>

            {/* Pagination Footer (Figma Screen 7) */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[#e5ede8] px-5 py-3.5 text-xs text-slate-600">
              <span>
                Showing <strong className="text-slate-900">{startIdx}</strong>–
                <strong className="text-slate-900">{endIdx}</strong> of{' '}
                <strong className="text-slate-900">{resources.length}</strong> resources
              </span>

              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={safePage <= 1}
                  onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
                >
                  <ArrowLeft aria-hidden="true" className="h-3.5 w-3.5" />
                  <span>Previous</span>
                </Button>
                <span className="px-2 font-semibold text-slate-700">
                  Page {safePage} of {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={safePage >= totalPages}
                  onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
                >
                  <span>Next</span>
                  <ArrowRight aria-hidden="true" className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
          </>
        )}
      </Card>

      <Modal
        open={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingResource ? 'Edit Learning Resource' : 'Add Learning Resource'}
        description="Descriptions power Scikit-learn TF-IDF content-based filtering and recommendation card summaries."
        className="max-w-2xl"
      >
        <form
          method="post"
          action="/api/v1/admin/resources"
          onSubmit={handleFormSubmit}
          className="space-y-4"
        >
          {formError ? (
            <div
              role="alert"
              className="space-y-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
            >
              <p>{formError}</p>
              {duplicateResourceId ? (
                <button
                  type="button"
                  onClick={async () => {
                    const localMatch = resources.find((r) => r.resource_id === duplicateResourceId);
                    if (localMatch) {
                      setDuplicateResourceId(null);
                      openEditModal(localMatch);
                      return;
                    }
                    const allMatches = await adminApi.listResources({
                      search: formState.external_url.trim(),
                    });
                    const found = allMatches.find((r) => r.resource_id === duplicateResourceId);
                    if (found) {
                      setDuplicateResourceId(null);
                      openEditModal(found);
                    }
                  }}
                  className="inline-flex items-center gap-1 font-semibold text-[#14532d] underline hover:text-[#0f3f22]"
                >
                  Edit existing resource instead &rarr;
                </button>
              ) : null}
            </div>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-1">
              <label htmlFor="modal-res-topic" className="text-sm font-semibold text-slate-900">
                Curriculum topic <span aria-hidden="true">*</span>
              </label>
              <select
                id="modal-res-topic"
                name="topic_id"
                required
                value={formState.topic_id}
                onChange={(e) => setFormState((s) => ({ ...s, topic_id: e.target.value }))}
                className="min-h-11 rounded-lg border border-slate-400 bg-white px-3 py-2 text-sm text-slate-900"
              >
                {topics.map((t) => (
                  <option key={t.topic_id} value={t.topic_id}>
                    {t.display_order}. {t.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <label htmlFor="modal-res-minutes" className="text-sm font-semibold text-slate-900">
                Estimated duration (minutes)
              </label>
              <input
                id="modal-res-minutes"
                name="estimated_minutes"
                type="text"
                inputMode="numeric"
                value={formState.estimated_minutes}
                onChange={(e) => setFormState((s) => ({ ...s, estimated_minutes: e.target.value }))}
                placeholder="e.g. 20"
                className="min-h-11 rounded-lg border border-slate-400 px-3 py-2 text-sm text-slate-900"
              />
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <label htmlFor="modal-res-title" className="text-sm font-semibold text-slate-900">
              Resource title <span aria-hidden="true">*</span>
            </label>
            <input
              id="modal-res-title"
              name="title"
              type="text"
              required
              minLength={3}
              maxLength={255}
              value={formState.title}
              onChange={(e) => setFormState((s) => ({ ...s, title: e.target.value }))}
              className="min-h-11 rounded-lg border border-slate-400 px-3 py-2 text-sm text-slate-900"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label htmlFor="modal-res-url" className="text-sm font-semibold text-slate-900">
              External URL (unique) <span aria-hidden="true">*</span>
            </label>
            <input
              id="modal-res-url"
              name="external_url"
              type="url"
              required
              spellCheck={false}
              autoCorrect="off"
              autoCapitalize="none"
              value={formState.external_url}
              onChange={(e) => setFormState((s) => ({ ...s, external_url: e.target.value }))}
              placeholder="https://docs.python.org/3/tutorial/..."
              className="min-h-11 rounded-lg border border-slate-400 px-3 py-2 text-sm text-slate-900"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label htmlFor="modal-res-desc" className="text-sm font-semibold text-slate-900">
              TF-IDF summary &amp; pedagogical description <span aria-hidden="true">*</span>
            </label>
            <span id="modal-res-desc-hint" className="text-xs text-slate-600">
              Minimum 10 characters ({formState.description.trim().length} entered). Include key
              Python concepts covered by this resource.
            </span>
            <textarea
              id="modal-res-desc"
              name="description"
              required
              minLength={10}
              rows={3}
              aria-describedby="modal-res-desc-hint"
              value={formState.description}
              onChange={(e) => setFormState((s) => ({ ...s, description: e.target.value }))}
              className="rounded-lg border border-slate-400 px-3 py-2 text-sm text-slate-900"
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <div className="flex flex-col gap-1">
              <label htmlFor="modal-res-format" className="text-sm font-semibold text-slate-900">
                Format <span aria-hidden="true">*</span>
              </label>
              <select
                id="modal-res-format"
                name="content_type"
                value={formState.content_type}
                onChange={(e) =>
                  setFormState((s) => ({ ...s, content_type: e.target.value as ContentType }))
                }
                className="min-h-11 rounded-lg border border-slate-400 bg-white px-3 py-2 text-sm text-slate-900"
              >
                <option value="VIDEO">VIDEO</option>
                <option value="ARTICLE">ARTICLE</option>
                <option value="EXERCISE">EXERCISE</option>
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <label htmlFor="modal-res-diff" className="text-sm font-semibold text-slate-900">
                Difficulty <span aria-hidden="true">*</span>
              </label>
              <select
                id="modal-res-diff"
                name="difficulty"
                value={formState.difficulty}
                onChange={(e) =>
                  setFormState((s) => ({ ...s, difficulty: e.target.value as DifficultyLevel }))
                }
                className="min-h-11 rounded-lg border border-slate-400 bg-white px-3 py-2 text-sm text-slate-900"
              >
                <option value="BEGINNER">BEGINNER</option>
                <option value="INTERMEDIATE">INTERMEDIATE</option>
                <option value="ADVANCED">ADVANCED</option>
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <label htmlFor="modal-res-lang" className="text-sm font-semibold text-slate-900">
                Language <span aria-hidden="true">*</span>
              </label>
              <select
                id="modal-res-lang"
                name="language"
                value={formState.language}
                onChange={(e) =>
                  setFormState((s) => ({ ...s, language: e.target.value as SupportedLanguage }))
                }
                className="min-h-11 rounded-lg border border-slate-400 bg-white px-3 py-2 text-sm text-slate-900"
              >
                <option value="en">English (en)</option>
                <option value="tr">Turkish (tr)</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-3 border-t border-slate-100 pt-4">
            <Button variant="outline" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={saveMutation.isPending}>
              {editingResource ? 'Save changes' : 'Create resource'}
            </Button>
          </div>
        </form>
      </Modal>
    </AppLayout>
  );
}
