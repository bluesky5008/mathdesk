import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

import { MessagesPage } from './MessagesPage'

const classes = [
  { id: 1, name: '고2 윤B', grade: '고2', teacher_id: 1, is_active: true, schedules: [] },
]
const daily = {
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
  records: [
    {
      student_id: 3,
      name: '김나윤',
      attendance_status: 'present',
      attendance_reason: null,
      homework_grade: 'B',
      recheck: { target: false, prev_grade: null, prev_date: null, result: null },
      test_score_num: null,
      test_score_text: null,
    },
  ],
  summary: { enrolled: 1, attending: 1, test_average: null, test_count: 0 },
}
const preview = { body: '**김나윤학생 학습피드백**\n\n■ 출결: 출석' }

let calls: { url: string; body?: unknown }[]

beforeEach(() => {
  calls = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      if (init?.method) calls.push({ url, body: init.body ? JSON.parse(String(init.body)) : undefined })
      if (url.includes('/classes')) return Response.json(classes)
      if (url.includes('/messages/preview')) return Response.json(preview)
      if (url.includes('/messages/logs')) return Response.json([])
      if (url.includes('/messages/send')) return Response.json({ channel: 'lms', results: [] })
      return Response.json(daily)
    }),
  )
})

afterEach(() => vi.unstubAllGlobals())

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MessagesPage />
    </QueryClientProvider>,
  )
}

it('shows the merged message body in the text tab', async () => {
  renderPage()

  expect(await screen.findByText(/김나윤학생 학습피드백/)).toBeInTheDocument()
})

it('disables sending until a recipient is selected', async () => {
  renderPage()
  const send = await screen.findByRole('button', { name: '문자 발송' })
  expect(send).toBeDisabled()

  await userEvent.click(screen.getByLabelText('학부모'))

  expect(screen.getByRole('button', { name: '문자 발송' })).toBeEnabled()
})

it('sends to the selected recipients', async () => {
  renderPage()
  await screen.findByRole('button', { name: '문자 발송' })
  await userEvent.click(screen.getByLabelText('학생'))
  await userEvent.click(screen.getByLabelText('학부모'))

  await userEvent.click(screen.getByRole('button', { name: '문자 발송' }))

  const sent = calls.find((call) => call.url.includes('/messages/send'))
  expect(sent?.body).toEqual({ session_id: 9, student_id: 3, recipients: ['student', 'guardian'] })
})

it('shows the report image in the report tab', async () => {
  renderPage()
  await userEvent.click(await screen.findByRole('tab', { name: '리포트 보기' }))

  const image = await screen.findByRole('img', { name: '리포트 카드' })
  expect(image).toHaveAttribute(
    'src',
    '/api/messages/report-image?session_id=9&student_id=3',
  )
})

it('copies the message text to the clipboard', async () => {
  const writeText = vi.fn(async () => undefined)
  Object.defineProperty(navigator, 'clipboard', {
    value: { writeText },
    configurable: true,
  })
  renderPage()
  await screen.findByText(/김나윤학생 학습피드백/)

  await userEvent.click(screen.getByRole('button', { name: '문자 복사' }))

  expect(writeText).toHaveBeenCalledWith(preview.body)
})
