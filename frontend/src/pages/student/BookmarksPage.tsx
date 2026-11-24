import { useEffect, useRef, useState, type KeyboardEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Bookmark, CheckCircle2, ExternalLink, RotateCcw, Star } from 'lucide-react';
import { studentApi } from '../../api/student';
import { AppLayout } from '../../components/layout/AppLayout';
import {
  FeedbackModal,
  type FeedbackTarget,
} from '../../components/student/FeedbackModal';
import { Badge, Button, Card } from '../../components/ui';
import type { ResourceProgressStatus } from '../../types/api';

type LibraryTab = 'bookmarks' | 'history';

export function BookmarksPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<LibraryTab>('bookmarks');
  const [feedbackTarget, setFeedbackTarget] = useState<FeedbackTarget | null>(null);

  const bookmarksTabRef = useRef<HTMLButtonElement | null>(null);
  const historyTabRef = useRef<HTMLButtonElement | null>(null);
  const bookmarksPanelRef = useRef<HTMLDivElement | null>(null);
  const historyPanelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    document.title = 'Saved Resources & Study History | LearnPath';
  }, []);

  useEffect(() => {
    const bPanel = bookmarksPanelRef.current;
    const hPanel = historyPanelRef.current;
    const onMatchBookmarks = () => setActiveTab('bookmarks');
    const onMatchHistory = () => setActiveTab('history');

    bPanel?.addEventListener('beforematch', onMatchBookmarks);
    hPanel?.addEventListener('beforematch', onMatchHistory);
    return () => {
      bPanel?.removeEventListener('beforematch', onMatchBookmarks);
      hPanel?.removeEventListener('beforematch', onMatchHistory);
    };
  }, []);

  const { data: bookmarks = [], isLoading: isLoadingBookmarks } = useQuery({
    queryKey: ['bookmarks'],
    queryFn: studentApi.listBookmarks,
  });

  const { data: history = [], isLoading: isLoadingHistory } = useQuery({
    queryKey: ['resource-history'],
    queryFn: studentApi.listResourceHistory,
  });

  const invalidateAll = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['bookmarks'] }),
      queryClient.invalidateQueries({ queryKey: ['resource-history'] }),
      queryClient.invalidateQueries({ queryKey: ['recommendations'] }),
    ]);
  };

  const openMutation = useMutation({
    mutationFn: (resourceId: string) => studentApi.recordResourceOpen(resourceId),
    onSuccess: invalidateAll,
  });

  const progressMutation = useMutation({
    mutationFn: ({
      resourceId,
      status,
    }: {
      resourceId: string;
      status: ResourceProgressStatus;
    }) => studentApi.setResourceProgress(resourceId, status),
    onSuccess: invalidateAll,
  });

  const toggleBookmarkMutation = useMutation({
    mutationFn: async ({
      resourceId,
      currentlyBookmarked,
    }: {
      resourceId: string;
      currentlyBookmarked: boolean;
    }) => {
      if (currentlyBookmarked) {
        await studentApi.removeBookmark(resourceId);
      } else {
        await studentApi.saveBookmark(resourceId);
      }
    },
    onSuccess: invalidateAll,
  });

  const handleTabKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
      e.preventDefault();
      const next = activeTab === 'bookmarks' ? 'history' : 'bookmarks';
      setActiveTab(next);
      (next === 'bookmarks' ? bookmarksTabRef.current : historyTabRef.current)?.focus();
    } else if (e.key === 'Home') {
      e.preventDefault();
      setActiveTab('bookmarks');
      bookmarksTabRef.current?.focus();
    } else if (e.key === 'End') {
      e.preventDefault();
      setActiveTab('history');
      historyTabRef.current?.focus();
    }
  };

  return (
    <AppLayout
      pageTitle="Saved Resources & Study History"
      pageSubtitle="Manage bookmarked materials, distinguish OPENED vs. COMPLETED study status, and rate resources (FR08–FR09)."
    >
      <div
        role="tablist"
        aria-label="Study library sections"
        onKeyDown={handleTabKeyDown}
        className="mb-6 flex overflow-x-auto border-b border-slate-200"
      >
        <button
          ref={bookmarksTabRef}
          type="button"
          role="tab"
          id="lib-tab-bookmarks"
          aria-selected={activeTab === 'bookmarks'}
          tabIndex={activeTab === 'bookmarks' ? 0 : -1}
          onClick={() => setActiveTab('bookmarks')}
          className="min-h-11 px-4 py-2.5 text-sm font-medium text-slate-700 hover:text-slate-900"
        >
          Saved Bookmarks ({bookmarks.length})
        </button>
        <button
          ref={historyTabRef}
          type="button"
          role="tab"
          id="lib-tab-history"
          aria-selected={activeTab === 'history'}
          tabIndex={activeTab === 'history' ? 0 : -1}
          onClick={() => setActiveTab('history')}
          className="min-h-11 px-4 py-2.5 text-sm font-medium text-slate-700 hover:text-slate-900"
        >
          Opened &amp; Completed ({history.length})
        </button>
      </div>

      <div
        ref={bookmarksPanelRef}
        role="tabpanel"
        aria-labelledby="lib-tab-bookmarks"
        {...(activeTab !== 'bookmarks' ? ({ hidden: 'until-found' } as Record<string, string>) : {})}
      >
        <div className="space-y-4">
          {isLoadingBookmarks ? (
            <Card className="p-8 text-center text-sm text-slate-600">Loading saved resources...</Card>
          ) : bookmarks.length === 0 ? (
            <Card className="p-8 text-center text-sm text-slate-600">
              You have not bookmarked any resources yet. Save items from the Recommendations page to
              build your personal study list.
            </Card>
          ) : (
            bookmarks.map((item) => (
              <Card key={item.resource_id} className="space-y-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone="info">{item.topic_name}</Badge>
                    <Badge tone="neutral">{item.content_type}</Badge>
                    <Badge tone="neutral">{item.difficulty}</Badge>
                    {!item.is_active ? <Badge tone="warning">Archived</Badge> : null}
                    {item.progress_status ? (
                      <Badge
                        tone={item.progress_status === 'COMPLETED' ? 'success' : 'info'}
                      >
                        {item.progress_status}
                      </Badge>
                    ) : null}
                    {item.my_rating ? (
                      <Badge tone="warning">{item.my_rating}/5 ★</Badge>
                    ) : null}
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <a
                      href={item.external_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label={`Open saved resource ${item.title}`}
                      onClick={() => openMutation.mutate(item.resource_id)}
                      className="inline-flex min-h-9 items-center gap-1.5 rounded-lg bg-[#14532d] px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-[#0f3f22]"
                    >
                      Open Resource
                      <ExternalLink aria-hidden="true" className="h-3.5 w-3.5" />
                    </a>

                    <Button
                      variant="outline"
                      size="sm"
                      aria-label={
                        item.progress_status === 'COMPLETED'
                          ? `Mark ${item.title} as in progress`
                          : `Mark ${item.title} as completed`
                      }
                      onClick={() =>
                        progressMutation.mutate({
                          resourceId: item.resource_id,
                          status: item.progress_status === 'COMPLETED' ? 'OPENED' : 'COMPLETED',
                        })
                      }
                    >
                      {item.progress_status === 'COMPLETED' ? (
                        <>
                          <RotateCcw aria-hidden="true" className="h-3.5 w-3.5" />
                          Reopen
                        </>
                      ) : (
                        <>
                          <CheckCircle2 aria-hidden="true" className="h-3.5 w-3.5 text-emerald-600" />
                          Mark Completed
                        </>
                      )}
                    </Button>

                    <Button
                      variant="outline"
                      size="sm"
                      aria-label={`Rate ${item.title}`}
                      onClick={() =>
                        setFeedbackTarget({
                          resource_id: item.resource_id,
                          title: item.title,
                          initialRating: item.my_rating,
                          initialComment: item.my_comment,
                        })
                      }
                    >
                      <Star aria-hidden="true" className="h-3.5 w-3.5 text-amber-500" />
                      {item.my_rating ? `Rated ${item.my_rating}★` : 'Rate'}
                    </Button>

                    <Button
                      variant="ghost"
                      size="sm"
                      aria-pressed="true"
                      aria-label={`Remove bookmark for ${item.title}`}
                      onClick={() =>
                        toggleBookmarkMutation.mutate({
                          resourceId: item.resource_id,
                          currentlyBookmarked: true,
                        })
                      }
                    >
                      <Bookmark aria-hidden="true" className="h-3.5 w-3.5 fill-[#14532d] text-[#14532d]" />
                      Saved
                    </Button>
                  </div>
                </div>

                <div>
                  <h2 className="text-base font-bold text-slate-900">{item.title}</h2>
                  <p className="mt-1 text-sm text-slate-600">{item.description}</p>
                </div>
              </Card>
            ))
          )}
        </div>
      </div>

      <div
        ref={historyPanelRef}
        role="tabpanel"
        aria-labelledby="lib-tab-history"
        {...(activeTab !== 'history' ? ({ hidden: 'until-found' } as Record<string, string>) : {})}
      >
        <div className="space-y-4">
          {isLoadingHistory ? (
            <Card className="p-8 text-center text-sm text-slate-600">Loading study history...</Card>
          ) : history.length === 0 ? (
            <Card className="p-8 text-center text-sm text-slate-600">
              No resources opened or completed yet. Opening any recommended link records{' '}
              <code>OPENED</code> automatically.
            </Card>
          ) : (
            history.map((item) => (
              <Card key={item.resource_id} className="space-y-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={item.status === 'COMPLETED' ? 'success' : 'info'}>
                      {item.status}
                    </Badge>
                    <Badge tone="info">{item.topic_name}</Badge>
                    <Badge tone="neutral">{item.content_type}</Badge>
                    {!item.is_active ? <Badge tone="warning">Archived</Badge> : null}
                    {item.my_rating ? <Badge tone="warning">{item.my_rating}/5 ★</Badge> : null}
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <a
                      href={item.external_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label={`Open study resource ${item.title}`}
                      onClick={() => openMutation.mutate(item.resource_id)}
                      className="inline-flex min-h-9 items-center gap-1.5 rounded-lg bg-[#14532d] px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-[#0f3f22]"
                    >
                      Open Again
                      <ExternalLink aria-hidden="true" className="h-3.5 w-3.5" />
                    </a>

                    <Button
                      variant="outline"
                      size="sm"
                      aria-label={
                        item.status === 'COMPLETED'
                          ? `Mark ${item.title} as in progress`
                          : `Mark ${item.title} as completed`
                      }
                      onClick={() =>
                        progressMutation.mutate({
                          resourceId: item.resource_id,
                          status: item.status === 'COMPLETED' ? 'OPENED' : 'COMPLETED',
                        })
                      }
                    >
                      {item.status === 'COMPLETED' ? 'Mark In Progress' : 'Mark Completed'}
                    </Button>

                    <Button
                      variant="outline"
                      size="sm"
                      aria-label={`Rate ${item.title}`}
                      onClick={() =>
                        setFeedbackTarget({
                          resource_id: item.resource_id,
                          title: item.title,
                          initialRating: item.my_rating,
                          initialComment: item.my_comment,
                        })
                      }
                    >
                      <Star aria-hidden="true" className="h-3.5 w-3.5 text-amber-500" />
                      {item.my_rating ? `Rated ${item.my_rating}★` : 'Rate'}
                    </Button>
                  </div>
                </div>

                <div>
                  <h2 className="text-base font-bold text-slate-900">{item.title}</h2>
                  <p className="mt-1 text-sm text-slate-600">{item.description}</p>
                </div>
              </Card>
            ))
          )}
        </div>
      </div>

      <FeedbackModal target={feedbackTarget} onClose={() => setFeedbackTarget(null)} />
    </AppLayout>
  );
}
