import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { afterEach, expect, it, vi } from 'vitest'

import { App } from './App'
import { PasswordChangeForm } from './PasswordChange'

afterEach(() => {
  vi.unstubAllGlobals()
})

type Call = { url: string; method: string; body: unknown }

function stubFetch(handler: (url: string, method: string) => Response | undefined) {
  const calls: Call[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? 'GET'
      calls.push({ url, method, body: init?.body ? JSON.parse(String(init.body)) : undefined })
      return handler(url, method) ?? Response.json([])
    }),
  )
  return calls
}

async function fill(current: string, next: string, confirm = next) {
  await userEvent.type(screen.getByLabelText('현재 비밀번호'), current)
  await userEvent.type(screen.getByLabelText('새 비밀번호'), next)
  await userEvent.type(screen.getByLabelText('새 비밀번호 확인'), confirm)
}

// AC-39 ① — 본인 변경
it('현재 비밀번호와 새 비밀번호를 보낸다', async () => {
  const calls = stubFetch(() => new Response(null, { status: 204 }))
  const done = vi.fn()
  render(<PasswordChangeForm onDone={done} />)

  await fill('old-password', 'brand-new-pw')
  await userEvent.click(screen.getByRole('button', { name: '비밀번호 변경' }))

  expect(calls).toEqual([
    {
      url: '/api/auth/password',
      method: 'POST',
      body: { current_password: 'old-password', new_password: 'brand-new-pw' },
    },
  ])
  expect(done).toHaveBeenCalled()
})

it('새 비밀번호 확인이 다르면 보내지 않는다', async () => {
  const calls = stubFetch(() => undefined)
  render(<PasswordChangeForm onDone={vi.fn()} />)

  await fill('old-password', 'brand-new-pw', 'brand-new-pX')
  await userEvent.click(screen.getByRole('button', { name: '비밀번호 변경' }))

  expect(calls).toHaveLength(0)
  expect(screen.getByRole('alert')).toHaveTextContent('일치하지 않습니다')
})

it('현재 비밀번호가 틀리면 서버 메시지를 보여 준다', async () => {
  stubFetch(() => Response.json({ detail: '현재 비밀번호가 올바르지 않습니다.' }, { status: 400 }))
  const done = vi.fn()
  render(<PasswordChangeForm onDone={done} />)

  await fill('wrong-password', 'brand-new-pw')
  await userEvent.click(screen.getByRole('button', { name: '비밀번호 변경' }))

  expect(await screen.findByRole('alert')).toHaveTextContent('현재 비밀번호가 올바르지 않습니다')
  expect(done).not.toHaveBeenCalled()
})

function mountApp() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

// AC-39 ②③ — 원장이 정한 비밀번호로 들어오면 새 비밀번호를 정하기 전에는 앱을 쓸 수 없다
it('변경이 강제된 사용자는 새 비밀번호를 정한 뒤에야 메뉴를 본다', async () => {
  let forced = true
  stubFetch((url, method) => {
    if (url === '/api/auth/me') {
      return Response.json({
        id: 2,
        login_id: 'teacher',
        display_name: '김강사',
        role: 'teacher',
        must_change_password: forced,
      })
    }
    if (url === '/api/auth/password' && method === 'POST') {
      forced = false
      return new Response(null, { status: 204 })
    }
    return undefined
  })
  mountApp()

  expect(await screen.findByRole('heading', { name: '새 비밀번호 설정' })).toBeInTheDocument()
  expect(screen.queryByRole('link', { name: '종합 대시보드' })).not.toBeInTheDocument()

  await fill('temporary-pw', 'brand-new-pw')
  await userEvent.click(screen.getByRole('button', { name: '비밀번호 변경' }))

  expect(await screen.findByRole('link', { name: '종합 대시보드' })).toBeInTheDocument()
})

it('상단의 비밀번호 변경 버튼으로 언제든 바꿀 수 있다', async () => {
  const calls = stubFetch((url) => {
    if (url === '/api/auth/me') {
      return Response.json({
        id: 1,
        login_id: 'director',
        display_name: '원장',
        role: 'director',
        must_change_password: false,
      })
    }
    if (url === '/api/auth/password') return new Response(null, { status: 204 })
    return undefined
  })
  mountApp()

  await userEvent.click(await screen.findByRole('button', { name: '비밀번호 변경' }))
  await fill('old-password', 'brand-new-pw')
  await userEvent.click(
    within(screen.getByRole('dialog')).getByRole('button', { name: '비밀번호 변경' }),
  )

  expect(calls.some((call) => call.url === '/api/auth/password' && call.method === 'POST')).toBe(true)
  expect(await screen.findByRole('status')).toHaveTextContent('비밀번호를 바꿨습니다')
})
