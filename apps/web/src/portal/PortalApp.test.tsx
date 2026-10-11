import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { PortalApp } from './PortalApp'

afterEach(() => {
  vi.unstubAllGlobals()
})

const GUARDIAN = { id: 9, login_id: '01098765432', display_name: '김나윤 학부모', role: 'guardian', must_change_password: false }

const STUDENTS = [
  { id: 1, name: '김나윤', grade: '고2', status: 'enrolled', classes: [{ id: 2, name: '고2 윤B', teacher_name: '홍길동' }] },
  { id: 3, name: '김정현', grade: '고1', status: 'enrolled', classes: [] },
]

const SESSION = {
  date: '2026-09-18',
  class_name: '고2 윤B',
  progress: [{ period: 1, content: '미적분 1단원' }, { period: 2, content: null }],
  homework: '기출 풀어오기',
  video_url: 'https://example.com/v',
  teacher_note: '다들 수고',
  test_name: '9월 3주 테스트',
  attendance: 'late',
  attendance_reason: '버스',
  homework_grade: 'A',
  grade_comment: '아주 잘했어요',
  recheck: { prev_grade: 'D', prev_date: '2026-09-16', result: 'pass' },
  test_score: '80',
  class_average: 70.0,
  comment: '집중력 좋음',
}

const SUMMARY = {
  attendance: { last_30_days: { present: 3, total: 4 }, all_time: { present: 10, total: 12 } },
  latest_session: SESSION,
  latest_tests: [{ date: '2026-09-18', source: 'daily', name: '9월 3주 테스트', score: 80, class_average: 70, homework_grade: 'A', attendance_status: 'late' }],
  timetable: [{ class_name: '고2 윤B', weekday: 0, start_time: '18:00:00', end_time: '22:00:00' }],
}

function mount(handler: (url: string) => Response, path = '/portal') {
  vi.stubGlobal('fetch', vi.fn(async (url: string) => handler(url)))
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <PortalApp user={GUARDIAN} onLogout={() => {}} />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

function routes(url: string): Response {
  if (url === '/api/portal/students') return Response.json(STUDENTS)
  if (url.endsWith('/summary')) return Response.json(SUMMARY)
  if (url.includes('/sessions')) return Response.json([SESSION])
  return Response.json([])
}

describe('PortalApp', () => {
  it('shows the home summary for the first child and lets a guardian switch children', async () => {
    mount(routes)

    expect(await screen.findByRole('heading', { name: '김나윤' })).toBeInTheDocument()
    expect(await screen.findByText('3 / 4회')).toBeInTheDocument()
    expect(screen.getByText('월 18:00~22:00')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: '종합 대시보드' })).not.toBeInTheDocument()

    await userEvent.selectOptions(screen.getByLabelText('자녀'), '3')
    expect(await screen.findByRole('heading', { name: '김정현' })).toBeInTheDocument()
  })

  it('renders a session record with the same sections as the message', async () => {
    mount(routes, '/portal/records')

    const card = within(await screen.findByRole('article', { name: '9/18(금) 고2 윤B' }))
    expect(card.getByText('[1교시] 미적분 1단원')).toBeInTheDocument()
    expect(card.queryByText('[2교시]')).not.toBeInTheDocument()
    expect(card.getByText('9월 3주 테스트')).toBeInTheDocument()
    expect(card.getByText('기출 풀어오기')).toBeInTheDocument()
    expect(card.getByRole('link', { name: 'https://example.com/v' })).toBeInTheDocument()
    expect(card.getByText('다들 수고')).toBeInTheDocument()
    expect(card.getByText('지각')).toBeInTheDocument()
    expect(card.getByText('버스')).toBeInTheDocument()
    expect(card.getByText('A')).toBeInTheDocument()
    expect(card.getByText('아주 잘했어요')).toBeInTheDocument()
    expect(card.getByText('직전 D (9/16) · 합격')).toBeInTheDocument()
    expect(card.getByText('80점')).toBeInTheDocument()
    expect(card.getByText('반평균 70점')).toBeInTheDocument()
    expect(card.getByText('집중력 좋음')).toBeInTheDocument()
  })

  it('hides empty sections like the message does', async () => {
    const bare = { ...SESSION, progress: [], homework: null, video_url: null, teacher_note: null, test_name: null,
      attendance: 'unchecked', attendance_reason: null, homework_grade: null, grade_comment: null, recheck: null,
      test_score: null, class_average: null, comment: null }
    mount((url) => (url.includes('/sessions') ? Response.json([bare]) : routes(url)), '/portal/records')

    const card = within(await screen.findByRole('article', { name: '9/18(금) 고2 윤B' }))
    expect(card.getByText('미확인')).toBeInTheDocument()
    expect(card.queryByText('수업진도')).not.toBeInTheDocument()
    expect(card.queryByText('테스트 점수')).not.toBeInTheDocument()
  })
})
