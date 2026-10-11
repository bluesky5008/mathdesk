import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
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
  test: { average: null, count: 0 },
  homework: { completion_rate: null, distribution: {} },
  attendance_rate: null,
}

const filledPeriod: PeriodStats = {
  ...emptyPeriod,
  students: [
    { student_id: 1, name: '김나윤', test_average: 92.5, homework_completion: 100.0, attendance_rate: 100.0 },
    { student_id: 2, name: '김정현', test_average: 72.5, homework_completion: 0.0, attendance_rate: 100.0 },
  ],
  test: { average: 82.5, count: 4 },
}

/** 전체 `total`회차 중 최근 회차들. 같은 날 일일 테스트와 OMR 시험이 함께 있다. */
function history(total: number): StudentHistory {
  return {
    student: { id: 1, name: '김나윤' },
    klass: { id: 1, name: '고2 윤B' },
    total,
    rounds: [
      { date: '2026-09-04', source: 'daily', name: '주간', score: 85, class_average: 66.7, homework_grade: 'A', attendance_status: 'present' },
      { date: '2026-09-11', source: 'daily', name: '주간', score: 90, class_average: 71.7, homework_grade: 'B', attendance_status: 'late' },
      { date: '2026-09-11', source: 'exam', name: '9월 모의', score: null, class_average: 70, homework_grade: 'B', attendance_status: 'late' },
    ],
  }
}

function stub(period: PeriodStats = filledPeriod, total = 3) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      if (url.includes('/stats/students/')) return Response.json(history(total))
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

  // DCR-018: 테스트 회차마다 내 점수·반 평균·그날의 과제 등급·출결
  it('lists each test round of the student beside the class average', async () => {
    stub()

    renderPage()

    expect(await screen.findByText('회차별 성적 추이')).toBeInTheDocument()
    const trend = await screen.findByRole('table', { name: '회차별 성적 추이' })
    await waitFor(() => expect(within(trend).getAllByRole('row')).toHaveLength(4))
    const rows = within(trend).getAllByRole('row').slice(1)
    expect(rows.map((row) => row.textContent)).toEqual([
      '2026-09-04주간8566.7A출석',
      '2026-09-11주간9071.7B지각',
      '2026-09-119월 모의—70B지각',
    ])
  })

  it('has no score distribution chart in the class card', async () => {
    stub()

    renderPage()

    await screen.findByRole('table', { name: '학생별 통계' })
    expect(screen.queryByText(/점수 분포/)).not.toBeInTheDocument()
  })

  it('fixes the rounds at ten when the class has ten rounds or fewer', async () => {
    stub(filledPeriod, 10)

    renderPage()

    const select = await screen.findByLabelText('회차')
    await waitFor(() => expect(select).toBeDisabled())
    expect(select).toHaveValue('10')
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      expect.stringContaining('/api/stats/students/1?to='),
      expect.anything(),
    )
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(expect.stringContaining('rounds=10'), expect.anything())
  })

  it('offers twenty rounds when the class has more than ten', async () => {
    stub(filledPeriod, 11)

    renderPage()

    const select = await screen.findByLabelText('회차')
    await waitFor(() => expect(select).toBeEnabled())
    await userEvent.selectOptions(select, '20')

    await waitFor(() =>
      expect(vi.mocked(fetch)).toHaveBeenCalledWith(expect.stringContaining('rounds=20'), expect.anything()),
    )
  })

  it('offers an excel download for the shown period', async () => {
    stub()

    renderPage()

    const link = await screen.findByRole('link', { name: '엑셀 내려받기' })
    expect(link).toHaveAttribute('href', expect.stringContaining('/api/stats/export?class_id=1'))
  })
})
