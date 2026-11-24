import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Compass,
  MinusCircle,
  XCircle,
} from 'lucide-react';
import { studentApi } from '../../api/student';
import { AppLayout } from '../../components/layout/AppLayout';
import {
  Badge,
  Button,
  Card,
  CodeSnippetBlock,
  cn,
} from '../../components/ui';
import type { AnswerReviewItem } from '../../types/api';

type AnswerFilter = 'ALL' | 'INCORRECT' | 'SKIPPED' | 'CORRECT';

function AnswerReviewCard({
  ans,
  questionNumber,
}: {
  ans: AnswerReviewItem;
  questionNumber: number;
}) {
  const options = [
    ['A', ans.option_a],
    ['B', ans.option_b],
    ['C', ans.option_c],
    ['D', ans.option_d],
  ] as const;

  return (
    <Card className="space-y-4 rounded-2xl border-[#dce6df] p-6 shadow-xs">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="info">{ans.topic_name}</Badge>
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Question {String(questionNumber).padStart(2, '0')}
          </span>
        </div>

        {ans.is_correct ? (
          <Badge tone="success">
            <CheckCircle2 aria-hidden="true" className="mr-1 h-3.5 w-3.5" />
            Correct
          </Badge>
        ) : ans.is_skipped ? (
          <Badge tone="warning">
            <MinusCircle aria-hidden="true" className="mr-1 h-3.5 w-3.5" />
            Skipped (No Option Selected)
          </Badge>
        ) : (
          <Badge tone="danger">
            <XCircle aria-hidden="true" className="mr-1 h-3.5 w-3.5" />
            Incorrect
          </Badge>
        )}
      </div>

      <p className="text-base font-bold leading-snug text-slate-900">{ans.question_text}</p>

      {ans.code_snippet ? <CodeSnippetBlock code={ans.code_snippet} /> : null}

      <div className="grid gap-2.5 sm:grid-cols-2">
        {options.map(([letter, text]) => {
          const isCorrectOpt = ans.correct_option === letter;
          const isStudentChoice = ans.selected_option === letter;

          return (
            <div
              key={letter}
              className={cn(
                'flex items-center justify-between gap-2 rounded-xl border px-3.5 py-2.5 text-sm',
                isCorrectOpt
                  ? 'border-[#6db388] bg-[#e9f5ee] font-semibold text-[#14532d]'
                  : isStudentChoice
                    ? 'border-red-300 bg-red-50/90 font-semibold text-red-900'
                    : 'border-slate-200 bg-white text-slate-700',
              )}
            >
              <span>
                <span className="mr-2 font-bold">{letter}.</span>
                {text}
              </span>
              {isCorrectOpt ? (
                <span className="inline-flex shrink-0 items-center gap-1 text-xs font-bold text-[#14532d]">
                  <CheckCircle2 aria-hidden="true" className="h-4 w-4" />
                  {isStudentChoice ? 'Yours' : 'Correct'}
                </span>
              ) : isStudentChoice ? (
                <span className="inline-flex shrink-0 items-center gap-1 text-xs font-bold text-red-700">
                  <XCircle aria-hidden="true" className="h-4 w-4" />
                  Yours
                </span>
              ) : null}
            </div>
          );
        })}
      </div>

      <div className="rounded-xl border border-[#b9d8c5] bg-[#edf6f0] p-4 text-sm text-[#14532d]">
        <p className="text-xs font-bold uppercase tracking-wider text-[#14532d]">
          Solution &amp; Explanation
        </p>
        <p className="mt-1 leading-relaxed text-slate-800">{ans.explanation}</p>
      </div>
    </Card>
  );
}

