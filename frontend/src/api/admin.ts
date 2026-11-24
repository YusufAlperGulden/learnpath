import { apiClient } from './client';
import type {
  ContentType,
  DifficultyLevel,
  QuestionAdminRead,
  QuestionCreatePayload,
  QuestionUpdatePayload,
  ResourceAdminRead,
  ResourceCreatePayload,
  ResourceUpdatePayload,
  SupportedLanguage,
  TopicAdminRead,
  TopicCreatePayload,
  TopicUpdatePayload,
} from '../types/api';

export interface ResourceListFilters {
  topic_id?: string;
  content_type?: ContentType;
  difficulty?: DifficultyLevel;
  language?: SupportedLanguage;
  is_active?: boolean;
  search?: string;
}

export interface QuestionListFilters {
  topic_id?: string;
  difficulty?: DifficultyLevel;
  is_active?: boolean;
  search?: string;
}

export const adminApi = {
  // Topics & DAG
  listTopics: async (): Promise<TopicAdminRead[]> =>
    (await apiClient.get<TopicAdminRead[]>('/admin/topics')).data,

  createTopic: async (payload: TopicCreatePayload): Promise<TopicAdminRead> =>
    (await apiClient.post<TopicAdminRead>('/admin/topics', payload)).data,

  updateTopic: async (topicId: string, payload: TopicUpdatePayload): Promise<TopicAdminRead> =>
    (await apiClient.put<TopicAdminRead>(`/admin/topics/${topicId}`, payload)).data,

  deleteTopic: async (topicId: string): Promise<void> => {
    await apiClient.delete(`/admin/topics/${topicId}`);
  },

  // Resources Catalog
  listResources: async (filters: ResourceListFilters = {}): Promise<ResourceAdminRead[]> =>
    (await apiClient.get<ResourceAdminRead[]>('/admin/resources', { params: filters })).data,

  createResource: async (payload: ResourceCreatePayload): Promise<ResourceAdminRead> =>
    (await apiClient.post<ResourceAdminRead>('/admin/resources', payload)).data,

  updateResource: async (
    resourceId: string,
    payload: ResourceUpdatePayload,
  ): Promise<ResourceAdminRead> =>
    (await apiClient.put<ResourceAdminRead>(`/admin/resources/${resourceId}`, payload)).data,

  setResourceActive: async (resourceId: string, isActive: boolean): Promise<ResourceAdminRead> =>
    (
      await apiClient.patch<ResourceAdminRead>(`/admin/resources/${resourceId}/status`, {
        is_active: isActive,
      })
    ).data,

  // Versioned Question Bank
  listQuestions: async (filters: QuestionListFilters = {}): Promise<QuestionAdminRead[]> =>
    (await apiClient.get<QuestionAdminRead[]>('/admin/questions', { params: filters })).data,

  createQuestion: async (payload: QuestionCreatePayload): Promise<QuestionAdminRead> =>
    (await apiClient.post<QuestionAdminRead>('/admin/questions', payload)).data,

  updateQuestion: async (
    questionId: string,
    payload: QuestionUpdatePayload,
  ): Promise<QuestionAdminRead> =>
    (await apiClient.put<QuestionAdminRead>(`/admin/questions/${questionId}`, payload)).data,

  setQuestionActive: async (questionId: string, isActive: boolean): Promise<QuestionAdminRead> =>
    (
      await apiClient.patch<QuestionAdminRead>(`/admin/questions/${questionId}/status`, {
        is_active: isActive,
      })
    ).data,

  getQuestionLineage: async (questionId: string): Promise<QuestionAdminRead[]> =>
    (await apiClient.get<QuestionAdminRead[]>(`/admin/questions/${questionId}/lineage`)).data,
};

export { extractApiErrorMessage } from './client';
