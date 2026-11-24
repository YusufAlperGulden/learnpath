import { useEffect, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, EyeOff, GraduationCap } from 'lucide-react';
import { apiClient, extractApiErrorMessage } from '../../api/client';
import { Button, Card } from '../../components/ui';
import { useAuth } from '../../context/AuthContext';
import type { TokenResponse } from '../../types/api';

export function AuthPage() {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { user, setSession } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!user) return;
    if (user.role === 'ADMIN') {
      navigate('/admin/resources', { replace: true });
    } else if (!user.has_profile) {
      navigate('/profile/setup', { replace: true });
    } else {
      navigate('/dashboard', { replace: true });
    }
  }, [user, navigate]);

  useEffect(() => {
    document.title = mode === 'login' ? 'Sign In | LearnPath' : 'Create Account | LearnPath';
  }, [mode]);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      const endpoint = mode === 'register' ? '/auth/register' : '/auth/login';
      const { data } = await apiClient.post<TokenResponse>(endpoint, {
        email,
        password,
      });
      setSession(data);
      if (data.user.role === 'ADMIN') {
        navigate('/admin/resources', { replace: true });
      } else if (!data.user.has_profile) {
        navigate('/profile/setup', { replace: true });
      } else {
        navigate('/dashboard', { replace: true });
      }
    } catch (err: unknown) {
      setErrorMessage(
        extractApiErrorMessage(
          err,
          'Unable to complete authentication. Please verify your credentials and backend connection.',
        ),
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col justify-center bg-slate-50 px-4 py-12">
      <main className="mx-auto w-full max-w-md">
        <div className="mb-6 flex flex-col items-center text-center">
          <GraduationCap aria-hidden="true" className="h-10 w-10 text-blue-600" />
          <h1 className="mt-3 text-2xl font-bold text-slate-900">
            {mode === 'login' ? 'Sign in to LearnPath' : 'Create your LearnPath account'}
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Personalized Python curriculum &amp; explainable resource recommendations
          </p>
        </div>

        <Card>
          <form method="post" action="/api/v1/auth" onSubmit={handleSubmit} className="space-y-5">
            {errorMessage ? (
              <div
                role="alert"
                className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
              >
                {errorMessage}
              </div>
            ) : null}

            <div className="flex flex-col gap-1.5">
              <label htmlFor="email" className="text-sm font-medium text-slate-900">
                Email address <span aria-hidden="true">*</span>
              </label>
              <input
                id="email"
                name="email"
                type="email"
                required
                autoComplete="username"
                autoCorrect="off"
                autoCapitalize="none"
                spellCheck={false}
                enterKeyHint="next"
                aria-invalid={errorMessage ? 'true' : 'false'}
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (errorMessage) setErrorMessage(null);
                }}
                className="min-h-12 rounded-lg border border-slate-400 px-3.5 py-2.5 text-base text-slate-900"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <div className="flex items-center justify-between">
                <label htmlFor="password" className="text-sm font-medium text-slate-900">
                  Password <span aria-hidden="true">*</span>
                </label>
                <button
                  type="button"
                  aria-pressed={showPassword}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  onClick={() => setShowPassword((prev) => !prev)}
                  className="inline-flex min-h-8 items-center gap-1 rounded px-2 text-xs font-medium text-slate-700 hover:bg-slate-100"
                >
                  {showPassword ? (
                    <>
                      <EyeOff aria-hidden="true" className="h-3.5 w-3.5" />
                      Hide
                    </>
                  ) : (
                    <>
                      <Eye aria-hidden="true" className="h-3.5 w-3.5" />
                      Show
                    </>
                  )}
                </button>
              </div>
              <span id="password-hint" className="text-xs text-slate-600">
                At least 8 characters.
              </span>
              <input
                id="password"
                name="password"
                type={showPassword ? 'text' : 'password'}
                required
                minLength={8}
                autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
                aria-describedby="password-hint"
                aria-invalid={errorMessage ? 'true' : 'false'}
                enterKeyHint="done"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (errorMessage) setErrorMessage(null);
                }}
                className="min-h-12 rounded-lg border border-slate-400 px-3.5 py-2.5 text-base text-slate-900"
              />
            </div>

            <Button type="submit" size="lg" isLoading={isSubmitting} className="w-full">
              {mode === 'login' ? 'Sign in' : 'Create account'}
            </Button>
          </form>

          <div className="mt-6 border-t border-slate-100 pt-4 text-center text-sm text-slate-600">
            {mode === 'login' ? "Don't have an account yet? " : 'Already registered? '}
            <button
              type="button"
              onClick={() => {
                setMode((prev) => (prev === 'login' ? 'register' : 'login'));
                setErrorMessage(null);
              }}
              className="font-semibold text-blue-600 hover:underline"
            >
              {mode === 'login' ? 'Create account' : 'Sign in'}
            </button>
          </div>
        </Card>
      </main>
    </div>
  );
}
