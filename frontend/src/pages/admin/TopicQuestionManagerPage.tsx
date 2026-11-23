import { useEffect, useRef, useState, type KeyboardEvent } from 'react';
import { useQuery } from '@tanstack/react-query';
import { adminApi } from '../../api/admin';
import { AppLayout } from '../../components/layout/AppLayout';
import { AdminQuestionsSection } from './AdminQuestionsSection';
import { AdminTopicsSection } from './AdminTopicsSection';

type AdminTab = 'dag' | 'questions';

export function TopicQuestionManagerPage() {
  const [activeTab, setActiveTab] = useState<AdminTab>('dag');
  const dagTabRef = useRef<HTMLButtonElement | null>(null);
  const questionsTabRef = useRef<HTMLButtonElement | null>(null);
  const dagPanelRef = useRef<HTMLDivElement | null>(null);
  const questionsPanelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    document.title = 'Admin DAG & Question Bank | LearnPath';
  }, []);

  // Sync tab selection if browser Find-in-Page matches hidden="until-found" content
  useEffect(() => {
    const dagPanel = dagPanelRef.current;
    const qPanel = questionsPanelRef.current;
    const onMatchDag = () => setActiveTab('dag');
    const onMatchQuestions = () => setActiveTab('questions');

    dagPanel?.addEventListener('beforematch', onMatchDag);
    qPanel?.addEventListener('beforematch', onMatchQuestions);
    return () => {
      dagPanel?.removeEventListener('beforematch', onMatchDag);
      qPanel?.removeEventListener('beforematch', onMatchQuestions);
    };
  }, []);

  const { data: topics = [], isLoading: isLoadingTopics } = useQuery({
    queryKey: ['admin', 'topics'],
    queryFn: adminApi.listTopics,
  });

  const selectAndFocusTab = (next: AdminTab) => {
    setActiveTab(next);
    const ref = next === 'dag' ? dagTabRef.current : questionsTabRef.current;
    ref?.focus();
    ref?.scrollIntoView({ block: 'nearest', inline: 'nearest' });
  };

  const handleTabKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
      e.preventDefault();
      selectAndFocusTab(activeTab === 'dag' ? 'questions' : 'dag');
    } else if (e.key === 'Home') {
      e.preventDefault();
      selectAndFocusTab('dag');
    } else if (e.key === 'End') {
      e.preventDefault();
      selectAndFocusTab('questions');
    }
  };

  return (
    <AppLayout
      pageTitle="Curriculum DAG & Versioned Question Bank"
      pageSubtitle="Manage acyclic Python topic prerequisites (FR11) and immutable question versioning (FR12)."
    >
      <div
        role="tablist"
        aria-label="Curriculum and assessment administration sections"
        onKeyDown={handleTabKeyDown}
        className="mb-6 flex overflow-x-auto border-b border-slate-200"
      >
        <button
          ref={dagTabRef}
          type="button"
          role="tab"
          id="admin-tab-dag"
          aria-selected={activeTab === 'dag'}
          tabIndex={activeTab === 'dag' ? 0 : -1}
          onClick={() => setActiveTab('dag')}
          className="min-h-11 px-4 py-2.5 text-sm font-medium text-slate-700 hover:text-slate-900"
        >
          Topics &amp; Prerequisite DAG ({topics.length})
        </button>
        <button
          ref={questionsTabRef}
          type="button"
          role="tab"
          id="admin-tab-questions"
          aria-selected={activeTab === 'questions'}
          tabIndex={activeTab === 'questions' ? 0 : -1}
          onClick={() => setActiveTab('questions')}
          className="min-h-11 px-4 py-2.5 text-sm font-medium text-slate-700 hover:text-slate-900"
        >
          Versioned Question Bank
        </button>
      </div>

      {/* Tab panels keep zero box styling on the panel node itself so hidden="until-found" renders no empty strip */}
      <div
        ref={dagPanelRef}
        role="tabpanel"
        aria-labelledby="admin-tab-dag"
        {...(activeTab !== 'dag' ? ({ hidden: 'until-found' } as Record<string, string>) : {})}
      >
        <div>
          <AdminTopicsSection topics={topics} isLoading={isLoadingTopics} />
        </div>
      </div>

      <div
        ref={questionsPanelRef}
        role="tabpanel"
        aria-labelledby="admin-tab-questions"
        {...(activeTab !== 'questions'
          ? ({ hidden: 'until-found' } as Record<string, string>)
          : {})}
      >
        <div>
          <AdminQuestionsSection topics={topics} />
        </div>
      </div>
    </AppLayout>
  );
}
