import { useState, type FormEvent } from 'react'

import { login, type CurrentUser } from './api'

export function LoginForm({ onLoggedIn }: { onLoggedIn: (user: CurrentUser) => void }) {
  const [loginId, setLoginId] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  async function submit(event: FormEvent) {
    event.preventDefault()
    setError('')
    try {
      onLoggedIn(await login(loginId, password))
    } catch (cause) {
      setError((cause as Error).message)
    }
  }

  return (
    <form onSubmit={submit}>
      <h1>mathdesk 로그인</h1>
      <label>
        아이디
        <input value={loginId} onChange={(event) => setLoginId(event.target.value)} />
      </label>
      <label>
        비밀번호
        <input
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
      </label>
      <button type="submit">로그인</button>
      {error && <p role="alert">{error}</p>}
    </form>
  )
}
