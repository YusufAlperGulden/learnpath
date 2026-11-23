import { useMemo, useState, type FormEvent } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Background, Controls, ReactFlow, type Edge, type Node } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Pencil, Plus, Trash2 } from 'lucide-react';
import { adminApi, extractApiErrorMessage } from '../../api/admin';
import {
  Badge,
  Button,
  Card,
  CheckboxGroup,
  Modal,
  ResponsiveTable,
  type CheckboxOption,
} from '../../components/ui';
import type { TopicAdminRead } from '../../types/api';

interface TopicFormState {
  name: string;
  slug: string;
  description: string;
  display_order: string;
  prerequisite_topic_ids: string[];
}

const EMPTY_TOPIC_FORM: TopicFormState = {
  name: '',
  slug: '',
  description: '',
  display_order: '1',
  prerequisite_topic_ids: [],
};

function slugifyTopicName(raw: string): string {
  return raw
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

export interface AdminTopicsSectionProps {
  topics: TopicAdminRead[];
  isLoading: boolean;
}

export function AdminTopicsSection({ topics, isLoading }: AdminTopicsSectionProps) {
  const queryClient = useQueryClient();

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingTopic, setEditingTopic] = useState<TopicAdminRead | null>(null);
  const [slugTouched, setSlugTouched] = useState(false);
  const [formState, setFormState] = useState<TopicFormState>(EMPTY_TOPIC_FORM);
  const [formError, setFormError] = useState<string | null>(null);
  const [tableBanner, setTableBanner] = useState<string | null>(null);

  const topicNameById = useMemo(
    () => new Map(topics.map((t) => [t.topic_id, `${t.display_order}. ${t.name}`])),
    [topics],
  );

  const { flowNodes, flowEdges } = useMemo(() => {
    const nodes: Node[] = topics.map((t, idx) => ({
      id: t.topic_id,
      position: { x: (idx % 3) * 290 + 40, y: Math.floor(idx / 3) * 140 + 35 },
      data: {
        label: `${t.display_order}. ${t.name} (${t.active_resource_count}R / ${t.active_question_count}Q)`,
      },
      style: {
        borderRadius: '12px',
        padding: '10px 12px',
        border: '2px solid #2563eb',
        background: '#ffffff',
        color: '#0f172a',
        fontWeight: 600,
        fontSize: '12px',
        width: 245,
      },
    }));

    const edges: Edge[] = topics.flatMap((t) =>
      t.prerequisite_topic_ids.map((prereqId) => ({
        id: `${prereqId}->${t.topic_id}`,
        source: prereqId,
        target: t.topic_id,
        animated: true,
      })),
    );
    return { flowNodes: nodes, flowEdges: edges };
  }, [topics]);

  const prerequisiteOptions: CheckboxOption<string>[] = useMemo(
    () =>
      topics
        .filter((t) => !editingTopic || t.topic_id !== editingTopic.topic_id)
        .map((t) => ({
          value: t.topic_id,
          label: `${t.display_order}. ${t.name}`,
          description: `slug: ${t.slug}`,
        })),
    [topics, editingTopic],
  );

  const saveTopicMutation = useMutation({
    mutationFn: async () => {
      const orderNum = Number.parseInt(formState.display_order.trim(), 10);
      if (Number.isNaN(orderNum) || orderNum < 0) {
        throw new Error('Display order must be a non-negative integer.');
      }

      const payload = {
        name: formState.name.trim(),
        slug: formState.slug.trim(),
        description: formState.description.trim(),
        display_order: orderNum,
        prerequisite_topic_ids: formState.prerequisite_topic_ids,
      };

      if (editingTopic) {
        return adminApi.updateTopic(editingTopic.topic_id, payload);
      }
      return adminApi.createTopic(payload);
    },
    onSuccess: async () => {
      setIsModalOpen(false);
      setEditingTopic(null);
      setFormError(null);
      setTableBanner(null);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['admin', 'topics'] }),
        queryClient.invalidateQueries({ queryKey: ['learning-path'] }),
      ]);
    },
    onError: (err: unknown) => {
      if (err instanceof Error && !('response' in err)) {
        setFormError(err.message);
        return;
      }
      setFormError(
        extractApiErrorMessage(
          err,
          'Could not save topic. Circular prerequisite dependencies are not allowed.',
        ),
      );
    },
  });

  const deleteTopicMutation = useMutation({
    mutationFn: (topicId: string) => adminApi.deleteTopic(topicId),
    onSuccess: async () => {
      setTableBanner(null);
      await queryClient.invalidateQueries({ queryKey: ['admin', 'topics'] });
    },
    onError: (err: unknown) => {
      setTableBanner(
        extractApiErrorMessage(
          err,
          'Cannot delete a topic referenced by dependent topics, resources, or questions.',
        ),
      );
    },
  });

  const openCreateModal = () => {
    setEditingTopic(null);
    setSlugTouched(false);
    setFormError(null);
    setFormState({
      ...EMPTY_TOPIC_FORM,
      display_order: String(topics.length + 1),
    });
    setIsModalOpen(true);
  };

  const openEditModal = (topic: TopicAdminRead) => {
    setEditingTopic(topic);
    setSlugTouched(true);
    setFormError(null);
    setFormState({
      name: topic.name,
      slug: topic.slug,
      description: topic.description,
      display_order: String(topic.display_order),
      prerequisite_topic_ids: [...topic.prerequisite_topic_ids],
    });
    setIsModalOpen(true);
  };

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setFormError(null);
    saveTopicMutation.mutate();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-slate-900">
            Curriculum Directed Acyclic Graph (FR11)
          </h2>
          <p className="text-xs text-slate-600">
            Pure-Python DFS validation blocks self-references and transitive prerequisite cycles
            with HTTP 400.
          </p>
        </div>
        <Button onClick={openCreateModal}>
          <Plus aria-hidden="true" className="h-4 w-4" />
          Add Topic
        </Button>
      </div>

      {tableBanner ? (
        <div
          role="alert"
          className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
        >
          {tableBanner}
        </div>
      ) : null}

      <Card className="h-[320px] overflow-hidden p-0">
        {isLoading ? (
          <div className="flex h-full items-center justify-center text-sm text-slate-600">
            Loading DAG preview...
          </div>
        ) : flowNodes.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-slate-600">
            No curriculum topics created yet.
          </div>
        ) : (
          <ReactFlow nodes={flowNodes} edges={flowEdges} fitView>
            <Background />
            <Controls />
          </ReactFlow>
        )}
      </Card>

      {topics.length > 0 ? (
        <ResponsiveTable
          caption="Curriculum topics and prerequisite edges"
          headers={['Order & Topic', 'Slug', 'Prerequisites', 'Active Catalog', 'Actions']}
        >
          {topics.map((topic) => (
            <tr key={topic.topic_id}>
              <th scope="row" className="max-w-sm px-4 py-3.5 align-top font-normal">
                <div className="font-semibold text-slate-900">
                  {topic.display_order}. {topic.name}
                </div>
                <p className="mt-1 text-xs text-slate-600">{topic.description}</p>
              </th>
              <td className="px-4 py-3.5 align-top font-mono text-xs text-slate-700">
                {topic.slug}
              </td>
              <td className="px-4 py-3.5 align-top">
                {topic.prerequisite_topic_ids.length === 0 ? (
                  <Badge tone="success">Entry Topic (None)</Badge>
                ) : (
                  <div className="flex flex-wrap gap-1.5">
                    {topic.prerequisite_topic_ids.map((pid) => (
                      <Badge key={pid} tone="info">
                        {topicNameById.get(pid) ?? pid.slice(0, 8)}
                      </Badge>
                    ))}
                  </div>
                )}
              </td>
              <td className="px-4 py-3.5 align-top text-xs text-slate-700">
                <span className="font-semibold">{topic.active_resource_count}</span> resources ·{' '}
                <span className="font-semibold">{topic.active_question_count}</span> questions
              </td>
              <td className="px-4 py-3.5 align-top">
                <div className="flex flex-wrap items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    aria-label={`Edit topic ${topic.name}`}
                    onClick={() => openEditModal(topic)}
                  >
                    <Pencil aria-hidden="true" className="h-3.5 w-3.5" />
                    Edit
                  </Button>
                  {topic.active_resource_count === 0 && topic.active_question_count === 0 ? (
                    <Button
                      variant="ghost"
                      size="sm"
                      aria-label={`Delete unreferenced topic ${topic.name}`}
                      onClick={() => deleteTopicMutation.mutate(topic.topic_id)}
                    >
                      <Trash2 aria-hidden="true" className="h-3.5 w-3.5 text-red-600" />
                      Delete
                    </Button>
                  ) : null}
                </div>
              </td>
            </tr>
          ))}
        </ResponsiveTable>
      ) : null}

      <Modal
        open={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingTopic ? `Edit Topic: ${editingTopic.name}` : 'Create Curriculum Topic'}
        description="Assign display order and prerequisite topics. Any cycle (e.g. A -> B -> A) is automatically rejected."
        className="max-w-2xl"
      >
        <form
          method="post"
          action="/api/v1/admin/topics"
          onSubmit={handleSubmit}
          className="space-y-4"
        >
          {formError ? (
            <div
              role="alert"
              className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
            >
              {formError}
            </div>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-3">
            <div className="flex flex-col gap-1 sm:col-span-2">
              <label htmlFor="topic-name" className="text-sm font-semibold text-slate-900">
                Topic name <span aria-hidden="true">*</span>
              </label>
              <input
                id="topic-name"
                name="name"
                type="text"
                required
                minLength={2}
                maxLength={150}
                value={formState.name}
                onChange={(e) => {
                  const nextName = e.target.value;
                  setFormState((s) => ({
                    ...s,
                    name: nextName,
                    slug: slugTouched ? s.slug : slugifyTopicName(nextName),
                  }));
                }}
                className="min-h-11 rounded-lg border border-slate-400 px-3 py-2 text-sm text-slate-900"
              />
            </div>

            <div className="flex flex-col gap-1">
              <label htmlFor="topic-order" className="text-sm font-semibold text-slate-900">
                Display order <span aria-hidden="true">*</span>
              </label>
              <input
                id="topic-order"
                name="display_order"
                type="text"
                inputMode="numeric"
                required
                value={formState.display_order}
                onChange={(e) => setFormState((s) => ({ ...s, display_order: e.target.value }))}
                className="min-h-11 rounded-lg border border-slate-400 px-3 py-2 text-sm text-slate-900"
              />
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <label htmlFor="topic-slug" className="text-sm font-semibold text-slate-900">
              URL slug (lowercase kebab-case) <span aria-hidden="true">*</span>
            </label>
            <input
              id="topic-slug"
              name="slug"
              type="text"
              required
              pattern="^[a-z0-9]+(?:-[a-z0-9]+)*$"
              spellCheck={false}
              autoCorrect="off"
              autoCapitalize="none"
              value={formState.slug}
              onChange={(e) => {
                setSlugTouched(true);
                setFormState((s) => ({ ...s, slug: e.target.value }));
              }}
              className="min-h-11 rounded-lg border border-slate-400 px-3 py-2 font-mono text-sm text-slate-900"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label htmlFor="topic-desc" className="text-sm font-semibold text-slate-900">
              Curriculum description <span aria-hidden="true">*</span>
            </label>
            <textarea
              id="topic-desc"
              name="description"
              required
              minLength={5}
              rows={2}
              value={formState.description}
              onChange={(e) => setFormState((s) => ({ ...s, description: e.target.value }))}
              className="rounded-lg border border-slate-400 px-3 py-2 text-sm text-slate-900"
            />
          </div>

          {prerequisiteOptions.length > 0 ? (
            <CheckboxGroup
              legend="Prerequisite topics (students must reach >= 70% MASTERED first)"
              name="prerequisite_topic_ids"
              options={prerequisiteOptions}
              selectedValues={formState.prerequisite_topic_ids}
              onChange={(next) => setFormState((s) => ({ ...s, prerequisite_topic_ids: next }))}
            />
          ) : null}

          <div className="flex justify-end gap-3 border-t border-slate-100 pt-4">
            <Button variant="outline" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={saveTopicMutation.isPending}>
              {editingTopic ? 'Save topic & validate DAG' : 'Create topic'}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
