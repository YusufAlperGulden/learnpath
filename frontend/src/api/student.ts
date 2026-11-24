import { apiClient } from './client';
import type {
  AssessmentAttemptDetail,
  AssessmentAttemptSummary,
  AssessmentQuestionsResponse,
  AssessmentSubmitPayload,
  BookmarkDetailRead,
  FeedbackRead,
  FeedbackUpsertPayload,
  LearningPathResponse,
  RecommendationResponse,
  RecommenderStrategy,
  ResourceProgressRead,
  ResourceProgressStatus,
  StudyResourceHistoryItem,
  TestType,
  TopicProgressRead,
} from '../types/api';

export const studentApi = {
  getLearningPath: async (): Promise<LearningPathResponse> =>
    (await apiClient.get<LearningPathResponse>('/learning-path')).data,

  // Assessments
  getAssessmentQuestions: async (
    testType: TestType,
    targetTopicId?: string | null,
  ): Promise<AssessmentQuestionsResponse> =>
    (
      await apiClient.get<AssessmentQuestionsResponse>('/assessments/questions', {
        params: {
          test_type: testType,
          target_topic_id: testType === 'TOPIC_QUIZ' ? targetTopicId || undefined : undefined,
        },
      })
    ).data,

  submitAssessment: async (
    payload: AssessmentSubmitPayload,
  ): Promise<AssessmentAttemptDetail> =>
    (await apiClient.post<AssessmentAttemptDetail>('/assessments/submit', payload)).data,

  listAttempts: async (): Promise<AssessmentAttemptSummary[]> =>
    (await apiClient.get<AssessmentAttemptSummary[]>('/assessments/attempts')).data,

  getAttemptDetail: async (attemptId: string): Promise<AssessmentAttemptDetail> =>
    (await apiClient.get<AssessmentAttemptDetail>(`/assessments/attempts/${attemptId}`)).data,

  // Recommendations
  getRecommendations: async (params: {
    strategy?: RecommenderStrategy;
    limit?: number;
    topic_id?: string;
    include_completed?: boolean;
  } = {}): Promise<RecommendationResponse> =>
    (await apiClient.get<RecommendationResponse>('/recommendations', { params })).data,

  // Dual Progress (FR08)
  listTopicProgress: async (): Promise<TopicProgressRead[]> =>
    (await apiClient.get<TopicProgressRead[]>('/progress/topics')).data,

  toggleTopicManualCompletion: async (
    topicId: string,
    isManuallyCompleted: boolean,
  ): Promise<TopicProgressRead> =>
    (
      await apiClient.put<TopicProgressRead>(`/progress/topics/${topicId}`, {
        is_manually_completed: isManuallyCompleted,
      })
    ).data,

  listResourceHistory: async (): Promise<StudyResourceHistoryItem[]> =>
    (await apiClient.get<StudyResourceHistoryItem[]>('/progress/resources/history')).data,

  recordResourceOpen: async (resourceId: string): Promise<ResourceProgressRead> =>
    (await apiClient.post<ResourceProgressRead>(`/progress/resources/${resourceId}/open`)).data,

  setResourceProgress: async (
    resourceId: string,
    status: ResourceProgressStatus,
  ): Promise<ResourceProgressRead> =>
    (
      await apiClient.put<ResourceProgressRead>(`/progress/resources/${resourceId}`, { status })
    ).data,

  // Bookmarks (FR08)
  listBookmarks: async (): Promise<BookmarkDetailRead[]> =>
    (await apiClient.get<BookmarkDetailRead[]>('/bookmarks')).data,

  saveBookmark: async (resourceId: string): Promise<BookmarkDetailRead> =>
    (await apiClient.post<BookmarkDetailRead>('/bookmarks', { resource_id: resourceId })).data,

  removeBookmark: async (resourceId: string): Promise<void> => {
    await apiClient.delete(`/bookmarks/${resourceId}`);
  },

  // 1–5 Star Feedback (FR09)
  listFeedback: async (): Promise<FeedbackRead[]> =>
    (await apiClient.get<FeedbackRead[]>('/feedback')).data,

  upsertFeedback: async (payload: FeedbackUpsertPayload): Promise<FeedbackRead> =>
    (await apiClient.put<FeedbackRead>('/feedback', payload)).data,

  deleteFeedback: async (resourceId: string): Promise<void> => {
    await apiClient.delete(`/feedback/${resourceId}`);
  },
};
