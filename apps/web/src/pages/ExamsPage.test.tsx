import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ExamDetail, ExamQuestion, ExamRow } from '../api'
import { ExamsPage } from './ExamsPage'

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <ExamsPage />
    </QueryClientProvider>,
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
})

const row: ExamRow = {
  id: 5,
  name: '강K 9회',
  source_file_id: 1,
  class_id: null,
  exam_date: '2026-09-19',
  question_count: 3,
  status: 'draft',
  needs_review: 1,
}

const detail: ExamDetail = {
  ...row,
  max_score: 100,
  answer_key_odd: null,
  answer_key_even: null,
  difficulty: { low: 1, mid: 1, high: 1, top: 0 },
}

const question = (no: number, needs_review: boolean): ExamQuestion => ({
  no,
  unit: '이차방정식',
  sub_type: `공통 객관식 ${no}번 — 근과 계수`,
  difficulty: 'mid',
  rationale: '두 근의 합을 이용한다',
  points: null,
  confidence: needs_review ? 0.5 : 0.9,
  needs_review,
})

type Call = { url: string; method: string; body: unknown }

function stub(calls: Call[]) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? 'GET'
      calls.push({ url, method, body: init?.body ? JSON.parse(String(init.body)) : null })
      const confirmed = calls.some((c) => c.method === 'PATCH' && c.url.endsWith('/questions'))
      if (url.endsWith('/questions')) {
        return Response.json([question(1, false), question(2, !confirmed), question(3, false)])
      }
      if (url.endsWith('/api/exams')) return Response.json([row])
      if (url.endsWith('/api/exams/5')) return Response.json(detail)
      return Response.json([])
    }),
  )
}

describe('ExamsPage', () => {
  it('flags low-confidence questions and clears the flag once confirmed', async () => {
    const calls: Call[] = []
    stub(calls)

    renderPage()

    const table = await screen.findByRole('table', { name: '시험지 문항 분석' })
    const flagged = (await within(table).findByText('확인 필요')).closest('tr')!
    expect(within(flagged).getByText('2')).toBeInTheDocument()

    await userEvent.click(within(flagged).getByRole('button', { name: '확인' }))

    await waitFor(() => expect(within(table).queryByText('확인 필요')).not.toBeInTheDocument())
    const patch = calls.find((c) => c.method === 'PATCH')!
    expect(patch.url).toBe('/api/exams/5/questions')
    expect(patch.body).toEqual({ questions: [{ no: 2 }] })
  })

  it('saves both answer keys for the exam', async () => {
    const calls: Call[] = []
    stub(calls)

    renderPage()

    await userEvent.type(await screen.findByLabelText('홀수형 정답'), '3 5 1')
    await userEvent.type(screen.getByLabelText('짝수형 정답'), '1, 5, 3')
    await userEvent.click(screen.getByRole('button', { name: '시험 정보 저장' }))

    await waitFor(() => expect(calls.some((c) => c.method === 'PATCH')).toBe(true))
    const patch = calls.find((c) => c.method === 'PATCH')!
    expect(patch.url).toBe('/api/exams/5')
    expect(patch.body).toMatchObject({ answer_key_odd: [3, 5, 1], answer_key_even: [1, 5, 3] })
  })

  it('shows the difficulty counts and offers the card image', async () => {
    stub([])

    renderPage()

    const link = await screen.findByRole('link', { name: '이미지 저장' })
    expect(link).toHaveAttribute('href', '/api/exams/5/difficulty-card')
    expect(screen.getByText('최상')).toBeInTheDocument()
  })
})
