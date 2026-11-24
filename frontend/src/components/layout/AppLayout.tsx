import { useState, type FormEvent, type ReactNode } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  Bookmark,
  BookOpen,
  Compass,
  FileQuestion,
  FolderKanban,
  GitBranch,
  GraduationCap,
  LayoutDashboard,
  LogOut,
  Menu,
  Search,
  Settings,
  Sparkles,
  X,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { Badge, Button } from '../ui';

export function BrandLogo({
  to,
  wordmark = 'LearnPath',
}: {
  to: string;
  wordmark?: string;
}) {
  return (
    <Link
      to={to}
      className="inline-flex items-center gap-2.5 text-lg font-bold tracking-tight text-slate-900"
    >
      <span
        aria-hidden="true"
        className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#14532d] text-white shadow-xs"
      >
        <BookOpen className="h-4 w-4" />
      </span>
      <span>{wordmark}</span>
    </Link>
  );
}

interface NavItemSpec {
  to: string;
  label: string;
  icon: typeof LayoutDashboard;
  isActive: (pathname: string, search: string) => boolean;
}

export interface AppLayoutProps {
  pageTitle: string;
  pageSubtitle?: string;
  eyebrow?: string;
  variant?: 'sidebar' | 'focused';
  contextPill?: string;
  showInlineNav?: boolean;
  headerActions?: ReactNode;
  hidePageHeader?: boolean;
  children: ReactNode;
}

