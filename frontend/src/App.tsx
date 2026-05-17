import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './hooks/useAuth'
import DashboardLayout from './components/layout/DashboardLayout'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import BookDetailPage from './pages/BookDetailPage'
import ComparisonPage from './pages/ComparisonPage'
import SearchPage from './pages/SearchPage'
import DigestPage from './pages/DigestPage'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="flex h-screen items-center justify-center">Loading...</div>
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <DashboardLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="books/:bookId" element={<BookDetailPage />} />
        <Route path="compare" element={<ComparisonPage />} />
        <Route path="search" element={<SearchPage />} />
        <Route path="digest" element={<DigestPage />} />
      </Route>
    </Routes>
  )
}
