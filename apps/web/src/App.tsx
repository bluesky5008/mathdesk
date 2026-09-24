import { Suspense, lazy, useEffect, useState } from 'react'
import { Route, Routes } from 'react-router'

import { fetchCurrentUser, logout, type CurrentUser } from './api'
import { LoginForm } from './LoginForm'
import { ForcedPasswordChange } from './PasswordChange'
import { AppShell } from './components/AppShell'
import { ClassesPage } from './pages/ClassesPage'
import { DailyPage } from './pages/DailyPage'
import { DashboardPage } from './pages/DashboardPage'
import { ExamsPage } from './pages/ExamsPage'
import { MessagesPage } from './pages/MessagesPage'
import { SettingsPage } from './pages/SettingsPage'
import { StudentsPage } from './pages/StudentsPage'

// 통계 화면만 차트 라이브러리를 쓴다. 같이 묶으면 모든 화면의 첫 로딩이 두 배로 무거워진다.
const StatsPage = lazy(() => import('./pages/StatsPage').then((m) => ({ default: m.StatsPage })))

export function App() {
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [checked, setChecked] = useState(false)

  useEffect(() => {
    fetchCurrentUser()
      .then(setUser)
      .finally(() => setChecked(true))
  }, [])

  if (!checked) {
    return <p className="p-6 text-sm text-muted-fg">확인 중</p>
  }
  if (!user) {
    return <LoginForm onLoggedIn={setUser} />
  }

  const signOut = () => {
    void logout().then(() => setUser(null))
  }

  if (user.must_change_password) {
    return (
      <ForcedPasswordChange
        onDone={() => void fetchCurrentUser().then(setUser)}
        onLogout={signOut}
      />
    )
  }

  return (
    <AppShell userName={user.display_name} userRole={user.role} onLogout={signOut}>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/daily" element={<DailyPage />} />
        <Route
          path="/stats"
          element={
            <Suspense fallback={<p className="p-6 text-sm text-muted-fg">불러오는 중</p>}>
              <StatsPage />
            </Suspense>
          }
        />
        <Route path="/exams" element={<ExamsPage />} />
        <Route path="/messages" element={<MessagesPage />} />
        <Route
          path="/settings"
          element={
            <SettingsPage
              account={user.role === 'director' ? { currentUserId: user.id } : undefined}
            />
          }
        />
        <Route
          path="/students"
          element={
            <>
              <StudentsPage />
              <ClassesPage />
            </>
          }
        />
      </Routes>
    </AppShell>
  )
}
