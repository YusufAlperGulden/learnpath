import { useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Background, Controls, ReactFlow, type Edge, type Node } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { apiClient } from '../../api/client';
import { AppLayout } from '../../components/layout/AppLayout';
import { Badge, Card } from '../../components/ui';
import type { LearningPathResponse } from '../../types/api';

export function RoadmapPage() {
  useEffect(() => {
    document.title = 'Prerequisite Learning Roadmap | LearnPath';
  }, []);

  const { data, isLoading } = useQuery({
    queryKey: ['learning-path'],
    queryFn: async () => (await apiClient.get<LearningPathResponse>('/learning-path')).data,
  });

  const { flowNodes, flowEdges } = useMemo(() => {
    const items = data?.nodes ?? [];
    const flowNodesResult: Node[] = items.map((topic, idx) => ({
      id: topic.topic_id,
      position: { x: (idx % 2) * 320 + 60, y: Math.floor(idx / 2) * 140 + 40 },
      data: {
        label: `${topic.display_order}. ${topic.name} [${
          topic.is_locked ? 'LOCKED' : topic.mastery_status
        }]`,
      },
      style: {
        borderRadius: '12px',
        padding: '12px',
        border: topic.is_locked ? '2px dashed #94a3b8' : '2px solid #2563eb',
        background: topic.mastery_status === 'MASTERED' ? '#ecfdf5' : '#ffffff',
        color: '#0f172a',
        fontWeight: 600,
        width: 250,
      },
    }));

    const flowEdgesResult: Edge[] = (data?.edges ?? []).map((edge) => ({
      id: `${edge.prerequisite_topic_id}->${edge.topic_id}`,
      source: edge.prerequisite_topic_id,
      target: edge.topic_id,
      animated: true,
    }));

    return { flowNodes: flowNodesResult, flowEdges: flowEdgesResult };
  }, [data]);

  return (
    <AppLayout
      pageTitle="Python Prerequisite Roadmap (DAG)"
      pageSubtitle="Downstream topics unlock automatically once prerequisites reach MASTERED (>= 70% latest score)."
    >
      <div className="mb-4 flex flex-wrap gap-2">
        <Badge tone="success">MASTERED (&gt;= 70%)</Badge>
        <Badge tone="warning">NEEDS_PRACTICE (&lt; 70%)</Badge>
        <Badge tone="neutral">LOCKED (Unmet Prerequisite)</Badge>
      </div>

      <Card className="h-[480px] p-0 overflow-hidden">
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
          <ReactFlow nodes={flowNodes} edges={flowEdges} fitView>
            <Background />
            <Controls />
          </ReactFlow>
        )}
      </Card>
    </AppLayout>
  );
}
