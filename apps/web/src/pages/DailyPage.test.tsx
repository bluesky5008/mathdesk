import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
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

function renderPage(path = '/daily') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <DailyPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

// TASK-74: 대시보드 링크가 준 반·날짜로 연다
it('opens the class and date given in the address', async () => {
  renderPage('/daily?class=1&date=2026-09-18')

  await screen.findByRole('row', { name: /학생1\b/ })
  expect(screen.getByLabelText('날짜')).toHaveValue('2026-09-18')
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
    /\(\d+\/\d+ \d{2}:\d{2} 확정\)\. 과제·테스트는 그대로 입력할 수 있습니다/,
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
