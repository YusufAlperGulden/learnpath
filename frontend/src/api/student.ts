import { apiClient } from './client';
import type {
  AssessmentAttemptDetail,
  AssessmentAttemptSummary,
  AssessmentQuestionsResponse,
  AssessmentSubmitPayload,
  LearningPathResponse,
  RecommendationResponse,
  RecommenderStrategy,
  TestType,
} from '../types/api';

export const studentApi = {
  getLearningPath: async (): Promise<LearningPathResponse> =>
    (await apiClient.get<LearningPathResponse>('/learning-path')).data,

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

  getRecommendations: async (params: {
    strategy?: RecommenderStrategy;
    limit?: number;
    topic_id?: string;
  } = {}): Promise<RecommendationResponse> =>
    (await apiClient.get<RecommendationResponse>('/recommendations', { params })).data,
};
