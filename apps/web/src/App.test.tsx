import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { afterEach, expect, it, vi } from 'vitest'

import { App } from './App'

afterEach(() => {
  vi.unstubAllGlobals()
})

const DIRECTOR = {
  id: 1,
  login_id: 'director',
  display_name: '원장',
  role: 'director',
  must_change_password: false,
}

function unauthorized() {
  return Response.json({ detail: '인증이 필요합니다.' }, { status: 401 })
}

function mountApp(handler: (url: string, method: string) => Response) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => handler(url, init?.method ?? 'GET')),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

// 2026-09-24 테스트 운영 재현: 사용 중 로그인이 끊기자 화면은 그대로 남고 "인증이 필요합니다"만 보였다
it('returns to the login screen with a notice when the session expires mid-use', async () => {
  mountApp((url) => (url === '/api/auth/me' ? Response.json(DIRECTOR) : unauthorized()))

  expect(await screen.findByRole('heading', { name: 'mathdesk 로그인' })).toBeInTheDocument()
  expect(screen.getByRole('status')).toHaveTextContent('로그인이 만료되었습니다. 다시 로그인해 주세요.')
})

it('shows the plain login screen when nobody is signed in', async () => {
  mountApp(() => unauthorized())

  expect(await screen.findByRole('heading', { name: 'mathdesk 로그인' })).toBeInTheDocument()
  expect(screen.queryByRole('status')).not.toBeInTheDocument()
})

it('keeps the wrong-password message on the login screen', async () => {
  mountApp((url) =>
    url === '/api/auth/login'
      ? Response.json({ detail: '자격 증명이 올바르지 않습니다.' }, { status: 401 })
      : unauthorized(),
  )

  await screen.findByRole('heading', { name: 'mathdesk 로그인' })
  await userEvent.type(screen.getByLabelText('아이디'), 'director')
  await userEvent.type(screen.getByLabelText('비밀번호'), 'wrong-password')
  await userEvent.click(screen.getByRole('button', { name: '로그인' }))

  expect(await screen.findByRole('alert')).toHaveTextContent('자격 증명이 올바르지 않습니다')
  expect(screen.queryByRole('status')).not.toBeInTheDocument()
})