export function AnswerReviewPage() {
  const { attemptId } = useParams<{ attemptId: string }>();
  const [filter, setFilter] = useState<AnswerFilter>('ALL');

  useEffect(() => {
    document.title = 'Detail Test Analysis & Gap Review | LearnPath';
  }, []);

  const { data: attempt, isLoading, isError } = useQuery({
    queryKey: ['attempt-detail', attemptId],
    queryFn: () => studentApi.getAttemptDetail(attemptId!),
    enabled: Boolean(attemptId),
  });

  const stats = useMemo(() => {
    const answers = attempt?.answers ?? [];
    const correct = answers.filter((a) => a.is_correct).length;
    const skipped = answers.filter((a) => a.is_skipped).length;
    const incorrect = answers.length - correct - skipped;
    return { total: answers.length, correct, incorrect, skipped };
  }, [attempt]);

  const indexedAnswers = useMemo(
    () => (attempt?.answers ?? []).map((ans, idx) => ({ ans, num: idx + 1 })),
    [attempt],
  );

  const answeredItems = useMemo(
    () => indexedAnswers.filter(({ ans }) => !ans.is_skipped),
    [indexedAnswers],
  );
  const skippedItems = useMemo(
    () => indexedAnswers.filter(({ ans }) => ans.is_skipped),
    [indexedAnswers],
  );

  const filteredItems = useMemo(() => {
    if (filter === 'CORRECT') return indexedAnswers.filter(({ ans }) => ans.is_correct);
    if (filter === 'SKIPPED') return skippedItems;
    if (filter === 'INCORRECT') {
      return indexedAnswers.filter(({ ans }) => !ans.is_correct && !ans.is_skipped);
    }
    return indexedAnswers;
  }, [indexedAnswers, skippedItems, filter]);

  const gapTopics = useMemo(
    () => (attempt?.topic_scores ?? []).filter((ts) => ts.mastery_status !== 'MASTERED'),
    [attempt],
  );

  const contextLabel = attempt
    ? `Detailed Test Analysis: ${attempt.test_type === 'DIAGNOSTIC' ? 'Python Placement Test' : 'Topic Mastery Quiz'}`
    : 'Detailed Test Analysis';

  return (
    <AppLayout
      variant="focused"
      hidePageHeader
      contextPill={contextLabel}
      pageTitle="Detail Test Analysis and Gap Review"
    >
      {isLoading ? (
        <Card className="mx-auto max-w-3xl p-10 text-center text-sm text-slate-600">
          Loading detailed test analysis...
        </Card>
      ) : isError || !attempt ? (
        <Card
          role="alert"
          className="mx-auto max-w-3xl border-red-200 bg-red-50 text-sm text-red-800"
        >
          Assessment attempt could not be found.
        </Card>
      ) : (
        <div className="mx-auto max-w-3xl space-y-6">
          {/* Centered Analysis Header (Figma Screen 5) */}
          <div className="text-center">
            <h2 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
              Detail Test Analysis and Gap Review
            </h2>
            <p className="mt-1.5 text-sm text-slate-600">
              Overall Score:{' '}
              <strong className="text-[#14532d]">
                {attempt.overall_score_percent.toFixed(1)}%
              </strong>{' '}
              · {stats.correct} Correct · {stats.incorrect} Incorrect · {stats.skipped} Skipped
            </p>
          </div>

          {/* Pathway Lock / Mastery Gate Banner (Figma Screen 5) */}
          {gapTopics.length > 0 ? (
            <div
              role="status"
              className="flex items-start gap-3 rounded-xl border border-[#96bfa5] bg-[#eaf4ee] px-4 py-3.5 text-sm text-slate-900"
            >
              <AlertTriangle
                aria-hidden="true"
                className="mt-0.5 h-5 w-5 shrink-0 text-amber-600"
              />
              <div>
                <span className="font-bold text-[#14532d]">NEW PATHWAY LOCKED: </span>
                <span>
                  Resolve the missing and incorrect topics below (
                  {gapTopics.map((g) => g.topic_name).join(', ')}) to reach &ge; 70% mastery and
                  proceed to downstream lessons.
                </span>
              </div>
            </div>
          ) : (
            <div
              role="status"
              className="flex items-center gap-3 rounded-xl border border-[#8dc0a0] bg-[#e6f3eb] px-4 py-3.5 text-sm font-semibold text-[#14532d]"
            >
              <CheckCircle2 aria-hidden="true" className="h-5 w-5 shrink-0" />
              <span>
                PATHWAY UNLOCKED: Every assessed topic achieved &ge; 70% mastery!
              </span>
            </div>
          )}

          {/* Topic Mastery Pills */}
          <div className="flex flex-wrap items-center justify-center gap-2">
            {attempt.topic_scores.map((ts) => (
              <span
                key={ts.topic_id}
                className={cn(
                  'inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold',
                  ts.mastery_status === 'MASTERED'
                    ? 'border-[#b7d9c4] bg-[#ebf6ef] text-[#14532d]'
                    : 'border-amber-200 bg-amber-50 text-amber-900',
                )}
              >
                <span>{ts.topic_name}:</span>
                <strong>{ts.score_percent.toFixed(0)}%</strong>
                <span className="text-[10px] opacity-80">
                  ({ts.correct_count}/{ts.question_count})
                </span>
              </span>
            ))}
          </div>

          {/* Filter Pills */}
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#e2eae5] pb-3">
            <p className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Question Breakdown
            </p>
            <div className="flex flex-wrap gap-1.5">
              {(
                [
                  ['ALL', `All (${stats.total})`],
                  ['INCORRECT', `Incorrect (${stats.incorrect})`],
                  ['SKIPPED', `Skipped (${stats.skipped})`],
                  ['CORRECT', `Correct (${stats.correct})`],
                ] as const
              ).map(([key, label]) => (
                <Button
                  key={key}
                  size="sm"
                  variant={filter === key ? 'primary' : 'outline'}
                  onClick={() => setFilter(key)}
                >
                  {label}
                </Button>
              ))}
            </div>
          </div>

          {/* Question Cards + Dedicated Skipped Questions Section (Figma Screen 5) */}
          {filter === 'ALL' ? (
            <div className="space-y-5">
              {answeredItems.map(({ ans, num }) => (
                <AnswerReviewCard key={ans.question_id} ans={ans} questionNumber={num} />
              ))}

              {skippedItems.length > 0 ? (
                <section aria-labelledby="skipped-section-heading" className="space-y-4 pt-2">
                  <div className="rounded-xl border border-[#d6e3db] bg-[#edf3ef] px-4 py-2.5">
                    <h3
                      id="skipped-section-heading"
                      className="text-xs font-bold uppercase tracking-widest text-slate-700"
                    >
                      Skipped Questions ({skippedItems.length})
                    </h3>
                  </div>
                  {skippedItems.map(({ ans, num }) => (
                    <AnswerReviewCard key={ans.question_id} ans={ans} questionNumber={num} />
                  ))}
                </section>
              ) : null}
            </div>
          ) : filteredItems.length === 0 ? (
            <Card className="p-8 text-center text-sm text-slate-600">
              No questions match the selected filter.
            </Card>
          ) : (
            <div className="space-y-4">
              {filteredItems.map(({ ans, num }) => (
                <AnswerReviewCard key={ans.question_id} ans={ans} questionNumber={num} />
              ))}
            </div>
          )}

          {/* Bottom Navigation Bar (Figma Screen 5 -> Screen 6 Flow) */}
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[#dce6df] pt-5">
            <Link
              to="/roadmap"
              className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-800 hover:bg-[#f4f8f5]"
            >
              <Compass aria-hidden="true" className="h-4 w-4 text-[#14532d]" />
              <span>Open Learning Roadmap</span>
            </Link>

            <Link
              to={`/recommendations?attemptId=${attempt.attempt_id}`}
              className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-[#14532d] px-5 py-2.5 text-sm font-semibold text-white shadow-xs hover:bg-[#0f3f22]"
            >
              <span>View Placement Results &amp; Recommendations</span>
              <ArrowRight aria-hidden="true" className="h-4 w-4" />
            </Link>
          </div>
        </div>
      )}
    </AppLayout>
  );
}
