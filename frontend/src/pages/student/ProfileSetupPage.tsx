import { useEffect, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../../api/client';
import { AppLayout } from '../../components/layout/AppLayout';
import {
  Button,
  Card,
  CheckboxGroup,
  RadioCardGroup,
  type CheckboxOption,
  type RadioCardOption,
} from '../../components/ui';
import { useAuth } from '../../context/AuthContext';
import type {
  ContentType,
  ExperienceLevel,
  StudentProfile,
  SupportedLanguage,
} from '../../types/api';

const GOAL_OPTIONS: RadioCardOption<string>[] = [
  {
    value: 'PYTHON_FUNDAMENTALS',
    label: 'Python Fundamentals',
    description: 'Master core syntax, control flow, functions, and data structures.',
  },
  {
    value: 'DATA_SCIENCE',
    label: 'Data Science & ML Prep',
    description: 'Build strong Python foundations for data manipulation and modeling.',
  },
  {
    value: 'WEB_DEVELOPMENT',
    label: 'Backend & Automation',
    description: 'Write clean scripts, APIs, and automated workflows in Python.',
  },
];

const EXPERIENCE_OPTIONS: RadioCardOption<ExperienceLevel>[] = [
  {
    value: 'BEGINNER',
    label: 'Beginner',
    description: 'New to programming or writing first Python scripts.',
  },
  {
    value: 'INTERMEDIATE',
    label: 'Intermediate',
    description: 'Comfortable with basics; strengthening functions & structures.',
  },
  {
    value: 'ADVANCED',
    label: 'Advanced',
    description: 'Experienced coder looking to fill targeted Python gaps.',
  },
];

const FORMAT_OPTIONS: CheckboxOption<ContentType>[] = [
  {
    value: 'VIDEO',
    label: 'Video Tutorials',
    description: 'Visual walkthroughs and recorded coding explanations.',
  },
  {
    value: 'ARTICLE',
    label: 'Articles & Docs',
    description: 'Written guides, reference chapters, and code breakdowns.',
  },
  {
    value: 'EXERCISE',
    label: 'Hands-On Exercises',
    description: 'Interactive coding drills and practice problems.',
  },
];

const LANGUAGE_OPTIONS: RadioCardOption<SupportedLanguage>[] = [
  { value: 'en', label: 'English (en)', description: 'Recommend English resources.' },
  { value: 'tr', label: 'Turkish (tr)', description: 'Recommend Turkish resources.' },
];

export function ProfileSetupPage() {
  const [displayName, setDisplayName] = useState(
    () => window.sessionStorage.getItem('learnpath_pending_display_name') || '',
  );
  const [learningGoal, setLearningGoal] = useState('PYTHON_FUNDAMENTALS');
  const [experienceLevel, setExperienceLevel] = useState<ExperienceLevel>('BEGINNER');
  const [preferredFormats, setPreferredFormats] = useState<ContentType[]>(['VIDEO', 'ARTICLE']);
  const [preferredLanguage, setPreferredLanguage] = useState<SupportedLanguage>('en');
  const [formatError, setFormatError] = useState<string | undefined>();
  const [statusBanner, setStatusBanner] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [nextDestination, setNextDestination] = useState<'/assessment' | '/dashboard'>(
    '/assessment',
  );

  const { refreshUser } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    document.title = 'Profile & Learning Preferences | LearnPath';
    apiClient
      .get<StudentProfile>('/profile')
      .then(({ data }) => {
        setDisplayName(data.display_name);
        setLearningGoal(data.learning_goal);
        setExperienceLevel(data.experience_level);
        setPreferredFormats(data.preferred_formats);
        setPreferredLanguage(data.preferred_language);
      })
      .catch(() => {
        // First-time student without profile yet — defaults apply
      });
  }, []);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (preferredFormats.length === 0) {
      setFormatError('Select at least one preferred resource format.');
      return;
    }
    setFormatError(undefined);
    setStatusBanner(null);
    setIsSaving(true);

    try {
      await apiClient.put('/profile', {
        display_name: displayName,
        learning_goal: learningGoal,
        experience_level: experienceLevel,
        preferred_formats: preferredFormats,
        preferred_language: preferredLanguage,
      });
      window.sessionStorage.removeItem('learnpath_pending_display_name');
      await refreshUser();
      navigate(nextDestination);
    } catch {
      setStatusBanner('Could not save profile preferences. Please check your inputs and retry.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <AppLayout
      pageTitle="Configure Your Learning Profile"
      pageSubtitle="Personalize your Python roadmap, difficulty calibration, and resource formats in under 3 minutes."
    >
      <Card>
        <form method="post" action="/api/v1/profile" onSubmit={handleSubmit} className="space-y-6">
          {statusBanner ? (
            <div
              role="alert"
              className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
            >
              {statusBanner}
            </div>
          ) : null}

          <div className="flex flex-col gap-1.5">
            <label htmlFor="display-name" className="text-sm font-semibold text-slate-900">
              Display name <span aria-hidden="true">*</span>
            </label>
            <input
              id="display-name"
              name="display_name"
              type="text"
              required
              maxLength={120}
              autoComplete="name"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="min-h-12 max-w-md rounded-lg border border-slate-400 px-3.5 py-2.5 text-base text-slate-900"
            />
          </div>

          <RadioCardGroup
            legend="Primary learning goal"
            name="learning_goal"
            options={GOAL_OPTIONS}
            value={learningGoal}
            onChange={setLearningGoal}
          />

          <RadioCardGroup
            legend="Current Python experience level"
            name="experience_level"
            options={EXPERIENCE_OPTIONS}
            value={experienceLevel}
            onChange={setExperienceLevel}
          />

          <CheckboxGroup
            legend="Preferred learning formats (choose one or more)"
            hint="Used to rank recommended videos, articles, and interactive exercises."
            name="preferred_formats"
            options={FORMAT_OPTIONS}
            selectedValues={preferredFormats}
            onChange={(next) => {
              setPreferredFormats(next);
              if (next.length > 0) setFormatError(undefined);
            }}
            error={formatError}
          />

          <RadioCardGroup
            legend="Preferred resource language"
            name="preferred_language"
            options={LANGUAGE_OPTIONS}
            value={preferredLanguage}
            onChange={setPreferredLanguage}
          />

          <div className="flex flex-wrap justify-end gap-3 border-t border-slate-100 pt-4">
            <Button
              type="submit"
              variant="outline"
              size="lg"
              isLoading={isSaving && nextDestination === '/dashboard'}
              disabled={isSaving}
              onClick={() => setNextDestination('/dashboard')}
            >
              Save &amp; return to overview
            </Button>
            <Button
              type="submit"
              size="lg"
              isLoading={isSaving && nextDestination === '/assessment'}
              disabled={isSaving}
              onClick={() => setNextDestination('/assessment')}
            >
              Save &amp; start placement test &rarr;
            </Button>
          </div>
        </form>
      </Card>
    </AppLayout>
  );
}
