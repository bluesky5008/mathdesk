import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router'
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

function renderPage(path = '/') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="*" element={<p>이동한 화면</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

// TASK-74: 항목을 누르면 그 수치의 화면으로, 보던 반·날짜 그대로 간다(사용자 결정 2026-09-25)
it('links each item to the screen behind it with the same class and date', async () => {
  renderPage('/?class=1&date=2026-09-20')

  expect(await screen.findByRole('link', { name: '47명' })).toHaveAttribute('href', '/students')
  expect(screen.getByLabelText('날짜')).toHaveValue('2026-09-20')
  expect(vi.mocked(fetch)).toHaveBeenCalledWith('/api/dashboard?class_id=1&date=2026-09-20', expect.anything())
  const daily = '/daily?class=1&date=2026-09-20'
  const week = '/stats?class=1&start=2026-09-14&end=2026-09-20'
  expect(screen.getByRole('link', { name: '활성 4개 반' })).toHaveAttribute('href', '/students/classes')
  expect(screen.getByRole('link', { name: /선택한 반 등원 현황/ })).toHaveAttribute('href', daily)
  expect(screen.getByRole('link', { name: /금주 과제 완수율/ })).toHaveAttribute('href', week)
  expect(screen.getByRole('link', { name: /주간테스트 종합 평균/ })).toHaveAttribute('href', week)
  expect(screen.getByRole('link', { name: '일일 입력에서 열기' })).toHaveAttribute('href', daily)
  expect(await screen.findByRole('link', { name: '2026-09-18 수업 열기' })).toHaveAttribute(
    'href',
    '/daily?class=1&date=2026-09-18',
  )
})

it('asks before leaving with unsaved attendance', async () => {
  const confirm = vi.fn(() => false)
  vi.stubGlobal('confirm', confirm)
  renderPage('/?class=1&date=2026-09-20')
  const row = within(await screen.findByRole('row', { name: /김나윤/ }))
  await userEvent.click(row.getByRole('button', { name: '출석' }))

  await userEvent.click(screen.getByRole('link', { name: /선택한 반 등원 현황/ }))
  expect(confirm).toHaveBeenCalledTimes(1)
  expect(screen.getByRole('heading', { name: '종합 대시보드' })).toBeInTheDocument()

  confirm.mockReturnValue(true)
  await userEvent.click(screen.getByRole('link', { name: /선택한 반 등원 현황/ }))
  expect(await screen.findByText('이동한 화면')).toBeInTheDocument()
})

it('leaves without asking when nothing is unsaved', async () => {
  const confirm = vi.fn(() => false)
  vi.stubGlobal('confirm', confirm)
  renderPage()

  await userEvent.click(await screen.findByRole('link', { name: /주간테스트 종합 평균/ }))
  expect(await screen.findByText('이동한 화면')).toBeInTheDocument()
  expect(confirm).not.toHaveBeenCalled()
})

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

it('confirms attendance and locks the buttons until unlocked', async () => {
  renderPage()
  const row = within(await screen.findByRole('row', { name: /김나윤/ }))
  expect(row.getByRole('button', { name: '출석' })).not.toHaveAttribute('aria-disabled')

  daily.session.attendance_confirmed_at = '2026-09-20T10:00:00+00:00'
  await userEvent.click(screen.getByRole('button', { name: '출결 확정' }))
  expect(calls).toContain('POST /api/daily/9/attendance/confirm')

  expect(await screen.findByText(/출결이 확정되어 잠겨 있습니다/)).toBeInTheDocument()
  const locked = within(screen.getByRole('row', { name: /김나윤/ }))
  expect(locked.getByRole('button', { name: '출석' })).toHaveAttribute('aria-disabled', 'true')
  await userEvent.click(locked.getByRole('button', { name: '출석' }))
  expect(locked.getByText('확정됨 · [확정 해제] 후 수정')).toBeInTheDocument()

  await userEvent.click(screen.getAllByRole('button', { name: '확정 해제' })[0])
  expect(calls).toContain('POST /api/daily/9/attendance/unlock')
})
