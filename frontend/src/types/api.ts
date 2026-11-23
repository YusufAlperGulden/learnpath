// Canonical TypeScript contracts synchronized with Revised RAD v2.0 & Backend Pydantic v2

export type UserRole = 'STUDENT' | 'ADMIN';
export type ExperienceLevel = 'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED';
export type DifficultyLevel = 'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED';
export type ContentType = 'VIDEO' | 'ARTICLE' | 'EXERCISE';
export type TestType = 'DIAGNOSTIC' | 'TOPIC_QUIZ';
export type MasteryStatus = 'UNKNOWN' | 'NEEDS_PRACTICE' | 'MASTERED';
export type ResourceProgressStatus = 'OPENED' | 'COMPLETED';
export type AnswerOption = 'A' | 'B' | 'C' | 'D';
export type SupportedLanguage = 'en' | 'tr';
export type RecommenderStrategy = 'rule_based' | 'popularity' | 'cbf' | 'cf' | 'hybrid';

export interface UserRead {
  user_id: string;
  email: string;
  role: UserRole;
  has_profile: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserRead;
}

export interface StudentProfile {
  student_id: string;
  display_name: string;
  learning_goal: string;
  experience_level: ExperienceLevel;
  preferred_formats: ContentType[];
  preferred_language: SupportedLanguage;
  updated_at: string;
}

export interface StudentProfileUpsert {
  display_name: string;
  learning_goal: string;
  experience_level: ExperienceLevel;
  preferred_formats: ContentType[];
  preferred_language: SupportedLanguage;
}

export interface LearningPathNode {
  topic_id: string;
  name: string;
  slug: string;
  description: string;
  display_order: number;
  is_locked: boolean;
  unmet_prerequisite_ids: string[];
  is_manually_completed: boolean;
  latest_score_percent: number | null;
  mastery_status: MasteryStatus;
}

export interface LearningPathEdge {
  prerequisite_topic_id: string;
  topic_id: string;
}

export interface LearningPathResponse {
  nodes: LearningPathNode[];
  edges: LearningPathEdge[];
  recommended_next_topic_id: string | null;
}

export interface PriorityTopicSummary {
  topic_id: string;
  name: string;
  score_percent: number | null;
  mastery_status: MasteryStatus;
}

export interface RecommendedResourceItem {
  resource_id: string;
  title: string;
  description: string;
  external_url: string;
  content_type: ContentType;
  difficulty: DifficultyLevel;
  language: SupportedLanguage;
  estimated_minutes: number | null;
  topic_id: string;
  topic_name: string;
  rank: number;
  score: number | null;
  format_fallback_used: boolean;
  rationale: string;
}

export interface RecommendationResponse {
  strategy_used: RecommenderStrategy;
  fallback_applied: boolean;
  fallback_reason: string | null;
  priority_topics: PriorityTopicSummary[];
  items: RecommendedResourceItem[];
}