export function AppLayout({
  pageTitle,
  pageSubtitle,
  eyebrow,
  variant = 'sidebar',
  contextPill,
  showInlineNav = false,
  headerActions,
  hidePageHeader = false,
  children,
}: AppLayoutProps) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [quickQuery, setQuickQuery] = useState('');

  const homePath = user?.role === 'ADMIN' ? '/admin/resources' : '/dashboard';

  const studentLinks: NavItemSpec[] = [
    {
      to: '/dashboard',
      label: 'Overview',
      icon: LayoutDashboard,
      isActive: (pathname) => pathname === '/dashboard',
    },
    {
      to: '/recommendations',
      label: 'Explore resources',
      icon: BookOpen,
      isActive: (pathname) => pathname === '/recommendations',
    },
    {
      to: '/bookmarks',
      label: 'My learning',
      icon: Bookmark,
      isActive: (pathname) => pathname === '/bookmarks',
    },
    {
      to: '/roadmap',
      label: 'Learning paths',
      icon: Compass,
      isActive: (pathname) => pathname === '/roadmap',
    },
    {
      to: '/assessment',
      label: 'Placement & quizzes',
      icon: GraduationCap,
      isActive: (pathname) => pathname.startsWith('/assessment'),
    },
  ];

  const adminLinks: NavItemSpec[] = [
    {
      to: '/admin/resources',
      label: 'Resource Management',
      icon: FolderKanban,
      isActive: (pathname) => pathname === '/admin/resources',
    },
    {
      to: '/admin/topics-questions?tab=questions',
      label: 'Question Pool',
      icon: FileQuestion,
      isActive: (pathname, search) => {
        if (pathname !== '/admin/topics-questions') return false;
        const params = new URLSearchParams(search);
        return params.get('tab') === 'questions';
      },
    },
    {
      to: '/admin/topics-questions?tab=dag',
      label: 'Topics & Prerequisites',
      icon: GitBranch,
      isActive: (pathname, search) => {
        if (pathname !== '/admin/topics-questions') return false;
        const params = new URLSearchParams(search);
        return params.get('tab') !== 'questions';
      },
    },
  ];

  const navItems = user?.role === 'ADMIN' ? adminLinks : studentLinks;
  const userHandle = user?.email ? user.email.split('@')[0] : 'Learner';
  const userInitial = userHandle.slice(0, 1).toUpperCase();

  const handleQuickSearch = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (user?.role === 'ADMIN') {
      navigate('/admin/resources');
    } else {
      navigate('/recommendations');
    }
  };

  if (variant === 'focused') {
    return (
      <div className="min-h-screen bg-[#f6f8f7] text-slate-900">
        <a
          href="#main-heading"
          className="visually-hidden fixed left-4 top-4 z-50 rounded-lg bg-[#14532d] px-4 py-2 text-sm font-semibold text-white shadow-lg"
        >
          Skip to main content
        </a>

        <header className="border-b border-[#e2eae5] bg-white">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-3.5 sm:px-6">
            <div className="flex items-center gap-3">
              <BrandLogo to={homePath} />
              {user?.role === 'ADMIN' ? <Badge tone="info">ADMIN</Badge> : null}
            </div>

            {contextPill ? (
              <div className="rounded-full border border-[#d0e1d6] bg-[#edf5f0] px-4 py-1.5 text-xs font-semibold text-[#14532d]">
                {contextPill}
              </div>
            ) : showInlineNav ? (
              <nav aria-label="Primary" className="hidden items-center gap-1 md:flex">
                {[
                  { to: '/dashboard', label: 'Overview', match: '/dashboard' },
                  { to: '/bookmarks', label: 'My learning', match: '/bookmarks' },
                  { to: '/roadmap', label: 'Learning path', match: '/roadmap' },
                  {
                    to: '/recommendations',
                    label: 'Placement results',
                    match: '/recommendations',
                  },
                ].map((item) => {
                  const active = location.pathname === item.match;
                  return (
                    <Link
                      key={item.to}
                      to={item.to}
                      aria-current={active ? 'page' : undefined}
                      className="lp-top-nav-link inline-flex min-h-9 items-center rounded-lg px-3 py-1.5 text-sm font-medium text-slate-600 transition-colors hover:bg-[#f2f7f4] hover:text-slate-900"
                    >
                      {item.label}
                    </Link>
                  );
                })}
              </nav>
            ) : null}

            {user ? (
              <div className="flex items-center gap-2.5">
                {user.role === 'STUDENT' && location.pathname !== '/dashboard' ? (
                  <Link
                    to="/dashboard"
                    className="hidden text-xs font-medium text-slate-600 hover:text-[#14532d] sm:inline"
                  >
                    Back to workspace
                  </Link>
                ) : null}
                <span
                  aria-hidden="true"
                  className="flex h-8 w-8 items-center justify-center rounded-full bg-[#e6f2eb] text-xs font-bold text-[#14532d]"
                >
                  {userInitial}
                </span>
                <Button variant="outline" size="sm" onClick={logout}>
                  <LogOut aria-hidden="true" className="h-3.5 w-3.5" />
                  <span className="hidden sm:inline">Sign out</span>
                </Button>
              </div>
            ) : null}
          </div>
        </header>

        <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
          {hidePageHeader ? (
            <h1 id="main-heading" tabIndex={-1} className="visually-hidden">
              {pageTitle}
            </h1>
          ) : (
            <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
              <div>
                {eyebrow ? (
                  <p className="text-[11px] font-bold uppercase tracking-widest text-[#14532d]">
                    {eyebrow}
                  </p>
                ) : null}
                <h1
                  id="main-heading"
                  tabIndex={-1}
                  className="mt-0.5 text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl"
                >
                  {pageTitle}
                </h1>
                {pageSubtitle ? (
                  <p className="mt-1 text-sm text-slate-600">{pageSubtitle}</p>
                ) : null}
              </div>
              {headerActions ? (
                <div className="flex flex-wrap items-center gap-2.5">{headerActions}</div>
              ) : null}
            </div>
          )}
          {children}
        </main>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-[#f6f8f7] text-slate-900">
      <a
        href="#main-heading"
        className="visually-hidden fixed left-4 top-4 z-50 rounded-lg bg-[#14532d] px-4 py-2 text-sm font-semibold text-white shadow-lg"
      >
        Skip to main content
      </a>

      {/* Desktop Left Workspace Sidebar (Figma Screens 2 & 7) */}
      <aside className="hidden w-60 shrink-0 flex-col justify-between border-r border-[#e2eae5] bg-white lg:flex">
        <div className="p-4">
          <div className="flex items-center justify-between gap-2 px-1 py-1">
            <BrandLogo to={homePath} />
            {user?.role === 'ADMIN' ? <Badge tone="info">ADMIN</Badge> : null}
          </div>

          <p className="mt-6 px-2.5 text-[10px] font-bold uppercase tracking-widest text-slate-400">
            Workspace
          </p>

          <nav aria-label="Primary" className="mt-2 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = item.isActive(location.pathname, location.search);
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  aria-current={active ? 'page' : undefined}
                  className="lp-sidebar-link flex min-h-10 items-center gap-2.5 rounded-r-lg px-3 py-2 text-sm font-medium text-slate-600 transition-colors hover:bg-[#f2f7f4] hover:text-slate-900"
                >
                  <Icon aria-hidden="true" className="h-4 w-4 shrink-0" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="space-y-3 border-t border-[#ebf1ed] p-4">
          {user?.role === 'STUDENT' ? (
            <div className="rounded-xl border border-[#d3e4d9] bg-[#eef6f1] p-3.5">
              <div className="flex items-center gap-1.5 text-xs font-bold text-[#14532d]">
                <Sparkles aria-hidden="true" className="h-3.5 w-3.5" />
                <span>A little every day.</span>
              </div>
              <p className="mt-1 text-[11px] leading-relaxed text-slate-600">
                Big things ahead. Follow your prerequisite-aware Python path.
              </p>
              <Link
                to="/roadmap"
                className="mt-2.5 inline-flex items-center rounded-md border border-[#14532d]/30 bg-white px-2.5 py-1 text-xs font-semibold text-[#14532d] hover:bg-[#e6f2eb]"
              >
                Find your path
              </Link>
            </div>
          ) : (
            <div className="rounded-xl border border-[#e2eae5] bg-[#f8faf9] p-3">
              <p className="text-xs font-semibold text-slate-800">Managing your library?</p>
              <p className="mt-0.5 text-[11px] text-slate-600">
                Keep topics, resources, and versioned questions aligned.
              </p>
            </div>
          )}

          <div className="space-y-1">
            {user?.role === 'STUDENT' ? (
              <Link
                to="/profile/setup"
                aria-current={location.pathname === '/profile/setup' ? 'page' : undefined}
                className="lp-sidebar-link flex min-h-9 items-center gap-2.5 rounded-r-lg px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-[#f2f7f4] hover:text-slate-900"
              >
                <Settings aria-hidden="true" className="h-3.5 w-3.5" />
                <span>Profile settings</span>
              </Link>
            ) : null}
            <button
              type="button"
              onClick={logout}
              className="flex min-h-9 w-full items-center gap-2.5 rounded-lg px-3 py-1.5 text-left text-xs font-medium text-slate-600 hover:bg-red-50 hover:text-red-700"
            >
              <LogOut aria-hidden="true" className="h-3.5 w-3.5" />
              <span>Sign out</span>
            </button>
          </div>
        </div>
      </aside>

      {/* Main Right Workspace Column */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="border-b border-[#e2eae5] bg-white">
          <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6 lg:px-8">
            <div className="flex items-center gap-3">
              <button
                type="button"
                aria-expanded={mobileMenuOpen}
                aria-controls="mobile-workspace-nav"
                onClick={() => setMobileMenuOpen((prev) => !prev)}
                className="inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 lg:hidden"
              >
                {mobileMenuOpen ? (
                  <X aria-hidden="true" className="h-4 w-4" />
                ) : (
                  <Menu aria-hidden="true" className="h-4 w-4" />
                )}
                <span>Menu</span>
              </button>

              <div className="lg:hidden">
                <BrandLogo to={homePath} />
              </div>

              <div className="hidden items-center gap-2 text-xs text-slate-500 lg:flex">
                <span className="font-medium text-slate-400">My workspace</span>
                <span aria-hidden="true">/</span>
                <span className="font-semibold text-slate-700">{pageTitle}</span>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {user?.role === 'STUDENT' ? (
                <search className="hidden sm:block">
                  <form onSubmit={handleQuickSearch} className="relative">
                    <label htmlFor="workspace-quick-search" className="visually-hidden">
                      Search topics or resources
                    </label>
                    <Search
                      aria-hidden="true"
                      className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400"
                    />
                    <input
                      id="workspace-quick-search"
                      name="q"
                      type="search"
                      value={quickQuery}
                      onChange={(e) => setQuickQuery(e.target.value)}
                      autoCorrect="off"
                      autoCapitalize="none"
                      spellCheck={false}
                      placeholder="Explore Python resources..."
                      className="h-9 w-56 rounded-full border border-[#dce6df] bg-[#f6f9f7] pl-8 pr-3 text-xs text-slate-800 placeholder:text-slate-400 focus:bg-white"
                    />
                  </form>
                </search>
              ) : null}

              {user ? (
                <div className="flex items-center gap-2">
                  <span
                    aria-hidden="true"
                    className="flex h-8 w-8 items-center justify-center rounded-full bg-[#14532d] text-xs font-bold text-white"
                  >
                    {userInitial}
                  </span>
                  <span className="hidden text-xs font-semibold text-slate-700 sm:inline">
                    {userHandle}
                  </span>
                </div>
              ) : null}
            </div>
          </div>

          {/* Collapsible Mobile Navigation */}
          <nav
            id="mobile-workspace-nav"
            aria-label="Mobile workspace"
            hidden={!mobileMenuOpen}
            className="border-t border-[#ebf1ed] bg-white px-4 py-3 lg:hidden"
          >
            <div className="space-y-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                const active = item.isActive(location.pathname, location.search);
                return (
                  <Link
                    key={item.to}
                    to={item.to}
                    onClick={() => setMobileMenuOpen(false)}
                    aria-current={active ? 'page' : undefined}
                    className="lp-sidebar-link flex min-h-10 items-center gap-2.5 rounded-r-lg px-3 py-2 text-sm font-medium text-slate-700"
                  >
                    <Icon aria-hidden="true" className="h-4 w-4 shrink-0" />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
              {user?.role === 'STUDENT' ? (
                <Link
                  to="/profile/setup"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex min-h-10 items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium text-slate-700"
                >
                  <Settings aria-hidden="true" className="h-4 w-4" />
                  <span>Profile settings</span>
                </Link>
              ) : null}
              <button
                type="button"
                onClick={logout}
                className="flex min-h-10 w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm font-medium text-red-700 hover:bg-red-50"
              >
                <LogOut aria-hidden="true" className="h-4 w-4" />
                <span>Sign out</span>
              </button>
            </div>
          </nav>
        </header>

        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6 lg:px-8">
          {hidePageHeader ? (
            <h1 id="main-heading" tabIndex={-1} className="visually-hidden">
              {pageTitle}
            </h1>
          ) : (
            <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
              <div>
                {eyebrow ? (
                  <p className="text-[11px] font-bold uppercase tracking-widest text-[#14532d]">
                    {eyebrow}
                  </p>
                ) : null}
                <h1
                  id="main-heading"
                  tabIndex={-1}
                  className="mt-0.5 text-2xl font-bold tracking-tight text-slate-900"
                >
                  {pageTitle}
                </h1>
                {pageSubtitle ? (
                  <p className="mt-1 text-sm text-slate-600">{pageSubtitle}</p>
                ) : null}
              </div>
              {headerActions ? (
                <div className="flex flex-wrap items-center gap-2.5">{headerActions}</div>
              ) : null}
            </div>
          )}
          {children}
        </main>
      </div>
    </div>
  );
}
