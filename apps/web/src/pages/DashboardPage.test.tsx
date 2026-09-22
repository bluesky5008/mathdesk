import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

import type { Daily, Dashboard } from '../api'
import { DashboardPage } from './DashboardPage'

const classes = [
  { id: 1, name: '고2 윤B', grade: '고2', teacher_id: 1, is_active: true, schedules: [] },
]

let dashboard: Dashboard
let daily: Daily
let calls: string[]

beforeEach(() => {
  dashboard = {
    campus: { enrolled_students: 47, active_classes: 4 },
    attendance: { class_id: 1, class_name: '고2 윤B', enrolled: 13, attending: 4 },
    homework: { completion_rate: 93.8, delta_points: 2.4, missing: 5, recheck_targets: 4 },
    test: { average: 82.6, count: 84, max: 100, max_count: 4, min: 58 },
    last_session: {
      session_date: '2026-09-18',
      progress: [{ period: 1, content: '2024 광문고 기출 시행' }],
      homework: '기출 풀어오기',
    },
  }
  daily = {
    session: {
      id: 9,
      class_id: 1,
      session_date: '2026-09-20',
      progress: [],
      homework: null,
      video_url: null,
      teacher_note: null,
      test_name: null,
      test_max_score: null,
      attendance_confirmed_at: null,
    },
    records: [
      {
        student_id: 1,
        name: '김나윤',
        attendance_status: 'unchecked',
        attendance_reason: null,
        homework_grade: null,
        recheck: { target: false, prev_grade: null, prev_date: null, result: null },
        test_score_num: null,
        test_score_text: null,
      },
    ],
    summary: { enrolled: 13, attending: 4, test_average: null, test_count: 0 },
  }
  calls = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      if (init?.method) calls.push(`${init.method} ${url}`)
      if (url.includes('/classes')) return Response.json(classes)
      if (url.includes('/dashboard')) return Response.json(dashboard)
      return Response.json(daily)
    }),
  )
})

afterEach(() => vi.unstubAllGlobals())

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <DashboardPage />
    </QueryClientProvider>,
  )
}

it('renders the four KPI cards', async () => {
  renderPage()

  expect(await screen.findByText('47명')).toBeInTheDocument()
  expect(screen.getByText('활성 4개 반')).toBeInTheDocument()
  expect(screen.getByText('4 / 13명')).toBeInTheDocument()
  expect(screen.getByText('93.8%')).toBeInTheDocument()
  expect(screen.getByText('전주 대비 +2.4%p')).toBeInTheDocument()
  expect(screen.getByText('82.6점')).toBeInTheDocument()
  expect(screen.getByText('N=84 · MAX 100 (4명) · MIN 58')).toBeInTheDocument()
})

it('shows the previous session progress and homework', async () => {
  renderPage()

  expect(await screen.findByText('[1교시] 2024 광문고 기출 시행')).toBeInTheDocument()
  expect(screen.getByText('기출 풀어오기')).toBeInTheDocument()
})

it('confirms attendance and locks the buttons until edit is pressed', async () => {
  renderPage()
  const row = within(await screen.findByRole('row', { name: /김나윤/ }))
  expect(row.getByRole('button', { name: '출석' })).toBeEnabled()

  await userEvent.click(screen.getByRole('button', { name: '확인' }))
  expect(calls).toContain('POST /api/daily/9/attendance/confirm')

  daily.session.attendance_confirmed_at = '2026-09-20T10:00:00+00:00'
  await userEvent.click(screen.getByRole('button', { name: '확인' }))

  const locked = within(await screen.findByRole('row', { name: /김나윤/ }))
  expect(locked.getByRole('button', { name: '출석' })).toBeDisabled()
  await userEvent.click(screen.getByRole('button', { name: '편집' }))
  expect(calls).toContain('POST /api/daily/9/attendance/unlock')
})
