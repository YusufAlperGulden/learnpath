import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/layout/ProtectedRoute';
import { AuthPage } from './pages/student/AuthPage';
import { ProfileSetupPage } from './pages/student/ProfileSetupPage';
import { DashboardPage } from './pages/student/DashboardPage';
import { RoadmapPage } from './pages/student/RoadmapPage';
import { RecommendationsPage } from './pages/student/RecommendationsPage';
import { BookmarksPage } from './pages/student/BookmarksPage';
import { PlacementTestPage } from './pages/assessment/PlacementTestPage';
import { AnswerReviewPage } from './pages/assessment/AnswerReviewPage';
import { ResourceManagerPage } from './pages/admin/ResourceManagerPage';
import { TopicQuestionManagerPage } from './pages/admin/TopicQuestionManagerPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/auth" element={<AuthPage />} />

            {/* Student Protected Routes */}
            <Route
              path="/profile/setup"
              element={
                <ProtectedRoute allowedRoles={['STUDENT']}>
                  <ProfileSetupPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute allowedRoles={['STUDENT']}>
                  <DashboardPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/roadmap"
              element={
                <ProtectedRoute allowedRoles={['STUDENT']}>
                  <RoadmapPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/recommendations"
              element={
                <ProtectedRoute allowedRoles={['STUDENT']}>
                  <RecommendationsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/bookmarks"
              element={
                <ProtectedRoute allowedRoles={['STUDENT']}>
                  <BookmarksPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/assessment"
              element={
                <ProtectedRoute allowedRoles={['STUDENT']}>
                  <PlacementTestPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/assessment/attempts/:attemptId"
              element={
                <ProtectedRoute allowedRoles={['STUDENT']}>
                  <AnswerReviewPage />
                </ProtectedRoute>
              }
            />

            {/* Admin Protected Routes */}
            <Route
              path="/admin/resources"
              element={
                <ProtectedRoute allowedRoles={['ADMIN']}>
                  <ResourceManagerPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/topics-questions"
              element={
                <ProtectedRoute allowedRoles={['ADMIN']}>
                  <TopicQuestionManagerPage />
                </ProtectedRoute>
              }
            />

            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
