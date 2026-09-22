import { useEffect, useState } from 'react'
import { Route, Routes } from 'react-router'

import { fetchCurrentUser, logout, type CurrentUser } from './api'
import { LoginForm } from './LoginForm'
import { AppShell } from './components/AppShell'
import { ClassesPage } from './pages/ClassesPage'
import { DailyPage } from './pages/DailyPage'
import { DashboardPage } from './pages/DashboardPage'
import { MessagesPage } from './pages/MessagesPage'
import { StudentsPage } from './pages/StudentsPage'

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

  return (
    <AppShell
      userName={user.display_name}
      userRole={user.role}
      onLogout={() => {
        void logout().then(() => setUser(null))
      }}
    >
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/daily" element={<DailyPage />} />
        <Route path="/messages" element={<MessagesPage />} />
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
