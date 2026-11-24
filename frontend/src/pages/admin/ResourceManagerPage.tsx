import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ExternalLink, Pencil, Plus, Power, RotateCcw } from 'lucide-react';
import { adminApi, extractApiErrorMessage } from '../../api/admin';
import { AppLayout } from '../../components/layout/AppLayout';
import { Badge, Button, Card, Modal, ResponsiveTable } from '../../components/ui';
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

export function ResourceManagerPage() {
  const queryClient = useQueryClient();

  const [searchQuery, setSearchQuery] = useState('');
  const [topicFilter, setTopicFilter] = useState('');
  const [formatFilter, setFormatFilter] = useState<ContentType | ''>('');
  const [difficultyFilter, setDifficultyFilter] = useState<DifficultyLevel | ''>('');
  const [languageFilter, setLanguageFilter] = useState<SupportedLanguage | ''>('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('ALL');

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingResource, setEditingResource] = useState<ResourceAdminRead | null>(null);
  const [formState, setFormState] = useState<ResourceFormState>(EMPTY_FORM);
  const [formError, setFormError] = useState<string | null>(null);
  const [duplicateResourceId, setDuplicateResourceId] = useState<string | null>(null);
  const [pendingToggleId, setPendingToggleId] = useState<string | null>(null);

  useEffect(() => {
    document.title = 'Admin Resource Catalog | LearnPath';
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

  const { data: resources = [], isLoading } = useQuery({
    queryKey: ['admin', 'resources', apiFilters],
    queryFn: () => adminApi.listResources(apiFilters),
  });

  const activeCount = useMemo(
    () => resources.filter((r) => r.is_active).length,
    [resources],
  );

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
    setFormState({
      ...EMPTY_FORM,
      topic_id: topics[0]?.topic_id ?? '',
    });
    setIsModalOpen(true);
  };

  const openEditModal = (res: ResourceAdminRead) => {
    setEditingResource(res);
    setFormError(null);
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

  return (
    <AppLayout
      pageTitle="Admin Resource Catalog"
      pageSubtitle="Manage TF-IDF indexed learning resources with duplicate-URL detection and FK-safe soft deactivation (FR10)."
    >
      <div className="mb-6 grid gap-4 sm:grid-cols-4">
        <Card className="p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Matching Resources
          </p>
          <p className="mt-1 text-2xl font-bold text-slate-900">{resources.length}</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Active in Recommender
          </p>
          <p className="mt-1 text-2xl font-bold text-emerald-700">{activeCount}</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Soft-Deactivated
          </p>
          <p className="mt-1 text-2xl font-bold text-amber-700">
            {resources.length - activeCount}
          </p>
        </Card>
        <Card className="flex items-center justify-between p-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Curriculum Topics
            </p>
            <p className="mt-1 text-2xl font-bold text-slate-900">{topics.length}</p>
          </div>
          <Button onClick={openCreateModal} disabled={topics.length === 0}>
            <Plus aria-hidden="true" className="h-4 w-4" />
            Add Resource
          </Button>
        </Card>
      </div>

      <Card className="mb-6 p-4">
        <search>
          <form
            method="get"
            action="/admin/resources"
            onSubmit={(e) => e.preventDefault()}
            className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6"
          >
            <div className="flex flex-col gap-1 lg:col-span-2">
              <label htmlFor="res-search" className="text-xs font-semibold text-slate-700">
                Search title, TF-IDF description, or URL
              </label>
              <input
                id="res-search"
                name="search"
                type="search"
                spellCheck={false}
                autoCorrect="off"
                autoCapitalize="none"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="e.g. comprehensions, itertools..."
                className="min-h-10 rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-900"
              />
            </div>

            <div className="flex flex-col gap-1">
              <label htmlFor="res-topic-filter" className="text-xs font-semibold text-slate-700">
                Topic
              </label>
              <select
                id="res-topic-filter"
                name="topic_id"
                value={topicFilter}
                onChange={(e) => setTopicFilter(e.target.value)}
                className="min-h-10 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900"
              >
                <option value="">All topics</option>
                {topics.map((t) => (
                  <option key={t.topic_id} value={t.topic_id}>
                    {t.display_order}. {t.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <label htmlFor="res-format-filter" className="text-xs font-semibold text-slate-700">
                Format
              </label>
              <select
                id="res-format-filter"
                name="content_type"
                value={formatFilter}
                onChange={(e) => setFormatFilter(e.target.value as ContentType | '')}
                className="min-h-10 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900"
              >
                <option value="">All formats</option>
                <option value="VIDEO">VIDEO</option>
                <option value="ARTICLE">ARTICLE</option>
                <option value="EXERCISE">EXERCISE</option>
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <label
                htmlFor="res-difficulty-filter"
                className="text-xs font-semibold text-slate-700"
              >
                Difficulty
              </label>
              <select
                id="res-difficulty-filter"
                name="difficulty"
                value={difficultyFilter}
                onChange={(e) => setDifficultyFilter(e.target.value as DifficultyLevel | '')}
                className="min-h-10 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900"
              >
                <option value="">All levels</option>
                <option value="BEGINNER">BEGINNER</option>
                <option value="INTERMEDIATE">INTERMEDIATE</option>
                <option value="ADVANCED">ADVANCED</option>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="flex flex-col gap-1">
                <label htmlFor="res-lang-filter" className="text-xs font-semibold text-slate-700">
                  Lang
                </label>
                <select
                  id="res-lang-filter"
                  name="language"
                  value={languageFilter}
                  onChange={(e) => setLanguageFilter(e.target.value as SupportedLanguage | '')}
                  className="min-h-10 rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm text-slate-900"
                >
                  <option value="">All</option>
                  <option value="en">en</option>
                  <option value="tr">tr</option>
                </select>
              </div>
              <div className="flex flex-col gap-1">
                <label htmlFor="res-status-filter" className="text-xs font-semibold text-slate-700">
                  Status
                </label>
                <select
                  id="res-status-filter"
                  name="status"
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
                  className="min-h-10 rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm text-slate-900"
                >
                  <option value="ALL">All</option>
                  <option value="ACTIVE">Active</option>
                  <option value="INACTIVE">Inactive</option>
                </select>
              </div>
            </div>
          </form>
        </search>
      </Card>

      {isLoading ? (
        <Card className="p-8 text-center text-sm text-slate-600">Loading resource catalog...</Card>
      ) : resources.length === 0 ? (
        <Card className="p-8 text-center text-sm text-slate-600">
          No resources match the selected filters.
        </Card>
      ) : (
        <ResponsiveTable
          caption="Python learning resource catalog"
          headers={['Resource & TF-IDF Description', 'Topic', 'Format & Level', 'Lang / Time', 'Status', 'Actions']}
        >
          {resources.map((res) => (
            <tr key={res.resource_id} className={!res.is_active ? 'bg-slate-50/70' : undefined}>
              <th scope="row" className="max-w-md px-4 py-3.5 align-top font-normal">
                <div className="font-semibold text-slate-900">{res.title}</div>
                <p className="mt-1 line-clamp-2 text-xs text-slate-600">{res.description}</p>
                <a
                  href={res.external_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={`Open external URL for ${res.title}`}
                  className="mt-1.5 inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:underline"
                >
                  <span className="max-w-[260px] truncate">{res.external_url}</span>
                  <ExternalLink aria-hidden="true" className="h-3 w-3 shrink-0" />
                </a>
              </th>
              <td className="px-4 py-3.5 align-top text-slate-800">
                <Badge tone="info">{res.topic_name ?? 'Topic'}</Badge>
              </td>
              <td className="px-4 py-3.5 align-top">
                <div className="flex flex-wrap gap-1.5">
                  <Badge tone="neutral">{res.content_type}</Badge>
                  <Badge
                    tone={
                      res.difficulty === 'BEGINNER'
                        ? 'success'
                        : res.difficulty === 'INTERMEDIATE'
                          ? 'info'
                          : 'warning'
                    }
                  >
                    {res.difficulty}
                  </Badge>
                </div>
              </td>
              <td className="px-4 py-3.5 align-top text-xs text-slate-700">
                <span className="font-semibold uppercase">{res.language}</span>
                {res.estimated_minutes ? ` · ${res.estimated_minutes} min` : ''}
              </td>
              <td className="px-4 py-3.5 align-top">
                <Badge tone={res.is_active ? 'success' : 'warning'}>
                  {res.is_active ? 'ACTIVE' : 'INACTIVE'}
                </Badge>
              </td>
              <td className="px-4 py-3.5 align-top">
                <div className="flex flex-wrap items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    aria-label={`Edit ${res.title}`}
                    onClick={() => openEditModal(res)}
                  >
                    <Pencil aria-hidden="true" className="h-3.5 w-3.5" />
                    Edit
                  </Button>
                  <Button
                    variant={res.is_active ? 'ghost' : 'secondary'}
                    size="sm"
                    isLoading={pendingToggleId === res.resource_id}
                    aria-label={`${res.is_active ? 'Deactivate' : 'Reactivate'} ${res.title}`}
                    onClick={() =>
                      toggleStatusMutation.mutate({
                        resourceId: res.resource_id,
                        nextActive: !res.is_active,
                      })
                    }
                  >
                    {res.is_active ? (
                      <>
                        <Power aria-hidden="true" className="h-3.5 w-3.5 text-amber-700" />
                        Deactivate
                      </>
                    ) : (
                      <>
                        <RotateCcw aria-hidden="true" className="h-3.5 w-3.5" />
                        Reactivate
                      </>
                    )}
                  </Button>
                </div>
              </td>
            </tr>
          ))}
        </ResponsiveTable>
      )}

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
                  className="inline-flex items-center gap-1 font-semibold text-blue-700 underline hover:text-blue-900"
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
