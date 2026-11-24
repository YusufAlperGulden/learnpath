import { useEffect, useRef, type KeyboardEvent } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { adminApi } from '../../api/admin';
import { AppLayout } from '../../components/layout/AppLayout';
import { AdminQuestionsSection } from './AdminQuestionsSection';
import { AdminTopicsSection } from './AdminTopicsSection';

type AdminTab = 'dag' | 'questions';

export function TopicQuestionManagerPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab: AdminTab = searchParams.get('tab') === 'questions' ? 'questions' : 'dag';
  const autoOpenNewQuestion = searchParams.get('new') === '1';

  const dagTabRef = useRef<HTMLButtonElement | null>(null);
  const questionsTabRef = useRef<HTMLButtonElement | null>(null);
  const dagPanelRef = useRef<HTMLDivElement | null>(null);
  const questionsPanelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    document.title =
      activeTab === 'questions'
        ? 'Question Pool | LearnPath Admin'
        : 'Topics & Prerequisites | LearnPath Admin';
  }, [activeTab]);

  const setTab = (next: AdminTab) => {
    setSearchParams({ tab: next });
  };

  // Sync tab selection if browser Find-in-Page matches hidden="until-found" content
  useEffect(() => {
    const dagPanel = dagPanelRef.current;
    const qPanel = questionsPanelRef.current;
    const onMatchDag = () => setSearchParams({ tab: 'dag' });
    const onMatchQuestions = () => setSearchParams({ tab: 'questions' });

    dagPanel?.addEventListener('beforematch', onMatchDag);
    qPanel?.addEventListener('beforematch', onMatchQuestions);
    return () => {
      dagPanel?.removeEventListener('beforematch', onMatchDag);
      qPanel?.removeEventListener('beforematch', onMatchQuestions);
    };
  }, [setSearchParams]);

  const { data: topics = [], isLoading: isLoadingTopics } = useQuery({
    queryKey: ['admin', 'topics'],
    queryFn: adminApi.listTopics,
  });

  const selectAndFocusTab = (next: AdminTab) => {
    setTab(next);
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
      variant="sidebar"
      eyebrow="Curriculum & Assessment Studio"
      pageTitle={
        activeTab === 'questions'
          ? 'Versioned Question Pool'
          : 'Topics & Prerequisite Graph'
      }
      pageSubtitle="Manage acyclic Python topic prerequisites (FR11) and immutable question versioning (FR12)."
    >
      <div
        role="tablist"
        aria-label="Curriculum and assessment administration sections"
        onKeyDown={handleTabKeyDown}
        className="lp-tab-scroller mb-6 border-b border-[#dce6df]"
      >
        <button
          ref={dagTabRef}
          type="button"
          role="tab"
          id="admin-tab-dag"
          aria-selected={activeTab === 'dag'}
          tabIndex={activeTab === 'dag' ? 0 : -1}
          onClick={() => selectAndFocusTab('dag')}
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
          onClick={() => selectAndFocusTab('questions')}
          className="min-h-11 px-4 py-2.5 text-sm font-medium text-slate-700 hover:text-slate-900"
        >
          Versioned Question Pool
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
          <AdminQuestionsSection
            topics={topics}
            autoOpenCreate={autoOpenNewQuestion}
            onAutoOpenConsumed={() => setSearchParams({ tab: 'questions' }, { replace: true })}
          />
        </div>
      </div>
    </AppLayout>
  );
}
