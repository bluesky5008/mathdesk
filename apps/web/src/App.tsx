import { useEffect, useState } from 'react'

import { fetchCurrentUser, logout, type CurrentUser } from './api'
import { LoginForm } from './LoginForm'

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
    <main>
      <h1>종합 대시보드</h1>
      <p>
        {user.display_name} ({user.role})
      </p>
      <button
        type="button"
        onClick={() => {
          void logout().then(() => setUser(null))
        }}
      >
        로그아웃
      </button>
    </main>
  )
}
