import { useEffect, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
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

const GOAL_CHOICES = [
  {
    value: 'PYTHON_FUNDAMENTALS',
    label: 'Python Fundamentals — Core syntax, control flow & functions',
  },
  {
    value: 'DATA_SCIENCE',
    label: 'Data Science & Machine Learning Foundations',
  },
  {
    value: 'WEB_DEVELOPMENT',
    label: 'Backend Engineering & Web APIs',
  },
  {
    value: 'AUTOMATION',
    label: 'Scripting & Workflow Automation',
  },
  {
    value: 'ALGORITHMS_PREP',
    label: 'Problem Solving & Algorithmic Thinking',
  },
];

const EXPERIENCE_OPTIONS: RadioCardOption<ExperienceLevel>[] = [
  {
    value: 'BEGINNER',
    label: 'Beginner',
    description: 'New to coding or writing first Python scripts.',
  },
  {
    value: 'INTERMEDIATE',
    label: 'Intermediate',
    description: 'Comfortable with basics; strengthening structures.',
  },
  {
    value: 'ADVANCED',
    label: 'Advanced',
    description: 'Experienced coder targeting specific Python gaps.',
  },
];

const FORMAT_OPTIONS: CheckboxOption<ContentType>[] = [
  {
    value: 'VIDEO',
    label: 'Video Tutorials',
    description: 'Guided visual walkthroughs.',
  },
  {
    value: 'ARTICLE',
    label: 'Written Articles',
    description: 'Documentation & code guides.',
  },
  {
    value: 'EXERCISE',
    label: 'Coding Exercises',
    description: 'Hands-on practice drills.',
  },
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
    document.title = 'Set Up Your Python Learning Profile | LearnPath';
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

  const hasCustomGoal = !GOAL_CHOICES.some((g) => g.value === learningGoal);

  return (
    <AppLayout
      variant="focused"
      hidePageHeader
      pageTitle="Set Up Your Python Learning Profile"
    >
      {/* 3-Step Onboarding Stepper (Figma Screen 3) */}
      <nav aria-label="Onboarding progress" className="mx-auto mb-8 max-w-xl">
        <ol className="flex items-center justify-between gap-2 text-xs font-semibold">
          <li aria-current="step" className="flex items-center gap-2 text-[#14532d]">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[#14532d] text-[11px] font-bold text-white">
              1
            </span>
            <span>Your profile</span>
          </li>
          <li aria-hidden="true" className="h-px flex-1 bg-[#cddcd3]" />
          <li className="flex items-center gap-2 text-slate-400">
            <span className="flex h-6 w-6 items-center justify-center rounded-full border border-slate-300 bg-white text-[11px] font-bold text-slate-500">
              2
            </span>
            <span>Placement test</span>
          </li>
          <li aria-hidden="true" className="h-px flex-1 bg-[#cddcd3]" />
          <li className="flex items-center gap-2 text-slate-400">
            <span className="flex h-6 w-6 items-center justify-center rounded-full border border-slate-300 bg-white text-[11px] font-bold text-slate-500">
              3
            </span>
            <span>Your learning path</span>
          </li>
        </ol>
      </nav>

      <Card className="mx-auto max-w-2xl rounded-2xl border-[#dce6df] p-6 shadow-xs sm:p-8">
        <div className="border-b border-slate-100 pb-5">
          <p className="text-[11px] font-bold uppercase tracking-widest text-[#14532d]">
            Let&apos;s make it personal
          </p>
          <h2 className="mt-1 text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">
            Set Up Your Python Learning Profile
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Personalize your placement test difficulty, prerequisite roadmap, and study formats.
          </p>
        </div>

        <form
          method="post"
          action="/api/v1/profile"
          onSubmit={handleSubmit}
          className="mt-6 space-y-6"
        >
          {statusBanner ? (
            <div
              role="alert"
              className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
            >
              {statusBanner}
            </div>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-1.5">
              <label htmlFor="display-name" className="text-sm font-semibold text-slate-900">
                Your Name <span aria-hidden="true">*</span>
              </label>
              <input
                id="display-name"
                name="display_name"
                type="text"
                required
                maxLength={120}
                autoComplete="name"
                placeholder="e.g. Alex Rivera"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className="min-h-11 rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-base text-slate-900"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label htmlFor="preferred-language" className="text-sm font-semibold text-slate-900">
                Resource Language
              </label>
              <select
                id="preferred-language"
                name="preferred_language"
                value={preferredLanguage}
                onChange={(e) => setPreferredLanguage(e.target.value as SupportedLanguage)}
                className="min-h-11 rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-base text-slate-900"
              >
                <option value="en">English (en)</option>
                <option value="tr">Turkish (tr)</option>
              </select>
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="learning-goal" className="text-sm font-semibold text-slate-900">
              Select Your Learning Goal
            </label>
            <select
              id="learning-goal"
              name="learning_goal"
              value={learningGoal}
              onChange={(e) => setLearningGoal(e.target.value)}
              className="min-h-12 rounded-xl border border-[#bdd6c6] bg-[#f6fbf8] px-3.5 py-2.5 text-base font-medium text-slate-900"
            >
              {GOAL_CHOICES.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
              {hasCustomGoal ? <option value={learningGoal}>{learningGoal}</option> : null}
            </select>
          </div>

          <RadioCardGroup
            legend="Current Experience Level"
            name="experience_level"
            options={EXPERIENCE_OPTIONS}
            value={experienceLevel}
            onChange={setExperienceLevel}
          />

          <CheckboxGroup
            legend="Preferred Resource Types"
            hint="Select one or more formats to prioritize in your recommendations."
            name="preferred_formats"
            options={FORMAT_OPTIONS}
            selectedValues={preferredFormats}
            onChange={(next) => {
              setPreferredFormats(next);
              if (next.length > 0) setFormatError(undefined);
            }}
            error={formatError}
          />

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-5">
            <Button
              type="submit"
              variant="ghost"
              size="md"
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
              <span>Save &amp; Start Placement Test</span>
              <ArrowRight aria-hidden="true" className="h-4 w-4" />
            </Button>
          </div>
        </form>
      </Card>

      <p className="mt-4 text-center text-xs text-slate-500">
        You can update your learning goals and preferred formats anytime from your workspace.
      </p>
    </AppLayout>
  );
}
