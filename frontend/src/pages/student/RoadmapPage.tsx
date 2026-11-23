import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Background, Controls, ReactFlow, type Edge, type Node } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { BookOpen, GraduationCap, Lock } from 'lucide-react';
import { studentApi } from '../../api/student';
import { AppLayout } from '../../components/layout/AppLayout';
import { Badge, Card } from '../../components/ui';

export function RoadmapPage() {
  const [selectedTopicId, setSelectedTopicId] = useState<string | null>(null);

  useEffect(() => {
    document.title = 'Prerequisite Learning Roadmap | LearnPath';
  }, []);

  const { data, isLoading } = useQuery({
    queryKey: ['learning-path'],
    queryFn: studentApi.getLearningPath,
  });

  const nodes = data?.nodes ?? [];
  const nameById = useMemo(
    () => new Map(nodes.map((n) => [n.topic_id, n.name])),
    [nodes],
  );

  const inspectedNode = useMemo(
    () =>
      nodes.find((n) => n.topic_id === selectedTopicId) ??
      nodes.find((n) => n.topic_id === data?.recommended_next_topic_id) ??
      nodes[0] ??
      null,
    [nodes, selectedTopicId, data?.recommended_next_topic_id],
  );

  const { flowNodes, flowEdges } = useMemo(() => {
    const flowNodesResult: Node[] = nodes.map((topic, idx) => ({
      id: topic.topic_id,
      position: { x: (idx % 2) * 320 + 50, y: Math.floor(idx / 2) * 140 + 35 },
      data: {
        label: `${topic.display_order}. ${topic.name} [${
          topic.is_locked ? 'LOCKED' : topic.mastery_status
        }]`,
      },
      style: {
        borderRadius: '12px',
        padding: '12px',
        border: topic.is_locked
          ? '2px dashed #94a3b8'
          : topic.mastery_status === 'MASTERED'
            ? '2px solid #059669'
            : '2px solid #2563eb',
        background: topic.is_locked
          ? '#f8fafc'
          : topic.mastery_status === 'MASTERED'
            ? '#ecfdf5'
            : '#ffffff',
        color: '#0f172a',
        fontWeight: 600,
        width: 255,
        cursor: 'pointer',
      },
    }));

    const flowEdgesResult: Edge[] = (data?.edges ?? []).map((edge) => ({
      id: `${edge.prerequisite_topic_id}->${edge.topic_id}`,
      source: edge.prerequisite_topic_id,
      target: edge.topic_id,
      animated: true,
    }));

    return { flowNodes: flowNodesResult, flowEdges: flowEdgesResult };
  }, [nodes, data?.edges]);

  return (
    <AppLayout
      pageTitle="Python Prerequisite Roadmap (DAG)"
      pageSubtitle="Click any curriculum node to inspect prerequisite gates, exam mastery, and recommended study actions (FR05)."
    >
      <div className="mb-4 flex flex-wrap gap-2">
        <Badge tone="success">MASTERED (&gt;= 70%)</Badge>
        <Badge tone="warning">NEEDS_PRACTICE (&lt; 70%)</Badge>
        <Badge tone="info">UNKNOWN (Unlocked)</Badge>
        <Badge tone="neutral">LOCKED (Unmet Prerequisite)</Badge>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="h-[480px] overflow-hidden p-0 lg:col-span-2">
          {isLoading ? (
            <div className="flex h-full items-center justify-center text-sm text-slate-600">
              Loading curriculum graph...
            </div>
          ) : flowNodes.length === 0 ? (
            <div className="flex h-full items-center justify-center p-6 text-sm text-slate-600">
              No curriculum topics seeded yet. Run <code>python -m scripts.seed_data</code> in{' '}
              <code>backend/</code>.
            </div>
          ) : (
            <ReactFlow
              nodes={flowNodes}
              edges={flowEdges}
              fitView
              onNodeClick={(_, node) => setSelectedTopicId(node.id)}
            >
              <Background />
              <Controls />
            </ReactFlow>
          )}
        </Card>

        <Card className="flex flex-col justify-between space-y-4">
          {inspectedNode ? (
            <>
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone="neutral">Step {inspectedNode.display_order}</Badge>
                  <Badge
                    tone={
                      inspectedNode.is_locked
                        ? 'neutral'
                        : inspectedNode.mastery_status === 'MASTERED'
                          ? 'success'
                          : 'warning'
                    }
                  >
                    {inspectedNode.is_locked ? 'LOCKED' : inspectedNode.mastery_status}
                  </Badge>
                </div>

                <h2 className="text-lg font-bold text-slate-900">{inspectedNode.name}</h2>
                <p className="text-sm text-slate-600">{inspectedNode.description}</p>

                <dl className="space-y-1.5 border-t border-slate-100 pt-3 text-xs">
                  <div className="flex justify-between">
                    <dt className="text-slate-500">Latest Exam Score</dt>
                    <dd className="font-semibold text-slate-900">
                      {inspectedNode.latest_score_percent !== null
                        ? `${inspectedNode.latest_score_percent.toFixed(1)}%`
                        : 'Not yet taken'}
                    </dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-slate-500">Self-Reported Study</dt>
                    <dd className="font-semibold text-slate-900">
                      {inspectedNode.is_manually_completed ? 'Completed' : 'In progress'}
                    </dd>
                  </div>
                </dl>

                {inspectedNode.is_locked ? (
                  <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-950">
                    <p className="flex items-center gap-1.5 font-semibold">
                      <Lock aria-hidden="true" className="h-3.5 w-3.5" />
                      Prerequisite Mastery Required (&gt;= 70%):
                    </p>
                    <ul className="mt-1 list-disc pl-4">
                      {inspectedNode.unmet_prerequisite_ids.map((pid) => (
                        <li key={pid}>{nameById.get(pid) ?? pid}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </div>

              <div className="space-y-2 pt-2">
                <Link
                  to={`/recommendations?topicId=${inspectedNode.topic_id}`}
                  className="flex min-h-10 w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-700"
                >
                  <BookOpen aria-hidden="true" className="h-4 w-4" />
                  {inspectedNode.is_locked
                    ? 'View Prerequisite Study Resources'
                    : 'Study Topic Resources'}
                </Link>
                {!inspectedNode.is_locked ? (
                  <Link
                    to={`/assessment?type=TOPIC_QUIZ&topicId=${inspectedNode.topic_id}`}
                    className="flex min-h-10 w-full items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-xs font-semibold text-slate-800 hover:bg-slate-50"
                  >
                    <GraduationCap aria-hidden="true" className="h-4 w-4" />
                    Take Topic Mastery Quiz
                  </Link>
                ) : null}
              </div>
            </>
          ) : (
            <p className="text-sm text-slate-600">Select a topic node to view details.</p>
          )}
        </Card>
      </div>
    </AppLayout>
  );
}
