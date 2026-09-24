import { Suspense, lazy, useEffect, useState } from 'react'
import { Route, Routes } from 'react-router'

import { SESSION_EXPIRED_EVENT, fetchCurrentUser, logout, type CurrentUser } from './api'
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
import { TimetablePage } from './pages/TimetablePage'

// 통계 화면만 차트 라이브러리를 쓴다. 같이 묶으면 모든 화면의 첫 로딩이 두 배로 무거워진다.
const StatsPage = lazy(() => import('./pages/StatsPage').then((m) => ({ default: m.StatsPage })))

export function App() {
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [checked, setChecked] = useState(false)
  const [expired, setExpired] = useState(false)

  useEffect(() => {
    fetchCurrentUser()
      .then(setUser)
      .finally(() => setChecked(true))
  }, [])

  // 사용 중 로그인이 끊기면(유휴 12시간 등) 화면을 남겨 두지 않고 로그인 화면으로 돌아간다
  useEffect(() => {
    const onExpired = () => {
      setUser(null)
      setExpired(true)
    }
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired)
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired)
  }, [])

  if (!checked) {
    return <p className="p-6 text-sm text-muted-fg">확인 중</p>
  }
  if (!user) {
    return (
      <LoginForm
        notice={expired ? '로그인이 만료되었습니다. 다시 로그인해 주세요.' : undefined}
        onLoggedIn={(signedIn) => {
          setExpired(false)
          setUser(signedIn)
        }}
      />
    )
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
        <Route path="/timetable" element={<TimetablePage isDirector={user.role === 'director'} />} />
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
              <ClassesPage isDirector={user.role === 'director'} />
            </>
          }
        />
      </Routes>
    </AppShell>
  )
}
