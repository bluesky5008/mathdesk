import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Consult } from '../api'
import { today } from '../lib/date'
import { ConsultDialog } from './ConsultDialog'

function renderDialog() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <ConsultDialog student={{ id: 3, name: '김나윤' }} onClose={() => {}} />
    </QueryClientProvider>,
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
})

const existing: Consult = {
  id: 21,
  student_id: 3,
  consulted_on: '2026-09-20',
  content: '모의고사 결과 상담',
  follow_up: '오답 노트 확인',
  author: { id: 1, name: '원장' },
}

type Call = { url: string; method: string; body: unknown }

function stub(calls: Call[]) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? 'GET'
      calls.push({ url, method, body: init?.body ? JSON.parse(String(init.body)) : null })
      if (method === 'POST') return Response.json({ ...existing, id: 22 }, { status: 201 })
      if (method === 'PATCH') return Response.json(existing)
      return Response.json([existing])
    }),
  )
}

describe('ConsultDialog', () => {
  it('lists the student consults with follow-ups and authors', async () => {
    stub([])
    renderDialog()

    const dialog = await screen.findByRole('dialog', { name: '김나윤 상담일지' })
    const entry = await within(dialog).findByRole('article', { name: '2026-09-20 상담' })
    expect(within(entry).getByText('모의고사 결과 상담')).toBeInTheDocument()
    expect(within(entry).getByText('후속 조치: 오답 노트 확인')).toBeInTheDocument()
    expect(within(entry).getByText('원장')).toBeInTheDocument()
  })

  it('records a new consult dated today by default', async () => {
    const calls: Call[] = []
    stub(calls)
    const user = userEvent.setup()
    renderDialog()

    const dialog = await screen.findByRole('dialog', { name: '김나윤 상담일지' })
    expect(within(dialog).getByLabelText('상담일')).toHaveValue(today())
    await user.type(within(dialog).getByLabelText('상담 내용'), '학습 계획 점검')
    await user.type(within(dialog).getByLabelText('후속 조치'), '다음 주 재확인')
    await user.click(within(dialog).getByRole('button', { name: '상담 기록' }))

    expect(calls.find((c) => c.method === 'POST')).toEqual({
      url: '/api/students/3/consults',
      method: 'POST',
      body: { consulted_on: today(), content: '학습 계획 점검', follow_up: '다음 주 재확인' },
    })
  })

  it('edits an existing consult in place', async () => {
    const calls: Call[] = []
    stub(calls)
    const user = userEvent.setup()
    renderDialog()

    const entry = await screen.findByRole('article', { name: '2026-09-20 상담' })
    await user.click(within(entry).getByRole('button', { name: '수정' }))
    const content = within(entry).getByLabelText('상담 내용')
    await user.clear(content)
    await user.type(content, '결과 상담 — 수열 보강')
    await user.clear(within(entry).getByLabelText('후속 조치'))
    await user.click(within(entry).getByRole('button', { name: '저장' }))

    expect(calls.find((c) => c.method === 'PATCH')).toEqual({
      url: '/api/students/3/consults/21',
      method: 'PATCH',
      body: { consulted_on: '2026-09-20', content: '결과 상담 — 수열 보강', follow_up: null },
    })
  })
})
