import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

import type { DailyHistory } from '../api'
import { DailyLayout } from './DailyLayout'
import { DailyPage } from './DailyPage'
import { StudentDailyPage } from './StudentDailyPage'

const classes = [{ id: 1, name: '고2 윤B', grade: '고2', teacher_id: 1, is_active: true, schedules: [] }]

function record(id: number, name: string) {
  return {
    student_id: id,
    name,
    attendance_status: 'unchecked',
    attendance_reason: null,
    homework_grade: null,
    recheck: { target: false, prev_grade: null, prev_date: null, result: null },
    test_score_num: null,
    test_score_text: null,
    comment: null,
  }
}

let records: ReturnType<typeof record>[]
let history: DailyHistory

beforeEach(() => {
  records = [record(1, '학생1'), record(2, '학생2')]
  history = {
    student: { id: 1, name: '학생1' },
    klass: { id: 1, name: '고2 윤B' },
    rows: [
      {
        date: '2026-09-16',
        attendance_status: 'unchecked',
        attendance_reason: null,
        recheck: { target: false, prev_grade: null, prev_date: null, result: null },
        homework_grade: null,
        test_name: null,
        test_score_num: null,
        class_average: null,
        comment: null,
      },
      {
        date: '2026-09-14',
        attendance_status: 'late',
        attendance_reason: '버스 지연',
        recheck: { target: true, prev_grade: 'B', prev_date: '2026-09-09', result: 'pass' },
        homework_grade: 'A',
        test_name: '4차연합고사',
        test_score_num: '78.00',
        class_average: 71.7,
        comment: '풀이가 깔끔해졌어요',
      },
    ],
  }
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      if (url.includes('/classes')) return Response.json(classes)
      if (url.includes('/daily/calendar')) return Response.json({ recorded_dates: [] })
      if (url.includes('/daily/history')) return Response.json(history)
      return Response.json({
        session: { id: 9, class_id: 1, session_date: '2026-09-18', progress: [], homework: null, video_url: null, teacher_note: null, test_name: null, test_max_score: null, attendance_confirmed_at: null },
        records,
        summary: { enrolled: records.length, attending: 0, test_average: null, test_count: 0 },
      })
    }),
  )
})

afterEach(() => vi.unstubAllGlobals())

function renderPage(path = '/daily/students?class=1&date=2026-09-18') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/daily" element={<DailyLayout />}>
            <Route index element={<DailyPage />} />
            <Route path="students" element={<StudentDailyPage />} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

// DCR-020 / AC-45 ②③④: 첫 학생의 최근 수업을 최신 순으로, 빈 날도 행으로
it('shows the first student history newest first with a link back to the class tab', async () => {
  renderPage()

  expect(await screen.findByRole('link', { name: '09/14(월)' })).toHaveAttribute('href', '/daily?class=1&date=2026-09-14')
  expect(vi.mocked(fetch)).toHaveBeenCalledWith(
    '/api/daily/history?class_id=1&student_id=1&to=2026-09-18&limit=20',
    expect.anything(),
  )
  expect(screen.getAllByRole('columnheader').map((cell) => cell.textContent)).toEqual([
    '날짜', '출결', '이전 과제 재검사', '과제피드백', '테스트', '코멘트',
  ])
  const rows = screen.getAllByRole('row').slice(1)
  expect(rows[0]).toHaveTextContent('09/16(수)')
  const newest = within(rows[0])
  expect(newest.getByText('미확인')).toBeInTheDocument()
  expect(newest.getAllByText('—')).toHaveLength(2)
  const older = within(rows[1])
  expect(older.getByText('지각')).toBeInTheDocument()
  expect(older.getByText('버스 지연')).toBeInTheDocument()
  expect(older.getByText('직전 B · 09/09')).toBeInTheDocument()
  expect(older.getByText('합격')).toBeInTheDocument()
  expect(older.getByText('A')).toBeInTheDocument()
  expect(older.getByText('4차연합고사')).toBeInTheDocument()
  expect(older.getByText('78 / 71.7')).toBeInTheDocument()
  expect(older.getByText('풀이가 깔끔해졌어요')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: '학생별 정보' })).toHaveAttribute('aria-current', 'page')
})

it('summarizes attendance and test average over the listed lessons', async () => {
  renderPage()

  expect(await screen.findByText('1 / 2회')).toBeInTheDocument()
  expect(screen.getByText('78점 (1회)')).toBeInTheDocument()
})

it('switches student through the address and refetches', async () => {
  renderPage()
  await screen.findByRole('link', { name: '09/14(월)' })

  await userEvent.selectOptions(screen.getByLabelText('학생'), '2')

  expect(vi.mocked(fetch)).toHaveBeenCalledWith(
    '/api/daily/history?class_id=1&student_id=2&to=2026-09-18&limit=20',
    expect.anything(),
  )
  expect(screen.getByRole('link', { name: '반별 정보' })).toHaveAttribute(
    'href',
    '/daily?class=1&date=2026-09-18&student=2',
  )
})

it('explains how to assign students when the roster is empty', async () => {
  records = []
  renderPage()

  expect(await screen.findByText(/이 날짜에 이 반에 배정된 학생이 없습니다/)).toBeInTheDocument()
})
