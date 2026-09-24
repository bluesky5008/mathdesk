import { useState, type FormEvent } from 'react'

import { login, type CurrentUser } from './api'
import { Button } from './components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/card'
import { Input } from './components/ui/input'

export function LoginForm({
  onLoggedIn,
  notice,
}: {
  onLoggedIn: (user: CurrentUser) => void
  notice?: string
}) {
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
    <div className="flex min-h-screen items-center justify-center bg-bg px-6">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle as="h1">mathdesk 로그인</CardTitle>
        </CardHeader>
        <CardContent>
          {notice && (
            <p role="status" className="mb-4 rounded-md bg-warning px-3 py-2 text-sm text-warning-fg">
              {notice}
            </p>
          )}
          <form className="flex flex-col gap-4" onSubmit={submit}>
            <label className="flex flex-col gap-1.5 text-sm font-medium">
              아이디
              <Input value={loginId} onChange={(event) => setLoginId(event.target.value)} />
            </label>
            <label className="flex flex-col gap-1.5 text-sm font-medium">
              비밀번호
              <Input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </label>
            <Button type="submit" size="lg">
              로그인
            </Button>
            {error && (
              <p role="alert" className="text-sm text-danger">
                {error}
              </p>
            )}
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
