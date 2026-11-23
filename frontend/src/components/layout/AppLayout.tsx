import type { ReactNode } from 'react';
import { Link, NavLink } from 'react-router-dom';
import {
  Bookmark,
  BookOpen,
  Compass,
  GraduationCap,
  LayoutDashboard,
  LogOut,
  Shield,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { Badge, Button, cn } from '../ui';

interface AppLayoutProps {
  pageTitle: string;
  pageSubtitle?: string;
  children: ReactNode;
}

export function AppLayout({ pageTitle, pageSubtitle, children }: AppLayoutProps) {
  const { user, logout } = useAuth();

  const studentLinks = [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/roadmap', label: 'Learning Roadmap', icon: Compass },
    { to: '/recommendations', label: 'Recommendations', icon: BookOpen },
    { to: '/bookmarks', label: 'Saved & Library', icon: Bookmark },
    { to: '/assessment', label: 'Placement & Quizzes', icon: GraduationCap },
  ];

  const adminLinks = [
    { to: '/admin/resources', label: 'Resources Catalog', icon: BookOpen },
    { to: '/admin/topics-questions', label: 'DAG & Questions', icon: Shield },
  ];

  const navItems = user?.role === 'ADMIN' ? adminLinks : studentLinks;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <a
        href="#main-heading"
        className="visually-hidden fixed left-4 top-4 z-50 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-lg"
      >
        Skip to main content
      </a>

      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-3.5 sm:px-6">
          <div className="flex items-center gap-6">
            <Link
              to={user?.role === 'ADMIN' ? '/admin/resources' : '/dashboard'}
              className="flex items-center gap-2 text-lg font-bold tracking-tight text-slate-900"
            >
              <GraduationCap aria-hidden="true" className="h-6 w-6 text-blue-600" />
              <span>LearnPath</span>
            </Link>

            <nav aria-label="Primary" className="flex flex-wrap items-center gap-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) =>
                      cn(
                        'inline-flex min-h-10 items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                        isActive
                          ? 'bg-blue-50 text-blue-700'
                          : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
                      )
                    }
                  >
                    <Icon aria-hidden="true" className="h-4 w-4" />
                    {item.label}
                  </NavLink>
                );
              })}
            </nav>
          </div>

          {user ? (
            <div className="flex items-center gap-3">
              <Badge tone={user.role === 'ADMIN' ? 'warning' : 'info'}>{user.role}</Badge>
              {user.role === 'STUDENT' ? (
                <Link
                  to="/profile/setup"
                  className="text-sm font-medium text-slate-600 hover:text-slate-900"
                >
                  Profile
                </Link>
              ) : null}
              <Button variant="outline" size="sm" onClick={logout}>
                <LogOut aria-hidden="true" className="h-4 w-4" />
                Sign out
              </Button>
            </div>
          ) : null}
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <div className="mb-6">
          <h1 id="main-heading" tabIndex={-1} className="text-2xl font-bold text-slate-900">
            {pageTitle}
          </h1>
          {pageSubtitle ? <p className="mt-1 text-sm text-slate-600">{pageSubtitle}</p> : null}
        </div>
        {children}
      </main>
    </div>
  );
}
