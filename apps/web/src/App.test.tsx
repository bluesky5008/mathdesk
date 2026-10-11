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

function mountApp(handler: (url: string, method: string) => Response, path = '/') {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => handler(url, init?.method ?? 'GET')),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
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

// 2026-09-25 사용자 요청: 학생/반 관리를 [학생]·[반] 하위 탭으로 나누고 탭마다 주소를 둔다
function signedIn(url: string) {
  return url === '/api/auth/me' ? Response.json(DIRECTOR) : Response.json([])
}

it('shows only the student tab at /students with the top menu selected', async () => {
  mountApp(signedIn, '/students')

  expect(await screen.findByRole('heading', { name: '학생 관리' })).toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: '반 관리' })).not.toBeInTheDocument()
  expect(screen.getByRole('link', { name: '학생' })).toHaveAttribute('aria-current', 'page')
  expect(screen.getByRole('link', { name: '학생/반 관리' })).toHaveAttribute('aria-current', 'page')
})

it('shows only the class tab at its own address with the top menu still selected', async () => {
  mountApp(signedIn, '/students/classes')

  expect(await screen.findByRole('heading', { name: '반 관리' })).toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: '학생 관리' })).not.toBeInTheDocument()
  expect(screen.getByRole('link', { name: '반' })).toHaveAttribute('aria-current', 'page')
  expect(screen.getByRole('link', { name: '학생' })).not.toHaveAttribute('aria-current')
  expect(screen.getByRole('link', { name: '학생/반 관리' })).toHaveAttribute('aria-current', 'page')
})

it('switches between the student and class tabs', async () => {
  mountApp(signedIn, '/students')

  await userEvent.click(await screen.findByRole('link', { name: '반' }))
  expect(await screen.findByRole('heading', { name: '반 관리' })).toBeInTheDocument()

  await userEvent.click(screen.getByRole('link', { name: '학생' }))
  expect(await screen.findByRole('heading', { name: '학생 관리' })).toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: '반 관리' })).not.toBeInTheDocument()
})

// TASK-83: 학교 탭은 원장에게만 보인다(DCR-015)
it('shows the school tab to directors at its own address', async () => {
  mountApp(signedIn, '/students/schools')

  expect(await screen.findByRole('heading', { name: '학교 관리' })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: '학교' })).toHaveAttribute('aria-current', 'page')
})

it('hides the school tab from teachers', async () => {
  const teacher = { ...DIRECTOR, id: 2, login_id: 'teacher', role: 'teacher' }
  mountApp((url) => (url === '/api/auth/me' ? Response.json(teacher) : Response.json([])), '/students')

  expect(await screen.findByRole('link', { name: '반' })).toBeInTheDocument()
  expect(screen.queryByRole('link', { name: '학교' })).not.toBeInTheDocument()
})

// TASK-93: 학생·학부모 계정은 원장·강사 셸이 아니라 포털 셸을 본다(FR-49, DCR-024)
it('opens the portal shell for a portal account', async () => {
  const guardian = { ...DIRECTOR, id: 9, login_id: '01098765432', display_name: '김나윤 학부모', role: 'guardian' }
  mountApp((url) => {
    if (url === '/api/auth/me') return Response.json(guardian)
    if (url === '/api/portal/students') return Response.json([{ id: 1, name: '김나윤', grade: '고2', status: 'enrolled', classes: [] }])
    return Response.json([])
  })

  expect(await screen.findByRole('heading', { name: '김나윤' })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: '기록' })).toBeInTheDocument()
  expect(screen.queryByRole('link', { name: '종합 대시보드' })).not.toBeInTheDocument()
})
