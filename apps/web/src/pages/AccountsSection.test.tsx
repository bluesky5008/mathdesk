import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'

import type { AppUserAccount } from '../api'
import { AccountsSection } from './AccountsSection'

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

const USERS: AppUserAccount[] = [
  { id: 1, login_id: 'director', display_name: '원장', role: 'director', is_active: true },
  { id: 2, login_id: 'kim', display_name: '김강사', role: 'teacher', is_active: true },
  { id: 3, login_id: 'lee', display_name: '이강사', role: 'teacher', is_active: false },
]

type Call = { url: string; method: string; body: unknown }

function mount(reply?: (url: string, method: string) => Response | undefined) {
  const calls: Call[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? 'GET'
      const body = init?.body ? JSON.parse(String(init.body)) : undefined
      if (method !== 'GET') calls.push({ url, method, body })
      const custom = reply?.(url, method)
      if (custom) return custom
      if (method === 'GET') return Response.json(USERS)
      if (url.endsWith('/password')) return new Response(null, { status: 204 })
      return Response.json({ ...USERS[1], ...body })
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <AccountsSection currentUserId={1} />
    </QueryClientProvider>,
  )
  return calls
}

// FR-02 — 원장의 계정 관리
it('계정 목록을 역할·상태와 함께 보여 준다', async () => {
  mount()

  const row = (await screen.findByText('김강사')).closest('tr')!
  expect(within(row).getByText('kim')).toBeInTheDocument()
  expect(within(row).getByText('강사')).toBeInTheDocument()
  expect(within(screen.getByText('이강사').closest('tr')!).getByText('사용 안 함')).toBeInTheDocument()
})

it('새 계정을 만든다', async () => {
  const calls = mount()
  await screen.findByText('김강사')

  await userEvent.click(screen.getByRole('button', { name: '계정 추가' }))
  const dialog = screen.getByRole('dialog')
  await userEvent.type(within(dialog).getByLabelText('아이디'), 'park')
  await userEvent.type(within(dialog).getByLabelText('이름'), '박강사')
  await userEvent.type(within(dialog).getByLabelText('임시 비밀번호'), 'temporary-pw')
  await userEvent.click(within(dialog).getByRole('button', { name: '저장' }))

  expect(calls).toEqual([
    {
      url: '/api/users',
      method: 'POST',
      body: { login_id: 'park', display_name: '박강사', role: 'teacher', password: 'temporary-pw' },
    },
  ])
})

it('이름·역할·사용 여부를 고친다', async () => {
  const calls = mount()
  await screen.findByText('김강사')

  await userEvent.click(screen.getByRole('button', { name: '김강사 수정' }))
  const dialog = screen.getByRole('dialog')
  await userEvent.clear(within(dialog).getByLabelText('이름'))
  await userEvent.type(within(dialog).getByLabelText('이름'), '김선생')
  await userEvent.click(within(dialog).getByLabelText('사용'))
  await userEvent.click(within(dialog).getByRole('button', { name: '저장' }))

  expect(calls).toEqual([
    {
      url: '/api/users/2',
      method: 'PATCH',
      body: { display_name: '김선생', role: 'teacher', is_active: false },
    },
  ])
})

it('마지막 원장을 바꾸지 못하면 서버 메시지를 보여 준다', async () => {
  mount((url, method) =>
    method === 'PATCH'
      ? Response.json({ detail: '원장 계정이 최소 한 개는 있어야 합니다.' }, { status: 409 })
      : undefined,
  )
  await screen.findByText('김강사')

  await userEvent.click(screen.getByRole('button', { name: '원장 수정' }))
  const dialog = screen.getByRole('dialog')
  await userEvent.selectOptions(within(dialog).getByLabelText('역할'), 'teacher')
  await userEvent.click(within(dialog).getByRole('button', { name: '저장' }))

  expect(await within(dialog).findByRole('alert')).toHaveTextContent('최소 한 개')
})

// AC-39 ② — 원장의 비밀번호 재설정
it('임시 비밀번호로 재설정한다', async () => {
  const calls = mount()
  await screen.findByText('김강사')

  await userEvent.click(screen.getByRole('button', { name: '김강사 비밀번호 재설정' }))
  const dialog = screen.getByRole('dialog')
  expect(dialog).toHaveTextContent('기존 로그인은 모두 끊기고')
  await userEvent.type(within(dialog).getByLabelText('임시 비밀번호'), 'temporary-pw')
  await userEvent.click(within(dialog).getByRole('button', { name: '재설정' }))

  expect(calls).toEqual([
    { url: '/api/users/2/password', method: 'POST', body: { new_password: 'temporary-pw' } },
  ])
  expect(await screen.findByRole('status')).toHaveTextContent('김강사')
})

it('본인 계정에는 재설정 버튼이 없다', async () => {
  mount()
  await screen.findByText('김강사')

  expect(screen.queryByRole('button', { name: '원장 비밀번호 재설정' })).not.toBeInTheDocument()
})
