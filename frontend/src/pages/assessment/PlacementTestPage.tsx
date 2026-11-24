import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, RotateCcw, Send } from 'lucide-react';
import { extractApiErrorMessage } from '../../api/admin';
import { studentApi } from '../../api/student';
import { AppLayout } from '../../components/layout/AppLayout';
import {
  Badge,
  Button,
  Card,
  CodeSnippetBlock,
  Modal,
  ProgressBar,
  cn,
} from '../../components/ui';
import { useAuth } from '../../context/AuthContext';
import type {
  AnswerOption,
  AssessmentQuestionsResponse,
  TestType,
} from '../../types/api';

interface StoredExamDraft {
  session: AssessmentQuestionsResponse;
  answersByQuestionId: Record<string, AnswerOption | null>;
}

function getDraftStorageKey(
  userId: string,
  testType: TestType,
  targetTopicId: string | null,
): string {
  return `learnpath_exam_draft_${userId}_${testType}_${targetTopicId || 'all'}`;
}

export function PlacementTestPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();

  const queryType = searchParams.get('type') === 'TOPIC_QUIZ' ? 'TOPIC_QUIZ' : 'DIAGNOSTIC';
  const queryTopicId = searchParams.get('topicId');

  const [session, setSession] = useState<AssessmentQuestionsResponse | null>(null);
  const [answersByQuestionId, setAnswersByQuestionId] = useState<
    Record<string, AnswerOption | null>
  >({});
  const [loadError, setLoadError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [pendingReconnectSync, setPendingReconnectSync] = useState(false);
  const [isLoadingQuestions, setIsLoadingQuestions] = useState(false);
  const [isSkipConfirmOpen, setIsSkipConfirmOpen] = useState(false);

  useEffect(() => {
    document.title =
      queryType === 'TOPIC_QUIZ'
        ? 'Topic Mastery Quiz | LearnPath'
        : 'Diagnostic Placement Assessment | LearnPath';
  }, [queryType]);

  const { data: pathData } = useQuery({
    queryKey: ['learning-path'],
    queryFn: studentApi.getLearningPath,
  });

  const unlockedTopics = useMemo(
    () => (pathData?.nodes ?? []).filter((n) => !n.is_locked),
    [pathData],
  );

  const loadFreshSession = useCallback(
    async (testType: TestType, topicId: string | null) => {
      if (!user) return;
      if (testType === 'TOPIC_QUIZ' && !topicId) {
        setSession(null);
        return;
      }

      setIsLoadingQuestions(true);
      setLoadError(null);
      setSubmitError(null);

      try {
        const fresh = await studentApi.getAssessmentQuestions(testType, topicId);
        const initialAnswers: Record<string, AnswerOption | null> = {};
        for (const q of fresh.questions) {
          initialAnswers[q.question_id] = null;
        }
        setSession(fresh);
        setAnswersByQuestionId(initialAnswers);

        const key = getDraftStorageKey(user.user_id, testType, topicId);
        const draft: StoredExamDraft = {
          session: fresh,
          answersByQuestionId: initialAnswers,
        };
        window.sessionStorage.setItem(key, JSON.stringify(draft));
      } catch (err: unknown) {
        setSession(null);
        setLoadError(
          extractApiErrorMessage(
            err,
            'Could not load assessment questions. Verify the topic is unlocked and seeded.',
          ),
        );
      } finally {
        setIsLoadingQuestions(false);
      }
    },
    [user],
  );

  // Restore sessionStorage draft on mount/param change, or fetch a fresh stateless token
  useEffect(() => {
    if (!user) return;
    const effectiveTopicId = queryType === 'TOPIC_QUIZ' ? queryTopicId : null;
    if (queryType === 'TOPIC_QUIZ' && !effectiveTopicId) {
      setSession(null);
      return;
    }

    const key = getDraftStorageKey(user.user_id, queryType, effectiveTopicId);
    const rawDraft = window.sessionStorage.getItem(key);
    if (rawDraft) {
      try {
        const parsed = JSON.parse(rawDraft) as StoredExamDraft;
        if (
          parsed?.session?.attempt_id &&
          parsed?.session?.test_session_token &&
          Array.isArray(parsed.session.questions) &&
          parsed.session.questions.length > 0
        ) {
          setSession(parsed.session);
          setAnswersByQuestionId(parsed.answersByQuestionId ?? {});
          setLoadError(null);
          return;
        }
      } catch {
        window.sessionStorage.removeItem(key);
      }
    }

    void loadFreshSession(queryType, effectiveTopicId);
  }, [user, queryType, queryTopicId, loadFreshSession]);

  const updateAnswer = (questionId: string, option: AnswerOption | null) => {
    setAnswersByQuestionId((prev) => {
      const next = { ...prev, [questionId]: option };
      if (user && session) {
        const key = getDraftStorageKey(
          user.user_id,
          session.test_type,
          session.target_topic_id,
        );
        const draft: StoredExamDraft = { session, answersByQuestionId: next };
        window.sessionStorage.setItem(key, JSON.stringify(draft));
      }
      return next;
    });
  };

  const questions = session?.questions ?? [];
  const answeredCount = useMemo(
    () => questions.filter((q) => answersByQuestionId[q.question_id] != null).length,
    [questions, answersByQuestionId],
  );

  const skippedQuestionNumbers = useMemo(
    () =>
      questions
        .map((q, idx) => (answersByQuestionId[q.question_id] == null ? idx + 1 : null))
        .filter((num): num is number => num !== null),
    [questions, answersByQuestionId],
  );

  const submitMutation = useMutation({
    mutationFn: async () => {
      if (!session) throw new Error('No active exam session.');
      return studentApi.submitAssessment({
        attempt_id: session.attempt_id,
        test_session_token: session.test_session_token,
        answers: session.questions.map((q) => ({
          question_id: q.question_id,
          selected_option: answersByQuestionId[q.question_id] ?? null,
        })),
      });
    },
    onSuccess: async (detail) => {
      if (user && session) {
        const key = getDraftStorageKey(
          user.user_id,
          session.test_type,
          session.target_topic_id,
        );
        window.sessionStorage.removeItem(key);
      }
      setPendingReconnectSync(false);
      setIsSkipConfirmOpen(false);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['learning-path'] }),
        queryClient.invalidateQueries({ queryKey: ['recommendations'] }),
        queryClient.invalidateQueries({ queryKey: ['attempts'] }),
      ]);
      navigate(`/assessment/attempts/${detail.attempt_id}`, { replace: true });
    },
    onError: (err: unknown) => {
      setIsSkipConfirmOpen(false);
      const isNetworkDrop = !(err as { response?: unknown })?.response;
      if (isNetworkDrop) {
        setPendingReconnectSync(true);
        setSubmitError(
          'Network connection interrupted. Your draft answers are saved locally and will automatically sync as soon as you reconnect.',
        );
        return;
      }
      setPendingReconnectSync(false);
      setSubmitError(
        extractApiErrorMessage(
          err,
          'Could not submit your assessment. Your draft answers remain saved locally.',
        ),
      );
    },
  });

  // Scenario 1 Alternative Flow 4a: Auto-retry saved draft submission when browser reconnects
  useEffect(() => {
    if (!pendingReconnectSync || !session) return;
    const handleOnline = () => {
      if (!submitMutation.isPending) {
        setSubmitError(null);
        submitMutation.mutate();
      }
    };
    window.addEventListener('online', handleOnline);
    return () => window.removeEventListener('online', handleOnline);
  }, [pendingReconnectSync, session, submitMutation]);

  const handleExamSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!session || submitMutation.isPending) return;
    setSubmitError(null);

    if (skippedQuestionNumbers.length > 0) {
      setIsSkipConfirmOpen(true);
      return;
    }
    submitMutation.mutate();
  };

  const switchMode = (nextType: TestType, topicId?: string) => {
    if (nextType === 'DIAGNOSTIC') {
      setSearchParams({});
    } else {
      const chosen = topicId ?? unlockedTopics[0]?.topic_id ?? '';
      setSearchParams(chosen ? { type: 'TOPIC_QUIZ', topicId: chosen } : { type: 'TOPIC_QUIZ' });
    }
  };

  return (
    <AppLayout
      pageTitle={
        queryType === 'TOPIC_QUIZ'
          ? 'Topic Mastery Verification Quiz'
          : 'Python Diagnostic Placement Assessment'
      }
      pageSubtitle="Answer what you know confidently — skipped questions are allowed and never guessed on your behalf (FR03)."
    >
      <Card className="mb-6 flex flex-wrap items-end justify-between gap-4 p-4">
        <div className="flex flex-wrap items-end gap-3">
          <Button
            variant={queryType === 'DIAGNOSTIC' ? 'primary' : 'outline'}
            size="sm"
            onClick={() => switchMode('DIAGNOSTIC')}
          >
            Diagnostic Placement (All Topics)
          </Button>
          <Button
            variant={queryType === 'TOPIC_QUIZ' ? 'primary' : 'outline'}
            size="sm"
            onClick={() => switchMode('TOPIC_QUIZ', queryTopicId ?? unlockedTopics[0]?.topic_id)}
          >
            Single-Topic Mastery Quiz
          </Button>

          {queryType === 'TOPIC_QUIZ' ? (
            <div className="flex flex-col gap-1">
              <label htmlFor="quiz-topic-select" className="text-xs font-semibold text-slate-700">
                Unlocked topic
              </label>
              <select
                id="quiz-topic-select"
                name="target_topic_id"
                value={queryTopicId ?? ''}
                onChange={(e) => switchMode('TOPIC_QUIZ', e.target.value)}
                className="min-h-9 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900"
              >
                <option value="" disabled>
                  Choose unlocked topic...
                </option>
                {unlockedTopics.map((t) => (
                  <option key={t.topic_id} value={t.topic_id}>
                    {t.display_order}. {t.name} ({t.mastery_status})
                  </option>
                ))}
              </select>
            </div>
          ) : null}
        </div>

        {session ? (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              if (user) {
                window.sessionStorage.removeItem(
                  getDraftStorageKey(
                    user.user_id,
                    session.test_type,
                    session.target_topic_id,
                  ),
                );
              }
              void loadFreshSession(session.test_type, session.target_topic_id);
            }}
          >
            <RotateCcw aria-hidden="true" className="h-3.5 w-3.5" />
            Reset Draft Session
          </Button>
        ) : null}
      </Card>

      {loadError ? (
        <Card role="alert" className="border-red-200 bg-red-50 text-sm text-red-800">
          {loadError}
        </Card>
      ) : isLoadingQuestions ? (
        <Card className="p-8 text-center text-sm text-slate-600">
          Preparing signed assessment session...
        </Card>
      ) : !session ? (
        <Card className="p-8 text-center text-sm text-slate-600">
          Select an unlocked topic above to begin a Topic Mastery Quiz.
        </Card>
      ) : (
        <form method="post" action="/api/v1/assessments/submit" onSubmit={handleExamSubmit}>
          <Card className="sticky top-3 z-10 mb-6 border-blue-200 bg-white/95 p-4 backdrop-blur">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="min-w-[240px] flex-1">
                <ProgressBar
                  label={`Answered ${answeredCount} of ${questions.length} questions (${skippedQuestionNumbers.length} unanswered)`}
                  value={answeredCount}
                  max={questions.length}
                />
              </div>
              <Button type="submit" isLoading={submitMutation.isPending}>
                <Send aria-hidden="true" className="h-4 w-4" />
                Submit Assessment
              </Button>
            </div>
            {submitError ? (
              <p role="alert" className="mt-2 text-xs font-semibold text-red-600">
                {submitError}
              </p>
            ) : null}
          </Card>

          <div className="space-y-5">
            {questions.map((q, index) => {
              const selected = answersByQuestionId[q.question_id] ?? null;
              const options: [AnswerOption, string][] = [
                ['A', q.option_a],
                ['B', q.option_b],
                ['C', q.option_c],
                ['D', q.option_d],
              ];

              return (
                <Card key={q.question_id} className="space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <Badge tone="neutral">Question {index + 1}</Badge>
                      <Badge tone="info">{q.topic_name}</Badge>
                    </div>
                    {selected ? (
                      <button
                        type="button"
                        onClick={() => updateAnswer(q.question_id, null)}
                        className="text-xs font-medium text-slate-500 hover:text-slate-800 hover:underline"
                      >
                        Clear choice (leave unanswered)
                      </button>
                    ) : (
                      <Badge tone="warning">Unanswered</Badge>
                    )}
                  </div>

                  {q.code_snippet ? <CodeSnippetBlock code={q.code_snippet} /> : null}

                  <fieldset className="border-0 p-0">
                    <legend className="text-base font-semibold text-slate-900">
                      {q.question_text}
                    </legend>
                    <div className="mt-3 grid gap-2.5 sm:grid-cols-2">
                      {options.map(([letter, text]) => {
                        const inputId = `q-${q.question_id}-${letter}`;
                        const isChecked = selected === letter;
                        return (
                          <div key={letter} className="relative">
                            <input
                              type="radio"
                              id={inputId}
                              name={`question_${q.question_id}`}
                              value={letter}
                              checked={isChecked}
                              onChange={() => updateAnswer(q.question_id, letter)}
                              className="visually-hidden peer"
                            />
                            <label
                              htmlFor={inputId}
                              className={cn(
                                'flex min-h-12 cursor-pointer items-start gap-3 rounded-xl border p-3.5 text-sm transition-colors',
                                'peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-blue-600',
                                isChecked
                                  ? 'border-blue-600 bg-blue-50/80 font-semibold text-slate-900'
                                  : 'border-slate-300 bg-white text-slate-800 hover:border-slate-400',
                              )}
                            >
                              <span
                                aria-hidden="true"
                                className={cn(
                                  'flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-xs font-bold',
                                  isChecked
                                    ? 'border-blue-600 bg-blue-600 text-white'
                                    : 'border-slate-300 bg-slate-50 text-slate-700',
                                )}
                              >
                                {letter}
                              </span>
                              <span className="pt-0.5">{text}</span>
                            </label>
                          </div>
                        );
                      })}
                    </div>
                  </fieldset>
                </Card>
              );
            })}
          </div>
        </form>
      )}

      <Modal
        open={isSkipConfirmOpen}
        onClose={() => setIsSkipConfirmOpen(false)}
        title="Submit With Unanswered Questions?"
        description="Unanswered questions are recorded with selected_option = NULL and scored as 0 points so your diagnostic stays honest."
      >
        <div className="space-y-4">
          <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 p-3.5 text-sm text-amber-950">
            <AlertTriangle aria-hidden="true" className="mt-0.5 h-5 w-5 shrink-0 text-amber-700" />
            <div>
              <p className="font-semibold">
                You left {skippedQuestionNumbers.length} question
                {skippedQuestionNumbers.length === 1 ? '' : 's'} unanswered:
              </p>
              <p className="mt-1 text-xs text-amber-900">
                Question #{skippedQuestionNumbers.join(', #')}
              </p>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <Button
              variant="outline"
              autoFocus
              onClick={() => setIsSkipConfirmOpen(false)}
              disabled={submitMutation.isPending}
            >
              Review Questions
            </Button>
            <Button
              variant="primary"
              isLoading={submitMutation.isPending}
              onClick={() => submitMutation.mutate()}
            >
              Confirm &amp; Submit Now
            </Button>
          </div>
        </div>
      </Modal>
    </AppLayout>
  );
}
