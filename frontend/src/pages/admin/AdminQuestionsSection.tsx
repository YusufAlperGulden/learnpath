import { useMemo, useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { GitBranch, Lock, Pencil, Plus, Power, RotateCcw } from 'lucide-react';
import { adminApi, extractApiErrorMessage } from '../../api/admin';
import {
  Badge,
  Button,
  Card,
  CodeSnippetBlock,
  Modal,
  RadioCardGroup,
  type RadioCardOption,
} from '../../components/ui';
import type {
  AnswerOption,
  DifficultyLevel,
  QuestionAdminRead,
  TopicAdminRead,
} from '../../types/api';

type QuestionStatusFilter = 'ALL' | 'ACTIVE' | 'INACTIVE';

interface QuestionFormState {
  topic_id: string;
  question_text: string;
  code_snippet: string;
  option_a: string;
  option_b: string;
  option_c: string;
  option_d: string;
  correct_option: AnswerOption;
  explanation: string;
  difficulty: DifficultyLevel;
}

const EMPTY_QUESTION_FORM: QuestionFormState = {
  topic_id: '',
  question_text: '',
  code_snippet: '',
  option_a: '',
  option_b: '',
  option_c: '',
  option_d: '',
  correct_option: 'A',
  explanation: '',
  difficulty: 'BEGINNER',
};

const CORRECT_OPTION_CARDS: RadioCardOption<AnswerOption>[] = [
  { value: 'A', label: 'Option A' },
  { value: 'B', label: 'Option B' },
  { value: 'C', label: 'Option C' },
  { value: 'D', label: 'Option D' },
];

export interface AdminQuestionsSectionProps {
  topics: TopicAdminRead[];
}

export function AdminQuestionsSection({ topics }: AdminQuestionsSectionProps) {
  const queryClient = useQueryClient();

  const [searchQuery, setSearchQuery] = useState('');
  const [topicFilter, setTopicFilter] = useState('');
  const [difficultyFilter, setDifficultyFilter] = useState<DifficultyLevel | ''>('');
  const [statusFilter, setStatusFilter] = useState<QuestionStatusFilter>('ACTIVE');

  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [editingQuestion, setEditingQuestion] = useState<QuestionAdminRead | null>(null);
  const [formState, setFormState] = useState<QuestionFormState>(EMPTY_QUESTION_FORM);
  const [formError, setFormError] = useState<string | null>(null);

  const [lineageTargetId, setLineageTargetId] = useState<string | null>(null);
  const [pendingToggleId, setPendingToggleId] = useState<string | null>(null);

  const filters = useMemo(
    () => ({
      topic_id: topicFilter || undefined,
      difficulty: difficultyFilter || undefined,
      is_active:
        statusFilter === 'ALL' ? undefined : statusFilter === 'ACTIVE' ? true : false,
      search: searchQuery.trim() || undefined,
    }),
    [topicFilter, difficultyFilter, statusFilter, searchQuery],
  );

  const { data: questions = [], isLoading } = useQuery({
    queryKey: ['admin', 'questions', filters],
    queryFn: () => adminApi.listQuestions(filters),
  });

  const { data: lineage = [], isLoading: isLoadingLineage } = useQuery({
    queryKey: ['admin', 'question-lineage', lineageTargetId],
    queryFn: () => adminApi.getQuestionLineage(lineageTargetId!),
    enabled: Boolean(lineageTargetId),
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        topic_id: formState.topic_id,
        question_text: formState.question_text.trim(),
        code_snippet: formState.code_snippet.trim() ? formState.code_snippet : null,
        option_a: formState.option_a.trim(),
        option_b: formState.option_b.trim(),
        option_c: formState.option_c.trim(),
        option_d: formState.option_d.trim(),
        correct_option: formState.correct_option,
        explanation: formState.explanation.trim(),
        difficulty: formState.difficulty,
      };
      if (editingQuestion) {
        return adminApi.updateQuestion(editingQuestion.question_id, payload);
      }
      return adminApi.createQuestion(payload);
    },
    onSuccess: async () => {
      setIsEditorOpen(false);
      setEditingQuestion(null);
      setFormError(null);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['admin', 'questions'] }),
        queryClient.invalidateQueries({ queryKey: ['admin', 'topics'] }),
        queryClient.invalidateQueries({ queryKey: ['admin', 'question-lineage'] }),
      ]);
    },
    onError: (err: unknown) => {
      setFormError(
        extractApiErrorMessage(err, 'Could not save question. Check all required options and explanation.'),
      );
    },
  });

  const toggleStatusMutation = useMutation({
    mutationFn: async ({ questionId, nextActive }: { questionId: string; nextActive: boolean }) => {
      setPendingToggleId(questionId);
      return adminApi.setQuestionActive(questionId, nextActive);
    },
    onSettled: async () => {
      setPendingToggleId(null);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['admin', 'questions'] }),
        queryClient.invalidateQueries({ queryKey: ['admin', 'topics'] }),
      ]);
    },
  });

  const openCreateModal = () => {
    setEditingQuestion(null);
    setFormError(null);
    setFormState({
      ...EMPTY_QUESTION_FORM,
      topic_id: topics[0]?.topic_id ?? '',
    });
    setIsEditorOpen(true);
  };

  const openEditModal = (q: QuestionAdminRead) => {
    setEditingQuestion(q);
    setFormError(null);
    setFormState({
      topic_id: q.topic_id,
      question_text: q.question_text,
      code_snippet: q.code_snippet ?? '',
      option_a: q.option_a,
      option_b: q.option_b,
      option_c: q.option_c,
      option_d: q.option_d,
      correct_option: q.correct_option,
      explanation: q.explanation,
      difficulty: q.difficulty,
    });
    setIsEditorOpen(true);
  };

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!formState.topic_id) {
      setFormError('Select a curriculum topic.');
      return;
    }
    setFormError(null);
    saveMutation.mutate();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-slate-900">
            Versioned Question Pool &amp; Solution Explanations (FR12)
          </h2>
          <p className="text-xs text-slate-600">
            Editing a question already answered in any exam preserves the old row untouched and
            opens <code>version + 1</code> automatically.
          </p>
        </div>
        <Button onClick={openCreateModal} disabled={topics.length === 0}>
          <Plus aria-hidden="true" className="h-4 w-4" />
          Add Question
        </Button>
      </div>

      <Card className="p-4">
        <search>
          <form
            method="get"
            action="/admin/topics-questions"
            onSubmit={(e) => e.preventDefault()}
            className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5"
          >
            <div className="flex flex-col gap-1 lg:col-span-2">
              <label htmlFor="q-search" className="text-xs font-semibold text-slate-700">
                Search question stem or explanation
              </label>
              <input
                id="q-search"
                name="search"
                type="search"
                spellCheck={false}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="e.g. UnboundLocalError, range..."
                className="min-h-10 rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-900"
              />
            </div>

            <div className="flex flex-col gap-1">
              <label htmlFor="q-topic-filter" className="text-xs font-semibold text-slate-700">
                Topic
              </label>
              <select
                id="q-topic-filter"
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
              <label htmlFor="q-diff-filter" className="text-xs font-semibold text-slate-700">
                Difficulty
              </label>
              <select
                id="q-diff-filter"
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

            <div className="flex flex-col gap-1">
              <label htmlFor="q-status-filter" className="text-xs font-semibold text-slate-700">
                Version status
              </label>
              <select
                id="q-status-filter"
                name="status"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as QuestionStatusFilter)}
                className="min-h-10 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900"
              >
                <option value="ACTIVE">Active versions</option>
                <option value="INACTIVE">Superseded / Inactive</option>
                <option value="ALL">All versions</option>
              </select>
            </div>
          </form>
        </search>
      </Card>

      {isLoading ? (
        <Card className="p-8 text-center text-sm text-slate-600">Loading question bank...</Card>
      ) : questions.length === 0 ? (
        <Card className="p-8 text-center text-sm text-slate-600">
          No questions match the selected filters.
        </Card>
      ) : (
        <div className="space-y-4">
          {questions.map((q) => (
            <Card
              key={q.question_id}
              className={!q.is_active ? 'border-slate-200 bg-slate-50/80' : undefined}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone="info">{q.topic_name ?? 'Topic'}</Badge>
                  <Badge
                    tone={
                      q.difficulty === 'BEGINNER'
                        ? 'success'
                        : q.difficulty === 'INTERMEDIATE'
                          ? 'info'
                          : 'warning'
                    }
                  >
                    {q.difficulty}
                  </Badge>
                  <Badge tone="neutral">v{q.version}</Badge>
                  <Badge tone={q.is_active ? 'success' : 'warning'}>
                    {q.is_active ? 'ACTIVE' : 'INACTIVE / SUPERSEDED'}
                  </Badge>
                  {q.is_answered ? (
                    <Badge tone="warning">
                      <Lock aria-hidden="true" className="mr-1 h-3 w-3" />
                      Answered (edits mint v{q.version + 1})
                    </Badge>
                  ) : null}
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  {q.version > 1 || q.previous_question_id ? (
                    <Button
                      variant="outline"
                      size="sm"
                      aria-label={`View version history for question ${q.question_text.slice(0, 32)}`}
                      onClick={() => setLineageTargetId(q.question_id)}
                    >
                      <GitBranch aria-hidden="true" className="h-3.5 w-3.5" />
                      History
                    </Button>
                  ) : null}
                  <Button
                    variant="outline"
                    size="sm"
                    aria-label={`Edit question ${q.question_text.slice(0, 32)}`}
                    onClick={() => openEditModal(q)}
                  >
                    <Pencil aria-hidden="true" className="h-3.5 w-3.5" />
                    Edit
                  </Button>
                  <Button
                    variant={q.is_active ? 'ghost' : 'secondary'}
                    size="sm"
                    isLoading={pendingToggleId === q.question_id}
                    aria-label={`${q.is_active ? 'Deactivate' : 'Reactivate'} question ${q.question_text.slice(0, 32)}`}
                    onClick={() =>
                      toggleStatusMutation.mutate({
                        questionId: q.question_id,
                        nextActive: !q.is_active,
                      })
                    }
                  >
                    {q.is_active ? (
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
              </div>

              <p className="mt-3 text-sm font-semibold text-slate-900">{q.question_text}</p>

              {q.code_snippet ? (
                <CodeSnippetBlock code={q.code_snippet} className="mt-3" />
              ) : null}

              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                {(
                  [
                    ['A', q.option_a],
                    ['B', q.option_b],
                    ['C', q.option_c],
                    ['D', q.option_d],
                  ] as const
                ).map(([letter, text]) => {
                  const isCorrect = q.correct_option === letter;
                  return (
                    <div
                      key={letter}
                      className={
                        isCorrect
                          ? 'rounded-lg border border-emerald-300 bg-emerald-50/70 px-3 py-2 text-xs font-semibold text-emerald-950'
                          : 'rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700'
                      }
                    >
                      <span className="mr-1.5 font-bold">{letter}.</span>
                      {text}
                      {isCorrect ? ' (Correct Answer)' : ''}
                    </div>
                  );
                })}
              </div>

              <div className="mt-3 rounded-lg border border-blue-100 bg-blue-50/50 px-3.5 py-2.5 text-xs text-slate-700">
                <span className="font-semibold text-blue-900">Solution &amp; Explanation: </span>
                {q.explanation}
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal
        open={isEditorOpen}
        onClose={() => setIsEditorOpen(false)}
        title={
          editingQuestion
            ? `Edit Question (Current: v${editingQuestion.version})`
            : 'Create Assessment Question'
        }
        description="Answer keys and explanations stay strictly server-hidden until a student submits their attempt."
        className="max-w-3xl"
      >
        <form
          method="post"
          action="/api/v1/admin/questions"
          onSubmit={handleSubmit}
          className="space-y-4"
        >
          {editingQuestion?.is_answered ? (
            <div className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-xs text-amber-950">
              <strong>Immutable Exam History Active (FR12):</strong> Students have already answered{' '}
              <code>v{editingQuestion.version}</code>. Saving content edits will mark{' '}
              <code>v{editingQuestion.version}</code> inactive without altering past exam records
              and automatically create <code>v{editingQuestion.version + 1}</code>.
            </div>
          ) : null}

          {formError ? (
            <div
              role="alert"
              className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
            >
              {formError}
            </div>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-1">
              <label htmlFor="modal-q-topic" className="text-sm font-semibold text-slate-900">
                Curriculum topic <span aria-hidden="true">*</span>
              </label>
              <select
                id="modal-q-topic"
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
              <label htmlFor="modal-q-diff" className="text-sm font-semibold text-slate-900">
                Difficulty <span aria-hidden="true">*</span>
              </label>
              <select
                id="modal-q-diff"
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
          </div>

          <div className="flex flex-col gap-1">
            <label htmlFor="modal-q-stem" className="text-sm font-semibold text-slate-900">
              Question text <span aria-hidden="true">*</span>
            </label>
            <textarea
              id="modal-q-stem"
              name="question_text"
              required
              minLength={5}
              rows={2}
              value={formState.question_text}
              onChange={(e) => setFormState((s) => ({ ...s, question_text: e.target.value }))}
              className="rounded-lg border border-slate-400 px-3 py-2 text-sm text-slate-900"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label htmlFor="modal-q-code" className="text-sm font-semibold text-slate-900">
              Optional Python code snippet (PrismJS highlighted)
            </label>
            <textarea
              id="modal-q-code"
              name="code_snippet"
              rows={4}
              spellCheck={false}
              value={formState.code_snippet}
              onChange={(e) => setFormState((s) => ({ ...s, code_snippet: e.target.value }))}
              placeholder="count = 0&#10;while count < 3:&#10;    print(count)"
              className="rounded-lg border border-slate-400 px-3 py-2 font-mono text-xs text-slate-900"
            />
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            {(
              [
                ['option_a', 'Option A'],
                ['option_b', 'Option B'],
                ['option_c', 'Option C'],
                ['option_d', 'Option D'],
              ] as const
            ).map(([field, label]) => (
              <div key={field} className="flex flex-col gap-1">
                <label htmlFor={`modal-q-${field}`} className="text-sm font-semibold text-slate-900">
                  {label} <span aria-hidden="true">*</span>
                </label>
                <input
                  id={`modal-q-${field}`}
                  name={field}
                  type="text"
                  required
                  value={formState[field]}
                  onChange={(e) => setFormState((s) => ({ ...s, [field]: e.target.value }))}
                  className="min-h-10 rounded-lg border border-slate-400 px-3 py-2 text-sm text-slate-900"
                />
              </div>
            ))}
          </div>

          <RadioCardGroup
            legend="Correct answer key"
            name="correct_option"
            options={CORRECT_OPTION_CARDS}
            value={formState.correct_option}
            onChange={(next) => setFormState((s) => ({ ...s, correct_option: next }))}
          />

          <div className="flex flex-col gap-1">
            <label htmlFor="modal-q-explanation" className="text-sm font-semibold text-slate-900">
              Post-submission solution &amp; explanation <span aria-hidden="true">*</span>
            </label>
            <textarea
              id="modal-q-explanation"
              name="explanation"
              required
              minLength={5}
              rows={2}
              value={formState.explanation}
              onChange={(e) => setFormState((s) => ({ ...s, explanation: e.target.value }))}
              className="rounded-lg border border-slate-400 px-3 py-2 text-sm text-slate-900"
            />
          </div>

          <div className="flex justify-end gap-3 border-t border-slate-100 pt-4">
            <Button variant="outline" onClick={() => setIsEditorOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={saveMutation.isPending}>
              {editingQuestion
                ? editingQuestion.is_answered
                  ? `Save as v${editingQuestion.version + 1}`
                  : 'Save changes'
                : 'Create question'}
            </Button>
          </div>
        </form>
      </Modal>

      <Modal
        open={Boolean(lineageTargetId)}
        onClose={() => setLineageTargetId(null)}
        title="Question Version Lineage"
        description="Chronological audit trail of question edits preserving historical student attempts."
        allowLightDismiss
        className="max-w-2xl"
      >
        {isLoadingLineage ? (
          <p className="text-sm text-slate-600">Loading version chain...</p>
        ) : (
          <ol className="space-y-3">
            {lineage.map((ver) => (
              <li
                key={ver.question_id}
                className="rounded-lg border border-slate-200 bg-slate-50 p-3.5 text-xs"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone="neutral">v{ver.version}</Badge>
                  <Badge tone={ver.is_active ? 'success' : 'warning'}>
                    {ver.is_active ? 'ACTIVE' : 'SUPERSEDED'}
                  </Badge>
                  {ver.is_answered ? <Badge tone="info">Referenced by Student Answers</Badge> : null}
                </div>
                <p className="mt-2 font-semibold text-slate-900">{ver.question_text}</p>
                <p className="mt-1 text-slate-600">
                  Correct: <strong>{ver.correct_option}</strong> — {ver.explanation}
                </p>
              </li>
            ))}
          </ol>
        )}
      </Modal>
    </div>
  );
}
