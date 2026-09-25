import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { PeriodStats, StudentHistory } from '../api'
import { StatsPage } from './StatsPage'

function renderPage(path = '/stats') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <StatsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
})

const klass = { id: 1, name: '고2 윤B', grade: '고2', teacher_id: 1, is_active: true, schedules: [] }

const emptyPeriod: PeriodStats = {
  start: '2026-09-01',
  end: '2026-09-30',
  students: [],
  test: { average: null, count: 0, distribution: [] },
  homework: { completion_rate: null, distribution: {} },
  attendance_rate: null,
}

const filledPeriod: PeriodStats = {
  ...emptyPeriod,
  students: [
    { student_id: 1, name: '김나윤', test_average: 92.5, homework_completion: 100.0, attendance_rate: 100.0 },
    { student_id: 2, name: '김정현', test_average: 72.5, homework_completion: 0.0, attendance_rate: 100.0 },
  ],
  test: { average: 82.5, count: 4, distribution: [{ bucket: '70~79', count: 2 }, { bucket: '90~100', count: 2 }] },
}

/** 8주 중 마지막 3주에만 표본이 있다. */
const history: StudentHistory = {
  student: { id: 1, name: '김나윤' },
  klass: { id: 1, name: '고2 윤B' },
  weeks: Array.from({ length: 8 }, (_, index) => ({
    week_start: `2026-08-0${index + 1}`.slice(0, 10),
    test_average: index >= 5 ? [85, 90, 95][index - 5] : null,
    class_test_average: index >= 5 ? [75, 80, 85][index - 5] : null,
    homework_grades: index >= 5 ? ['A'] : [],
    homework_completion: index >= 5 ? 100 : null,
    class_homework_completion: index >= 5 ? 50 : null,
    attendance_rate: index >= 5 ? 100 : null,
  })),
}

function stub(period: PeriodStats = filledPeriod) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      if (url.includes('/stats/students/')) return Response.json(history)
      if (url.includes('/stats/classes/')) {
        return Response.json({ klass, period, compare: null })
      }
      return Response.json([klass])
    }),
  )
}

describe('StatsPage', () => {
  // TASK-74: 대시보드의 과제·테스트 KPI가 그 주 범위로 연다
  it('opens the class and period given in the address', async () => {
    stub()

    renderPage('/stats?class=1&start=2026-09-14&end=2026-09-20')

    await waitFor(() =>
      expect(vi.mocked(fetch)).toHaveBeenCalledWith(
        '/api/stats/classes/1?start=2026-09-14&end=2026-09-20',
        expect.anything(),
      ),
    )
    expect(screen.getByLabelText('시작')).toHaveValue('2026-09-14')
    expect(screen.getByLabelText('종료')).toHaveValue('2026-09-20')
  })

  it('shows an empty state when the period has no samples', async () => {
    stub(emptyPeriod)

    renderPage()

    expect(await screen.findByText('표본이 없습니다.')).toBeInTheDocument()
  })

  it('lists the last eight weeks of the student trend beside the class average', async () => {
    stub()

    renderPage()

    const trend = await screen.findByRole('table', { name: '주간 추이' })
    await waitFor(() => expect(within(trend).getAllByRole('row')).toHaveLength(9))
    const rows = within(trend).getAllByRole('row').slice(1)
    expect(within(rows[7]).getByText('95')).toBeInTheDocument()
    expect(within(rows[7]).getByText('85')).toBeInTheDocument()
  })

  it('offers an excel download for the shown period', async () => {
    stub()

    renderPage()

    const link = await screen.findByRole('link', { name: '엑셀 내려받기' })
    expect(link).toHaveAttribute('href', expect.stringContaining('/api/stats/export?class_id=1'))
  })
})
