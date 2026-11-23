import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { BookOpen, CheckCircle2, Compass, MinusCircle, XCircle } from 'lucide-react';
import { studentApi } from '../../api/student';
import { AppLayout } from '../../components/layout/AppLayout';
import {
  Badge,
  Button,
  Card,
  CodeSnippetBlock,
  ResponsiveTable,
  cn,
} from '../../components/ui';

type AnswerFilter = 'ALL' | 'INCORRECT' | 'SKIPPED' | 'CORRECT';

export function AnswerReviewPage() {
  const { attemptId } = useParams<{ attemptId: string }>();
  const [filter, setFilter] = useState<AnswerFilter>('ALL');

  useEffect(() => {
    document.title = 'Assessment Results & Solution Review | LearnPath';
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

  const filteredAnswers = useMemo(() => {
    const answers = attempt?.answers ?? [];
    if (filter === 'CORRECT') return answers.filter((a) => a.is_correct);
    if (filter === 'SKIPPED') return answers.filter((a) => a.is_skipped);
    if (filter === 'INCORRECT') return answers.filter((a) => !a.is_correct && !a.is_skipped);
    return answers;
  }, [attempt, filter]);

  const donutData = useMemo(
    () => [
      { name: 'Correct', value: stats.correct, color: '#059669' },
      { name: 'Incorrect', value: stats.incorrect, color: '#dc2626' },
      { name: 'Skipped', value: stats.skipped, color: '#d97706' },
    ].filter((d) => d.value > 0),
    [stats],
  );

  return (
    <AppLayout
      pageTitle="Assessment Results & Solution Review"
      pageSubtitle="Inspect topic mastery breakdown, skipped questions, and step-by-step explanations (FR04)."
    >
      {isLoading ? (
        <Card className="p-8 text-center text-sm text-slate-600">Loading attempt review...</Card>
      ) : isError || !attempt ? (
        <Card role="alert" className="border-red-200 bg-red-50 text-sm text-red-800">
          Assessment attempt could not be found.
        </Card>
      ) : (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-4">
            <Card className="p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Overall Score
              </p>
              <p className="mt-1 text-3xl font-bold text-slate-900">
                {attempt.overall_score_percent.toFixed(1)}%
              </p>
              <Badge
                tone={attempt.overall_score_percent >= 70 ? 'success' : 'warning'}
                className="mt-2"
              >
                {attempt.test_type}
              </Badge>
            </Card>
            <Card className="p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Correct</p>
              <p className="mt-1 text-3xl font-bold text-emerald-700">{stats.correct}</p>
              <p className="mt-1 text-xs text-slate-500">of {stats.total} questions</p>
            </Card>
            <Card className="p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Incorrect
              </p>
              <p className="mt-1 text-3xl font-bold text-red-600">{stats.incorrect}</p>
              <p className="mt-1 text-xs text-slate-500">Needs concept review</p>
            </Card>
            <Card className="p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Skipped (NULL)
              </p>
              <p className="mt-1 text-3xl font-bold text-amber-700">{stats.skipped}</p>
              <p className="mt-1 text-xs text-slate-500">Honest gap signal</p>
            </Card>
          </div>

          <div className="flex flex-wrap gap-3">
            <Link
              to="/recommendations"
              className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700"
            >
              <BookOpen aria-hidden="true" className="h-4 w-4" />
              View Personalized Recommendations
            </Link>
            <Link
              to="/roadmap"
              className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-800 hover:bg-slate-50"
            >
              <Compass aria-hidden="true" className="h-4 w-4" />
              Open Updated Learning Roadmap
            </Link>
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            <Card>
              <figure>
                <figcaption className="mb-3 text-sm font-semibold text-slate-900">
                  Response Distribution
                </figcaption>
                <div className="h-52 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={donutData}
                        dataKey="value"
                        nameKey="name"
                        innerRadius={48}
                        outerRadius={76}
                        paddingAngle={3}
                      >
                        {donutData.map((entry) => (
                          <Cell key={entry.name} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </figure>
            </Card>

            <Card className="lg:col-span-2">
              <figure>
                <figcaption className="mb-3 text-sm font-semibold text-slate-900">
                  Topic Mastery Breakdown (70% Threshold)
                </figcaption>
                <div className="h-52 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={attempt.topic_scores}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis dataKey="topic_name" tick={{ fontSize: 11 }} />
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

          {/* Semantic table alternative for screen-reader and keyboard chart parity */}
          <ResponsiveTable
            caption="Per-topic score and mastery summary"
            hideCaptionVisually={false}
            headers={['Topic', 'Correct / Questions', 'Score %', 'Updated Mastery Status']}
          >
            {attempt.topic_scores.map((ts) => (
              <tr key={ts.topic_id}>
                <th scope="row" className="px-4 py-3 font-semibold text-slate-900">
                  {ts.topic_name}
                </th>
                <td className="px-4 py-3 text-slate-700">
                  {ts.correct_count} / {ts.question_count}
                </td>
                <td className="px-4 py-3 font-semibold text-slate-900">
                  {ts.score_percent.toFixed(1)}%
                </td>
                <td className="px-4 py-3">
                  <Badge tone={ts.mastery_status === 'MASTERED' ? 'success' : 'warning'}>
                    {ts.mastery_status}
                  </Badge>
                </td>
              </tr>
            ))}
          </ResponsiveTable>

          <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
            <h2 className="text-lg font-bold text-slate-900">Question-by-Question Solutions</h2>
            <div className="flex flex-wrap gap-2">
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
                  variant={filter === key ? 'secondary' : 'outline'}
                  onClick={() => setFilter(key)}
                >
                  {label}
                </Button>
              ))}
            </div>
          </div>

          <div className="space-y-4">
            {filteredAnswers.map((ans, idx) => {
              const options = [
                ['A', ans.option_a],
                ['B', ans.option_b],
                ['C', ans.option_c],
                ['D', ans.option_d],
              ] as const;

              return (
                <Card key={ans.question_id} className="space-y-3.5">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge tone="neutral">Item {idx + 1}</Badge>
                      <Badge tone="info">{ans.topic_name}</Badge>
                    </div>
                    {ans.is_correct ? (
                      <Badge tone="success">
                        <CheckCircle2 aria-hidden="true" className="mr-1 h-3.5 w-3.5" />
                        CORRECT
                      </Badge>
                    ) : ans.is_skipped ? (
                      <Badge tone="warning">
                        <MinusCircle aria-hidden="true" className="mr-1 h-3.5 w-3.5" />
                        SKIPPED (No Option Selected)
                      </Badge>
                    ) : (
                      <Badge tone="danger">
                        <XCircle aria-hidden="true" className="mr-1 h-3.5 w-3.5" />
                        INCORRECT
                      </Badge>
                    )}
                  </div>

                  <p className="text-base font-semibold text-slate-900">{ans.question_text}</p>

                  {ans.code_snippet ? <CodeSnippetBlock code={ans.code_snippet} /> : null}

                  <div className="grid gap-2 sm:grid-cols-2">
                    {options.map(([letter, text]) => {
                      const isCorrectOpt = ans.correct_option === letter;
                      const isStudentChoice = ans.selected_option === letter;

                      return (
                        <div
                          key={letter}
                          className={cn(
                            'rounded-lg border px-3.5 py-2.5 text-sm',
                            isCorrectOpt
                              ? 'border-emerald-400 bg-emerald-50/80 font-semibold text-emerald-950'
                              : isStudentChoice
                                ? 'border-red-300 bg-red-50/80 font-semibold text-red-900'
                                : 'border-slate-200 bg-white text-slate-700',
                          )}
                        >
                          <span className="mr-2 font-bold">{letter}.</span>
                          {text}
                          {isCorrectOpt ? ' (Correct Answer)' : ''}
                          {isStudentChoice && !isCorrectOpt ? ' (Your Answer)' : ''}
                          {isStudentChoice && isCorrectOpt ? ' (Your Answer)' : ''}
                        </div>
                      );
                    })}
                  </div>

                  <div className="rounded-xl border border-blue-200 bg-blue-50/70 p-4 text-sm text-slate-800">
                    <p className="font-semibold text-blue-950">Solution &amp; Explanation</p>
                    <p className="mt-1 leading-relaxed">{ans.explanation}</p>
                  </div>
                </Card>
              );
            })}
          </div>
        </div>
      )}
    </AppLayout>
  );
}
