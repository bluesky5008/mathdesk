import { useEffect, useState } from 'react'
import { Link, Route, Routes } from 'react-router'

import { fetchCurrentUser, logout, type CurrentUser } from './api'
import { LoginForm } from './LoginForm'
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
          <Link to="/">종합 대시보드</Link>
          <Link to="/daily">일일 수업 &amp; 성적 입력</Link>
          <Link to="/students">학생/반 관리</Link>
          <Link to="/messages">알림문자</Link>
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
      </main>
    </div>
  )
}
