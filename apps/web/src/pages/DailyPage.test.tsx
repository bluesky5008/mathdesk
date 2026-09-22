import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

import type { Daily } from '../api'
import { DailyPage } from './DailyPage'

const classes = [{ id: 1, name: '고2 윤B', grade: '고2', teacher_id: 1, is_active: true, schedules: [] }]

function makeRecord(id: number, name: string) {
  return {
    student_id: id,
    name,
    attendance_status: 'unchecked',
    attendance_reason: null,
    homework_grade: null,
    recheck: { target: false, prev_grade: null, prev_date: null, result: null },
    test_score_num: null,
    test_score_text: null,
  }
}

let daily: Daily
let calls: { url: string; body: unknown }[]

beforeEach(() => {
  daily = {
    session: {
      id: 9,
      class_id: 1,
      session_date: '2026-09-18',
      progress: [],
      homework: null,
      video_url: null,
      teacher_note: null,
      test_name: null,
      test_max_score: null,
      attendance_confirmed_at: null,
    },
    records: Array.from({ length: 13 }, (_, index) => makeRecord(index + 1, `학생${index + 1}`)),
    summary: { enrolled: 13, attending: 0, test_average: null, test_count: 0 },
  }
  calls = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      if (init?.body) calls.push({ url, body: JSON.parse(String(init.body)) })
      if (url.includes('/classes')) return Response.json(classes)
      return Response.json(daily)
    }),
  )
})

afterEach(() => vi.unstubAllGlobals())

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <DailyPage />
    </QueryClientProvider>,
  )
}

it('keeps unsaved notes when the record table is saved', async () => {
  renderPage()
  const homework = await screen.findByLabelText('오늘의 과제')
  await userEvent.type(homework, '기출 풀어오기')

  await userEvent.click(screen.getByRole('button', { name: '표 저장' }))

  expect(await screen.findByLabelText('오늘의 과제')).toHaveValue('기출 풀어오기')
})

it('shows the attendance count as attending over enrolled', async () => {
  daily.summary = { enrolled: 13, attending: 4, test_average: null, test_count: 0 }

  renderPage()

  expect(await screen.findByText('4 / 13명')).toBeInTheDocument()
})

it('toggles an attendance button back to unchecked', async () => {
  renderPage()
  const row = within(await screen.findByRole('row', { name: /학생1\b/ }))

  await userEvent.click(row.getByRole('button', { name: '출석' }))
  expect(row.getByRole('button', { name: '출석' })).toHaveAttribute('aria-pressed', 'true')

  await userEvent.click(row.getByRole('button', { name: '출석' }))
  expect(row.getByRole('button', { name: '출석' })).toHaveAttribute('aria-pressed', 'false')
})

it('saves the recheck result immediately without the bulk save', async () => {
  daily.records[0].recheck = { target: true, prev_grade: 'B', prev_date: '2026-09-16', result: null }

  renderPage()
  const row = within(await screen.findByRole('row', { name: /학생1\b/ }))
  expect(row.getByText('직전 B · 09/16')).toBeInTheDocument()

  await userEvent.click(row.getByRole('button', { name: '합격' }))

  expect(calls.map((call) => call.url)).toEqual(['/api/daily/9/records/1/recheck'])
})
