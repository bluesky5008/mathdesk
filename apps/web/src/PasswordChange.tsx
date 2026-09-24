import { useState, type FormEvent } from 'react'

import { changePassword } from './api'
import { Button } from './components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card'
import { Field } from './components/ui/field'
import { Input } from './components/ui/input'

export function PasswordChangeForm({ onDone }: { onDone: () => void }) {
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setError('')
    if (next !== confirm) {
      setError('새 비밀번호 확인이 일치하지 않습니다.')
      return
    }
    setPending(true)
    try {
      await changePassword(current, next)
      onDone()
    } catch (cause) {
      setError((cause as Error).message)
    } finally {
      setPending(false)
    }
  }

  return (
    <form className="flex flex-col gap-4" onSubmit={submit}>
      <Field label="현재 비밀번호" htmlFor="password-current">
        <Input
          id="password-current"
          type="password"
          autoComplete="current-password"
          value={current}
          onChange={(event) => setCurrent(event.target.value)}
        />
      </Field>
      <Field label="새 비밀번호" htmlFor="password-new">
        <Input
          id="password-new"
          type="password"
          autoComplete="new-password"
          minLength={8}
          maxLength={128}
          value={next}
          onChange={(event) => setNext(event.target.value)}
        />
      </Field>
      <Field label="새 비밀번호 확인" htmlFor="password-confirm">
        <Input
          id="password-confirm"
          type="password"
          autoComplete="new-password"
          value={confirm}
          onChange={(event) => setConfirm(event.target.value)}
        />
      </Field>
      <p className="text-xs text-muted-fg">8자 이상. 바꾸면 다른 기기의 로그인은 끊깁니다.</p>
      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}
      <Button type="submit" disabled={pending}>
        비밀번호 변경
      </Button>
    </form>
  )
}

// 원장이 정한 비밀번호(새 계정·재설정·최초 원장)로 들어온 사용자는 이 화면만 본다(DCR-009).
// 서버도 다른 요청을 403으로 막으므로 화면을 우회해도 쓸 수 없다.
export function ForcedPasswordChange({
  onDone,
  onLogout,
}: {
  onDone: () => void
  onLogout: () => void
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-bg px-6">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle as="h1">새 비밀번호 설정</CardTitle>
          <CardDescription>
            원장님이 정해 준 임시 비밀번호로 로그인했습니다. 계속하려면 본인만 아는 새 비밀번호를
            정해 주세요.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 pt-4">
          <PasswordChangeForm onDone={onDone} />
          <Button type="button" variant="ghost" onClick={onLogout}>
            로그아웃
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
