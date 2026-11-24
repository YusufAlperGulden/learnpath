import { useEffect, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, EyeOff } from 'lucide-react';
import { apiClient, extractApiErrorMessage } from '../../api/client';
import { BrandLogo } from '../../components/layout/AppLayout';
import { Button, Card, cn } from '../../components/ui';
import { useAuth } from '../../context/AuthContext';
import type { TokenResponse } from '../../types/api';

export function AuthPage() {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [fullName, setFullName] = useState('');
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
      const trimmedName = fullName.trim();
      const { data } = await apiClient.post<TokenResponse>(
        endpoint,
        mode === 'register' && trimmedName
          ? { email, password, display_name: trimmedName }
          : { email, password },
      );
      if (mode === 'register' && trimmedName) {
        window.sessionStorage.setItem('learnpath_pending_display_name', trimmedName);
      }
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
    <div className="flex min-h-screen flex-col bg-[#e6efea] text-slate-900">
      {/* Top White Brand Header (Figma Screen 1) */}
      <header className="border-b border-[#d6e3dc] bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3.5 sm:px-6">
          <BrandLogo to="/auth" />
          <div className="flex items-center gap-2">
            <button
              type="button"
              aria-pressed={mode === 'login'}
              onClick={() => {
                setMode('login');
                setErrorMessage(null);
              }}
              className={cn(
                'min-h-9 rounded-full px-4 py-1.5 text-xs font-semibold transition-colors',
                mode === 'login'
                  ? 'bg-[#14532d] text-white shadow-xs'
                  : 'border border-slate-300 bg-white text-slate-700 hover:bg-[#f3f8f5]',
              )}
            >
              Sign in
            </button>
            <button
              type="button"
              aria-pressed={mode === 'register'}
              onClick={() => {
                setMode('register');
                setErrorMessage(null);
              }}
              className={cn(
                'min-h-9 rounded-full px-4 py-1.5 text-xs font-semibold transition-colors',
                mode === 'register'
                  ? 'bg-[#14532d] text-white shadow-xs'
                  : 'border border-slate-300 bg-white text-slate-700 hover:bg-[#f3f8f5]',
              )}
            >
              Register
            </button>
          </div>
        </div>
      </header>

      {/* Sage-Mint Centered Canvas */}
      <main className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center px-4 py-12">
        <div className="mb-7 text-center">
          <h1 className="text-4xl font-extrabold tracking-tight text-[#14532d]">Learn Path</h1>
          <p className="mt-1.5 text-base font-medium text-slate-700">Your Learning Guide.</p>
        </div>

        <Card className="mx-auto w-full max-w-[380px] rounded-2xl border-[#d3e2da] p-6 shadow-md">
          <h2 className="mb-4 text-sm font-bold text-slate-900">
            {mode === 'login' ? 'Sign in to your account' : 'Create your account'}
          </h2>

          <form method="post" action="/api/v1/auth" onSubmit={handleSubmit} className="space-y-4">
            {errorMessage ? (
              <div
                role="alert"
                className="rounded-lg border border-red-200 bg-red-50 px-3.5 py-2.5 text-xs font-medium text-red-800"
              >
                {errorMessage}
              </div>
            ) : null}

            {mode === 'register' ? (
              <div className="flex flex-col gap-1">
                <label htmlFor="full-name" className="text-xs font-semibold text-slate-800">
                  Full Name
                </label>
                <input
                  id="full-name"
                  name="display_name"
                  type="text"
                  maxLength={120}
                  autoComplete="name"
                  enterKeyHint="next"
                  aria-invalid="false"
                  placeholder="Ada Lovelace"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="min-h-11 rounded-lg border border-slate-300 bg-white px-3 py-2 text-base text-slate-900 placeholder:text-slate-400"
                />
              </div>
            ) : null}

            <div className="flex flex-col gap-1">
              <label htmlFor="email" className="text-xs font-semibold text-slate-800">
                Email <span aria-hidden="true">*</span>
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
                placeholder="you@example.com"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (errorMessage) setErrorMessage(null);
                }}
                className="min-h-11 rounded-lg border border-slate-300 bg-white px-3 py-2 text-base text-slate-900 placeholder:text-slate-400"
              />
            </div>

            <div className="flex flex-col gap-1">
              <div className="flex items-center justify-between">
                <label htmlFor="password" className="text-xs font-semibold text-slate-800">
                  Password <span aria-hidden="true">*</span>
                </label>
                <button
                  type="button"
                  aria-pressed={showPassword}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  onClick={() => setShowPassword((prev) => !prev)}
                  className="inline-flex min-h-7 items-center gap-1 rounded px-1.5 text-[11px] font-medium text-slate-600 hover:bg-slate-100"
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
                className="min-h-11 rounded-lg border border-slate-300 bg-white px-3 py-2 text-base text-slate-900"
              />
              <span id="password-hint" className="text-[11px] text-slate-500">
                At least 8 characters.
              </span>
            </div>

            <Button type="submit" size="md" isLoading={isSubmitting} className="mt-2 w-full">
              {mode === 'login' ? 'Sign In' : 'Create Account'}
            </Button>
          </form>

          <div className="mt-4 border-t border-slate-100 pt-3.5 text-center text-xs text-slate-600">
            {mode === 'login' ? "Don't have an account yet? " : 'Already registered? '}
            <button
              type="button"
              onClick={() => {
                setMode((prev) => (prev === 'login' ? 'register' : 'login'));
                setErrorMessage(null);
              }}
              className="font-semibold text-[#14532d] hover:underline"
            >
              {mode === 'login' ? 'Create account' : 'Sign in'}
            </button>
          </div>
        </Card>
      </main>
    </div>
  );
}
