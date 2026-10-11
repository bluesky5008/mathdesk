import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

import type { Daily } from '../api'
import { DailyLayout } from './DailyLayout'
import { DailyPage } from './DailyPage'
import { StudentDailyPage } from './StudentDailyPage'

// 시간표는 월요일(weekday 0) — 달력에서 월요일이 수업일로 굵어진다(AC-46)
const classes = [
  { id: 1, name: '고2 윤B', grade: '고2', teacher_id: 1, is_active: true, schedules: [{ weekday: 0, start_time: '16:00' }] },
]

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
    comment: null as string | null,
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
      if (url.includes('/daily/calendar')) return Response.json({ recorded_dates: ['2026-09-19'] })
      if (url.includes('/daily/history')) return Response.json({ student: { id: 1, name: '학생1' }, klass: { id: 1, name: '고2 윤B' }, rows: [] })
      return Response.json(daily)
    }),
  )
})

afterEach(() => vi.unstubAllGlobals())

function renderPage(path = '/daily') {
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

// TASK-74: 대시보드 링크가 준 반·날짜로 연다
it('opens the class and date given in the address', async () => {
  renderPage('/daily?class=1&date=2026-09-18')

  await screen.findByRole('row', { name: /학생1\b/ })
  expect(screen.getByLabelText('날짜')).toHaveTextContent('2026-09-18')
  expect(vi.mocked(fetch)).toHaveBeenCalledWith('/api/daily?class_id=1&date=2026-09-18', expect.anything())
})

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

// 2026-09-25 테스트 운영: 새 반에 배정이 없어 "0 / 0명"만 보이고 이유를 알 수 없었다
it('explains how to assign students when nobody is enrolled on that date', async () => {
  daily.records = []
  daily.summary = { enrolled: 0, attending: 0, test_average: null, test_count: 0 }

  renderPage()

  expect(await screen.findByText(/이 날짜에 이 반에 배정된 학생이 없습니다/)).toBeInTheDocument()
  expect(screen.getByRole('link', { name: '학생/반 관리 → 반' })).toHaveAttribute(
    'href',
    '/students/classes',
  )
})

it('shows no assignment notice when students are enrolled', async () => {
  renderPage()

  await screen.findByRole('row', { name: /학생1\b/ })
  expect(screen.queryByText(/배정된 학생이 없습니다/)).not.toBeInTheDocument()
})

// 2026-09-25 테스트 운영: 확정된 출결이 흐린 버튼과 표 아래 [편집]으로만 표시되어 잠긴 줄 몰랐다
it('marks confirmed attendance as locked with a banner and an unlock button', async () => {
  daily.session.attendance_confirmed_at = '2026-09-18T15:08:00+00:00'

  renderPage()

  expect(await screen.findByText(/9\/18 출결이 확정되어 잠겨 있습니다/)).toHaveTextContent(
    /\(\d+\/\d+ \d{2}:\d{2} 확정\)\. 과제·테스트·코멘트는 그대로 입력할 수 있습니다/,
  )
  expect(screen.getByRole('columnheader', { name: '출결 상태 🔒' })).toBeInTheDocument()

  await userEvent.click(screen.getAllByRole('button', { name: '확정 해제' })[0])
  expect(vi.mocked(fetch)).toHaveBeenCalledWith('/api/daily/9/attendance/unlock', expect.anything())
})

it('keeps a locked attendance cell unchanged and says why when clicked', async () => {
  daily.session.attendance_confirmed_at = '2026-09-18T15:08:00+00:00'

  renderPage()
  const row = within(await screen.findByRole('row', { name: /학생1\b/ }))
  await userEvent.click(row.getByRole('button', { name: '출석' }))
  await userEvent.type(row.getByLabelText('학생1 사유'), '병원')

  expect(row.getByRole('button', { name: '출석' })).toHaveAttribute('aria-pressed', 'false')
  expect(row.getByLabelText('학생1 사유')).toHaveValue('')
  expect(row.getByText('확정됨 · [확정 해제] 후 수정')).toBeInTheDocument()
})

it('names the confirm button and leaves the header plain while unlocked', async () => {
  renderPage()

  expect(await screen.findByRole('button', { name: '출결 확정' })).toBeInTheDocument()
  expect(screen.getByRole('columnheader', { name: '출결 상태' })).toBeInTheDocument()
  expect(screen.queryByText(/잠겨 있습니다/)).not.toBeInTheDocument()
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

// DCR-017: 표 맨 오른쪽 학생별 코멘트 — [표 저장]으로 저장, 문자 개별 구획에 붙는다
it('saves a different comment for each student with the table', async () => {
  daily.records[2].comment = '지난 코멘트'
  renderPage()

  expect(await screen.findByLabelText('학생3 코멘트')).toHaveValue('지난 코멘트')
  expect(screen.getAllByRole('columnheader').at(-1)).toHaveTextContent('코멘트')

  await userEvent.type(screen.getByLabelText('학생1 코멘트'), '잘했어요')
  await userEvent.type(screen.getByLabelText('학생2 코멘트'), '지각 주의')
  await userEvent.click(screen.getByRole('button', { name: '표 저장' }))

  expect(calls).toEqual([
    {
      url: '/api/daily/9/records',
      body: {
        records: [
          { student_id: 1, comment: '잘했어요' },
          { student_id: 2, comment: '지각 주의' },
        ],
      },
    },
  ])
})

it('moves to the next student comment with Enter', async () => {
  renderPage()

  await userEvent.type(await screen.findByLabelText('학생1 코멘트'), '좋아요{Enter}')

  expect(screen.getByLabelText('학생2 코멘트')).toHaveFocus()
})

it('keeps comments editable after attendance is confirmed', async () => {
  daily.session.attendance_confirmed_at = '2026-09-18T15:08:00+00:00'
  renderPage()

  await userEvent.type(await screen.findByLabelText('학생1 코멘트'), '확정 뒤')

  expect(screen.getByLabelText('학생1 코멘트')).toHaveValue('확정 뒤')
})

it('names the teacher note as the common comment that goes into messages', async () => {
  renderPage()

  expect(await screen.findByLabelText('선생님 코멘트 (문자 공통)')).toBeInTheDocument()
  expect(screen.queryByLabelText('강사 첨언')).not.toBeInTheDocument()
})

it('saves the test name from the progress card without a max-score field', async () => {
  // DCR-019 / AC-44 ①: 테스트명은 반 공통 값이라 "오늘 진도" 카드에서 [메모 저장]으로 저장한다
  renderPage()
  await userEvent.type(await screen.findByLabelText('테스트명'), '4차연합고사')
  expect(screen.queryByLabelText('만점')).not.toBeInTheDocument()

  await userEvent.click(screen.getByRole('button', { name: '메모 저장' }))

  expect(calls.find((call) => call.url === '/api/daily/9/notes')?.body).toMatchObject({ test_name: '4차연합고사' })
})

// DCR-020 / AC-45 ①⑤: 반별·학생별 탭, 선택은 주소 쿼리로 공유
it('opens on the class tab and carries class and date into the student tab link', async () => {
  renderPage('/daily?class=1&date=2026-09-18')
  await screen.findByRole('row', { name: /학생1\b/ })

  expect(screen.getByRole('link', { name: '반별 정보' })).toHaveAttribute('aria-current', 'page')
  expect(screen.getByRole('link', { name: '학생별 정보' })).toHaveAttribute(
    'href',
    '/daily/students?class=1&date=2026-09-18',
  )
  expect(screen.getByRole('button', { name: '표 저장' })).toBeInTheDocument()
})

it('asks before leaving the class tab with unsaved input', async () => {
  vi.spyOn(window, 'confirm').mockReturnValue(false)
  renderPage('/daily?class=1&date=2026-09-18')
  await userEvent.type(await screen.findByLabelText('오늘의 과제'), '기출')

  await userEvent.click(screen.getByRole('link', { name: '학생별 정보' }))

  expect(window.confirm).toHaveBeenCalled()
  expect(screen.getByLabelText('오늘의 과제')).toHaveValue('기출')
})

// DCR-020 / AC-46: 달력에서 시간표 요일과 기록이 있는 날이 굵고, 기록이 있는 날은 점
it('opens a month calendar that emphasizes timetable weekdays and recorded days', async () => {
  renderPage('/daily?class=1&date=2026-09-18')
  await screen.findByRole('row', { name: /학생1\b/ })

  await userEvent.click(screen.getByLabelText('날짜'))

  expect(await screen.findByRole('button', { name: '9월 19일 수업일 기록 있음' })).toHaveClass('font-bold')
  expect(screen.getByRole('button', { name: '9월 14일 수업일' })).toHaveClass('font-bold')
  expect(screen.getByRole('button', { name: '9월 15일' })).not.toHaveClass('font-bold')
  expect(vi.mocked(fetch)).toHaveBeenCalledWith('/api/daily/calendar?class_id=1&month=2026-09', expect.anything())

  await userEvent.click(screen.getByRole('button', { name: '9월 21일 수업일' }))

  expect(screen.getByLabelText('날짜')).toHaveTextContent('2026-09-21')
  expect(vi.mocked(fetch)).toHaveBeenCalledWith('/api/daily?class_id=1&date=2026-09-21', expect.anything())
})

it('keeps the date when the unsaved-input warning is declined', async () => {
  vi.spyOn(window, 'confirm').mockReturnValue(false)
  renderPage('/daily?class=1&date=2026-09-18')
  await userEvent.type(await screen.findByLabelText('오늘의 과제'), '기출')

  await userEvent.click(screen.getByLabelText('날짜'))
  await userEvent.click(await screen.findByRole('button', { name: '9월 21일 수업일' }))

  expect(screen.getByLabelText('날짜')).toHaveTextContent('2026-09-18')
  expect(vi.mocked(fetch)).not.toHaveBeenCalledWith('/api/daily?class_id=1&date=2026-09-21', expect.anything())
})
