import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
} from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  RotateCcw,
  Send,
} from 'lucide-react';
import { extractApiErrorMessage } from '../../api/admin';
import { studentApi } from '../../api/student';
import { AppLayout } from '../../components/layout/AppLayout';
import {
  Badge,
  Button,
  Card,
  CodeSnippetBlock,
  Modal,
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
  currentIndex?: number;
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
  const questionHeadingRef = useRef<HTMLHeadingElement | null>(null);

  const queryType = searchParams.get('type') === 'TOPIC_QUIZ' ? 'TOPIC_QUIZ' : 'DIAGNOSTIC';
  const queryTopicId = searchParams.get('topicId');

  const [session, setSession] = useState<AssessmentQuestionsResponse | null>(null);
  const [answersByQuestionId, setAnswersByQuestionId] = useState<
    Record<string, AnswerOption | null>
  >({});
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [pendingReconnectSync, setPendingReconnectSync] = useState(false);
  const [isLoadingQuestions, setIsLoadingQuestions] = useState(false);
  const [isSkipConfirmOpen, setIsSkipConfirmOpen] = useState(false);

  useEffect(() => {
    document.title =
      queryType === 'TOPIC_QUIZ'
        ? 'Topic Mastery Quiz | LearnPath'
        : 'Python Placement Test | LearnPath';
  }, [queryType]);

  const { data: pathData } = useQuery({
    queryKey: ['learning-path'],
    queryFn: studentApi.getLearningPath,
  });

  const unlockedTopics = useMemo(
    () => (pathData?.nodes ?? []).filter((n) => !n.is_locked),
    [pathData],
  );

  const persistDraft = useCallback(
    (
      nextSession: AssessmentQuestionsResponse,
      nextAnswers: Record<string, AnswerOption | null>,
      nextIdx: number,
    ) => {
      if (!user) return;
      const key = getDraftStorageKey(
        user.user_id,
        nextSession.test_type,
        nextSession.target_topic_id,
      );
      const draft: StoredExamDraft = {
        session: nextSession,
        answersByQuestionId: nextAnswers,
        currentIndex: nextIdx,
      };
      window.sessionStorage.setItem(key, JSON.stringify(draft));
    },
    [user],
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
        setCurrentIndex(0);
        persistDraft(fresh, initialAnswers, 0);
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
    [user, persistDraft],
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
          const clampedIdx = Math.min(
            Math.max(parsed.currentIndex ?? 0, 0),
            parsed.session.questions.length - 1,
          );
          setSession(parsed.session);
          setAnswersByQuestionId(parsed.answersByQuestionId ?? {});
          setCurrentIndex(clampedIdx);
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
      if (session) {
        persistDraft(session, next, currentIndex);
      }
      return next;
    });
  };

  const goToQuestion = (nextIdx: number) => {
    if (!session) return;
    const bounded = Math.min(Math.max(nextIdx, 0), session.questions.length - 1);
    setCurrentIndex(bounded);
    persistDraft(session, answersByQuestionId, bounded);
    window.requestAnimationFrame(() => {
      questionHeadingRef.current?.focus();
    });
  };

  const questions = session?.questions ?? [];
  const activeQuestion = questions[currentIndex] ?? null;

  const answeredCount = useMemo(
    () => questions.filter((q) => answersByQuestionId[q.question_id] != null).length,
    [questions, answersByQuestionId],
  );

  const progressPercent =
    questions.length > 0 ? Math.round(((currentIndex + 1) / questions.length) * 100) : 0;

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

  const headerPill =
    session && questions.length > 0
      ? `${queryType === 'TOPIC_QUIZ' ? 'Topic Mastery Quiz' : 'Python Placement Test'}  |  Question ${currentIndex + 1} of ${questions.length}`
      : queryType === 'TOPIC_QUIZ'
        ? 'Topic Mastery Quiz'
        : 'Python Placement Test';

  return (
    <AppLayout
      variant="focused"
      hidePageHeader
      contextPill={headerPill}
      pageTitle={
        queryType === 'TOPIC_QUIZ'
          ? 'Topic Mastery Verification Quiz'
          : 'Python Diagnostic Placement Test'
      }
    >
      <div className="mx-auto max-w-3xl space-y-5">
        {/* Compact Mode Switcher Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[#dce6df] bg-white px-4 py-2.5">
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              aria-pressed={queryType === 'DIAGNOSTIC'}
              onClick={() => switchMode('DIAGNOSTIC')}
              className={cn(
                'min-h-8 rounded-lg px-3 py-1 text-xs font-semibold transition-colors',
                queryType === 'DIAGNOSTIC'
                  ? 'bg-[#14532d] text-white'
                  : 'text-slate-600 hover:bg-[#edf5f0]',
              )}
            >
              Placement Test (All Topics)
            </button>
            <button
              type="button"
              aria-pressed={queryType === 'TOPIC_QUIZ'}
              onClick={() => switchMode('TOPIC_QUIZ', queryTopicId ?? unlockedTopics[0]?.topic_id)}
              className={cn(
                'min-h-8 rounded-lg px-3 py-1 text-xs font-semibold transition-colors',
                queryType === 'TOPIC_QUIZ'
                  ? 'bg-[#14532d] text-white'
                  : 'text-slate-600 hover:bg-[#edf5f0]',
              )}
            >
              Topic Mastery Quiz
            </button>

            {queryType === 'TOPIC_QUIZ' ? (
              <div className="flex items-center gap-1.5">
                <label htmlFor="quiz-topic-select" className="visually-hidden">
                  Unlocked topic
                </label>
                <select
                  id="quiz-topic-select"
                  name="target_topic_id"
                  value={queryTopicId ?? ''}
                  onChange={(e) => switchMode('TOPIC_QUIZ', e.target.value)}
                  className="min-h-8 rounded-lg border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-900"
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
              Reset session
            </Button>
          ) : null}
        </div>

        {loadError ? (
          <Card role="alert" className="border-red-200 bg-red-50 text-sm text-red-800">
            {loadError}
          </Card>
        ) : isLoadingQuestions ? (
          <Card className="p-10 text-center text-sm text-slate-600">
            Preparing your signed Python placement session...
          </Card>
        ) : !session || !activeQuestion ? (
          <Card className="p-10 text-center text-sm text-slate-600">
            Select an unlocked topic above to begin a Topic Mastery Quiz.
          </Card>
        ) : (
          <form method="post" action="/api/v1/assessments/submit" onSubmit={handleExamSubmit}>
            {/* Top Placement Progress Bar + Step Pills (Figma Screen 4) */}
            <div className="mb-5 space-y-2.5">
              <div className="flex items-center justify-between text-xs">
                <label
                  htmlFor="placement-step-progress"
                  className="font-bold uppercase tracking-widest text-slate-500"
                >
                  Your Placement Progress
                </label>
                <span className="font-semibold text-[#14532d]">
                  {progressPercent}% complete · {answeredCount}/{questions.length} answered
                </span>
              </div>
              <progress
                id="placement-step-progress"
                value={currentIndex + 1}
                max={questions.length}
                className="h-2 w-full overflow-hidden rounded-full [&::-moz-progress-bar]:bg-[#14532d] [&::-webkit-progress-bar]:rounded-full [&::-webkit-progress-bar]:bg-[#dce8e1] [&::-webkit-progress-value]:rounded-full [&::-webkit-progress-value]:bg-[#14532d]"
              >
                {progressPercent}%
              </progress>

              {/* Quick Question Navigator Pills */}
              <nav aria-label="Questions" className="flex flex-wrap gap-1.5 pt-1">
                {questions.map((q, idx) => {
                  const isCurrent = idx === currentIndex;
                  const isAnswered = answersByQuestionId[q.question_id] != null;
                  return (
                    <button
                      key={q.question_id}
                      type="button"
                      aria-current={isCurrent ? 'step' : undefined}
                      aria-label={`Question ${idx + 1}${isAnswered ? ' (answered)' : ' (unanswered)'}`}
                      onClick={() => goToQuestion(idx)}
                      className={cn(
                        'flex h-7 min-w-7 items-center justify-center rounded-md border px-1.5 text-[11px] font-bold transition-colors',
                        isCurrent
                          ? 'border-[#14532d] bg-[#14532d] text-white'
                          : isAnswered
                            ? 'border-[#9dc4ac] bg-[#e6f2eb] text-[#14532d]'
                            : 'border-slate-200 bg-white text-slate-600 hover:border-[#14532d]/40',
                      )}
                    >
                      {idx + 1}
                    </button>
                  );
                })}
              </nav>
            </div>

            {submitError ? (
              <div
                role="alert"
                className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-xs font-semibold text-red-700"
              >
                {submitError}
              </div>
            ) : null}

            {/* Single-Question Centered Card (Figma Screen 4) */}
            <Card className="rounded-2xl border-[#dce6df] p-6 shadow-xs sm:p-8">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <Badge tone="info">Topic: {activeQuestion.topic_name}</Badge>
                <span className="text-xs font-bold uppercase tracking-widest text-slate-400">
                  Question {String(currentIndex + 1).padStart(2, '0')}
                </span>
              </div>

              <h2
                ref={questionHeadingRef}
                tabIndex={-1}
                className="mt-4 text-lg font-bold leading-snug text-slate-900 outline-none sm:text-xl"
              >
                {activeQuestion.question_text}
              </h2>

              {activeQuestion.code_snippet ? (
                <CodeSnippetBlock code={activeQuestion.code_snippet} className="mt-4" />
              ) : null}

              <fieldset className="mt-6 border-0 p-0">
                <div className="flex items-center justify-between">
                  <legend className="text-xs font-semibold text-slate-600">
                    Select one answer (or leave blank to skip honestly)
                  </legend>
                  {answersByQuestionId[activeQuestion.question_id] ? (
                    <button
                      type="button"
                      onClick={() => updateAnswer(activeQuestion.question_id, null)}
                      className="text-xs font-semibold text-slate-500 hover:text-[#14532d] hover:underline"
                    >
                      Clear choice
                    </button>
                  ) : null}
                </div>

                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  {(
                    [
                      ['A', activeQuestion.option_a],
                      ['B', activeQuestion.option_b],
                      ['C', activeQuestion.option_c],
                      ['D', activeQuestion.option_d],
                    ] as [AnswerOption, string][]
                  ).map(([letter, text]) => {
                    const selected = answersByQuestionId[activeQuestion.question_id] ?? null;
                    const inputId = `q-${activeQuestion.question_id}-${letter}`;
                    const isChecked = selected === letter;

                    return (
                      <div key={letter} className="relative">
                        <input
                          type="radio"
                          id={inputId}
                          name={`question_${activeQuestion.question_id}`}
                          value={letter}
                          checked={isChecked}
                          onChange={() => updateAnswer(activeQuestion.question_id, letter)}
                          className="visually-hidden peer"
                        />
                        <label
                          htmlFor={inputId}
                          className={cn(
                            'flex min-h-14 cursor-pointer items-center justify-between gap-3 rounded-xl border p-3.5 text-sm transition-colors',
                            'peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-[#14532d]',
                            isChecked
                              ? 'border-[#14532d] bg-[#edf6f0] font-semibold text-slate-900 shadow-2xs'
                              : 'border-slate-200 bg-white text-slate-800 hover:border-[#14532d]/40 hover:bg-[#f8fbf9]',
                          )}
                        >
                          <span className="flex items-center gap-3">
                            <span
                              aria-hidden="true"
                              className={cn(
                                'flex h-6 w-6 shrink-0 items-center justify-center rounded-md border text-xs font-bold',
                                isChecked
                                  ? 'border-[#14532d] bg-[#14532d] text-white'
                                  : 'border-slate-300 bg-slate-50 text-slate-700',
                              )}
                            >
                              {letter}
                            </span>
                            <span>{text}</span>
                          </span>

                          <span
                            aria-hidden="true"
                            className={cn(
                              'flex h-5 w-5 shrink-0 items-center justify-center rounded-full border',
                              isChecked
                                ? 'border-[#14532d] bg-[#14532d] text-white'
                                : 'border-slate-300 bg-white',
                            )}
                          >
                            {isChecked ? <Check className="h-3 w-3" /> : null}
                          </span>
                        </label>
                      </div>
                    );
                  })}
                </div>
              </fieldset>

              {/* Step Footer Navigation */}
              <div className="mt-7 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-5">
                <Button
                  type="button"
                  variant="outline"
                  size="md"
                  disabled={currentIndex === 0}
                  onClick={() => goToQuestion(currentIndex - 1)}
                >
                  <ArrowLeft aria-hidden="true" className="h-4 w-4" />
                  <span>Previous</span>
                </Button>

                <div className="flex flex-wrap items-center gap-2.5">
                  {currentIndex < questions.length - 1 ? (
                    <>
                      <Button
                        type="submit"
                        variant="outline"
                        size="md"
                        isLoading={submitMutation.isPending}
                      >
                        Submit test
                      </Button>
                      <Button
                        type="button"
                        variant="primary"
                        size="md"
                        onClick={() => goToQuestion(currentIndex + 1)}
                      >
                        <span>Next Question</span>
                        <ArrowRight aria-hidden="true" className="h-4 w-4" />
                      </Button>
                    </>
                  ) : (
                    <Button
                      type="submit"
                      variant="primary"
                      size="md"
                      isLoading={submitMutation.isPending}
                    >
                      <Send aria-hidden="true" className="h-4 w-4" />
                      <span>Submit Assessment</span>
                    </Button>
                  )}
                </div>
              </div>
            </Card>

            <p className="mt-4 flex items-center justify-center gap-1.5 text-center text-xs font-medium text-[#14532d]">
              <CheckCircle2 aria-hidden="true" className="h-3.5 w-3.5" />
              <span>Your progress is saved automatically.</span>
            </p>
          </form>
        )}
      </div>

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
              onClick={() => {
                setIsSkipConfirmOpen(false);
                if (skippedQuestionNumbers.length > 0) {
                  goToQuestion(skippedQuestionNumbers[0] - 1);
                }
              }}
              disabled={submitMutation.isPending}
            >
              Jump to First Unanswered
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
