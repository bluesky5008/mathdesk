import { useEffect, useState } from 'react'
import { Link, Navigate, Route, Routes } from 'react-router'

import { fetchCurrentUser, logout, type CurrentUser } from './api'
import { LoginForm } from './LoginForm'
import { ClassesPage } from './pages/ClassesPage'
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
    return <p>확인 중</p>
  }
  if (!user) {
    return <LoginForm onLoggedIn={setUser} />
  }

  return (
    <div>
      <header>
        <strong>mathdesk</strong>
        <nav>
          <Link to="/students">학생/반 관리</Link>
        </nav>
        <span>
          {user.display_name} ({user.role})
        </span>
        <button
          type="button"
          onClick={() => {
            void logout().then(() => setUser(null))
          }}
        >
          로그아웃
        </button>
      </header>

      <main>
        <Routes>
          <Route path="/" element={<Navigate to="/students" replace />} />
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
      </main>
    </div>
  )
}
