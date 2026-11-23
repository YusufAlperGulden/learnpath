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

// Admin Catalog, DAG & Versioned Question Bank Contracts (FR10–FR12)

export interface TopicAdminRead {
  topic_id: string;
  name: string;
  slug: string;
  description: string;
  display_order: number;
  prerequisite_topic_ids: string[];
  active_resource_count: number;
  active_question_count: number;
}

export interface TopicCreatePayload {
  name: string;
  slug: string;
  description: string;
  display_order: number;
  prerequisite_topic_ids: string[];
}

export interface TopicUpdatePayload {
  name?: string;
  slug?: string;
  description?: string;
  display_order?: number;
  prerequisite_topic_ids?: string[];
}

export interface ResourceAdminRead {
  resource_id: string;
  topic_id: string;
  topic_name: string | null;
  created_by: string;
  title: string;
  description: string;
  external_url: string;
  content_type: ContentType;
  difficulty: DifficultyLevel;
  language: SupportedLanguage;
  estimated_minutes: number | null;
  is_active: boolean;
  created_at: string;
}

export interface ResourceCreatePayload {
  topic_id: string;
  title: string;
  description: string;
  external_url: string;
  content_type: ContentType;
  difficulty: DifficultyLevel;
  language: SupportedLanguage;
  estimated_minutes: number | null;
}

export interface ResourceUpdatePayload {
  topic_id?: string;
  title?: string;
  description?: string;
  external_url?: string;
  content_type?: ContentType;
  difficulty?: DifficultyLevel;
  language?: SupportedLanguage;
  estimated_minutes?: number | null;
  is_active?: boolean;
}

export interface QuestionAdminRead {
  question_id: string;
  topic_id: string;
  topic_name: string | null;
  created_by: string;
  question_text: string;
  code_snippet: string | null;
  option_a: string;
  option_b: string;
  option_c: string;
  option_d: string;
  correct_option: AnswerOption;
  explanation: string;
  difficulty: DifficultyLevel;
  version: number;
  previous_question_id: string | null;
  is_active: boolean;
  is_answered: boolean;
  created_at: string;
}

export interface QuestionCreatePayload {
  topic_id: string;
  question_text: string;
  code_snippet: string | null;
  option_a: string;
  option_b: string;
  option_c: string;
  option_d: string;
  correct_option: AnswerOption;
  explanation: string;
  difficulty: DifficultyLevel;
}

export interface QuestionUpdatePayload {
  topic_id?: string;
  question_text?: string;
  code_snippet?: string | null;
  option_a?: string;
  option_b?: string;
  option_c?: string;
  option_d?: string;
  correct_option?: AnswerOption;
  explanation?: string;
  difficulty?: DifficultyLevel;
  is_active?: boolean;
}

// Student Assessment Contracts (FR03–FR04)

export interface AssessmentQuestionPublic {
  question_id: string;
  topic_id: string;
  topic_name: string;
  question_text: string;
  code_snippet: string | null;
  option_a: string;
  option_b: string;
  option_c: string;
  option_d: string;
}

export interface AssessmentQuestionsResponse {
  attempt_id: string;
  test_type: TestType;
  target_topic_id: string | null;
  test_session_token: string;
  questions: AssessmentQuestionPublic[];
}

export interface SubmittedAnswerItem {
  question_id: string;
  selected_option: AnswerOption | null;
}

export interface AssessmentSubmitPayload {
  attempt_id: string;
  test_session_token: string;
  answers: SubmittedAnswerItem[];
}

export interface TopicScoreRead {
  topic_id: string;
  topic_name: string;
  correct_count: number;
  question_count: number;
  score_percent: number;
  mastery_status: MasteryStatus;
}

export interface AnswerReviewItem {
  question_id: string;
  topic_id: string;
  topic_name: string;
  question_text: string;
  code_snippet: string | null;
  option_a: string;
  option_b: string;
  option_c: string;
  option_d: string;
  selected_option: AnswerOption | null;
  correct_option: AnswerOption;
  is_correct: boolean;
  is_skipped: boolean;
  explanation: string;
}

export interface AssessmentAttemptSummary {
  attempt_id: string;
  test_type: TestType;
  target_topic_id: string | null;
  overall_score_percent: number;
  started_at: string;
  submitted_at: string;
}

export interface AssessmentAttemptDetail extends AssessmentAttemptSummary {
  topic_scores: TopicScoreRead[];
  answers: AnswerReviewItem[];
}

// Student Learning Path & Recommendation Contracts

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
  progress_status?: ResourceProgressStatus | null;
  is_bookmarked?: boolean;
  my_rating?: number | null;
  my_comment?: string | null;
}

// Dual Progress, Bookmarks & 1–5 Feedback Contracts (FR08–FR09)

export interface TopicProgressRead {
  student_id: string;
  topic_id: string;
  topic_name: string | null;
  is_manually_completed: boolean;
  manually_completed_at: string | null;
  latest_score_percent: number | null;
  mastery_status: MasteryStatus;
  updated_at: string;
}

export interface ResourceProgressRead {
  student_id: string;
  resource_id: string;
  status: ResourceProgressStatus;
  first_opened_at: string;
  completed_at: string | null;
  last_accessed_at: string;
}

export interface StudyResourceHistoryItem {
  resource_id: string;
  topic_id: string;
  topic_name: string;
  title: string;
  description: string;
  external_url: string;
  content_type: ContentType;
  difficulty: DifficultyLevel;
  language: SupportedLanguage;
  estimated_minutes: number | null;
  is_active: boolean;
  status: ResourceProgressStatus;
  first_opened_at: string;
  completed_at: string | null;
  last_accessed_at: string;
  is_bookmarked: boolean;
  my_rating: number | null;
  my_comment: string | null;
}

export interface BookmarkDetailRead {
  student_id: string;
  resource_id: string;
  saved_at: string;
  topic_id: string;
  topic_name: string;
  title: string;
  description: string;
  external_url: string;
  content_type: ContentType;
  difficulty: DifficultyLevel;
  language: SupportedLanguage;
  estimated_minutes: number | null;
  is_active: boolean;
  progress_status: ResourceProgressStatus | null;
  my_rating: number | null;
  my_comment: string | null;
}

export interface FeedbackUpsertPayload {
  resource_id: string;
  rating: number;
  comment?: string | null;
}

export interface FeedbackRead {
  feedback_id: string;
  student_id: string;
  resource_id: string;
  rating: number;
  comment: string | null;
  created_at: string;
}

export interface RecommendationResponse {
  strategy_used: RecommenderStrategy;
  fallback_applied: boolean;
  fallback_reason: string | null;
  priority_topics: PriorityTopicSummary[];
  items: RecommendedResourceItem[];
}
