import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
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
    {
      student_id: 4,
      name: '김정현',
      attendance_status: 'late',
      attendance_reason: null,
      homework_grade: null,
      recheck: { target: false, prev_grade: null, prev_date: null, result: null },
      test_score_num: null,
      test_score_text: null,
    },
  ],
  summary: { enrolled: 2, attending: 2, test_average: null, test_count: 0 },
}
// DCR-023: 반 단위 일괄 발송 — 대상·제외 미리보기, 작업 등록, 폴링 결과
const batchPlan = {
  planned: [{ student_id: 3, name: '김나윤' }, { student_id: 4, name: '김정현' }],
  skipped: [{ student_id: 5, name: '김태호', reason: 'no_recipient' }, { student_id: 6, name: '박지성', reason: 'already_sent' }],
}
let sendResult: { channel: string; results: unknown[] } = { channel: 'lms', results: [] }
let taskResult = {
  id: 77, kind: 'message_batch', status: 'done', progress: 100, error: null,
  result: {
    sent: 1, failed: 1, test: 0, skipped: 0,
    students: [
      { student_id: 3, name: '김나윤', status: 'sent', channel: 'lms', error: null },
      { student_id: 4, name: '김정현', status: 'failed', channel: 'lms', error: '수신 거부' },
    ],
  },
}
const preview = { body: '**김나윤학생 학습피드백**\n\n■ 출결: 출석' }
const templates = {
  fallback_to_sms: true,
  alimtalk: [{ code: 'TPL_DAILY_01', body: '#{학생명} 학생 수업 안내', variables: { 학생명: 'student_name' } }],
  fields: [{ key: 'student_name', label: '학생 이름' }],
}

let calls: { url: string; body?: unknown }[]

beforeEach(() => {
  calls = []
  sendResult = { channel: 'lms', results: [] }
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      if (init?.method) calls.push({ url, body: init.body ? JSON.parse(String(init.body)) : undefined })
      if (url.includes('/classes')) return Response.json(classes)
      if (url.includes('/messages/preview')) return Response.json(preview)
      if (url.includes('/messages/logs')) return Response.json([])
      if (url.includes('/messages/send-batch/preview')) return Response.json(batchPlan)
      if (url.includes('/messages/send-batch')) return Response.json({ task_id: 77, ...batchPlan })
      if (url.includes('/tasks/77')) return Response.json(taskResult)
      if (url.includes('/messages/send')) return Response.json(sendResult)
      if (url.includes('/messages/templates')) return Response.json(templates)
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

it('sends through an approved alimtalk template when one is chosen', async () => {
  renderPage()
  await userEvent.selectOptions(await screen.findByLabelText('발송 방식'), '알림톡 · TPL_DAILY_01')
  await userEvent.click(screen.getByLabelText('학부모'))

  await userEvent.click(screen.getByRole('button', { name: '알림톡 발송' }))

  const sent = calls.find((call) => call.url.includes('/messages/send'))
  expect(sent?.body).toEqual({ session_id: 9, student_id: 3, recipients: ['guardian'], template_code: 'TPL_DAILY_01' })
})

// DCR-023 / AC-49 ①: 확인 창에 대상 수와 제외 학생(사유)이 보인다
it('previews the class batch with planned and skipped students', async () => {
  renderPage()
  await screen.findByRole('button', { name: '반 전체 발송' })
  await userEvent.click(screen.getByLabelText('학부모'))

  await userEvent.click(screen.getByRole('button', { name: '반 전체 발송' }))

  const dialog = await screen.findByRole('dialog')
  expect(within(dialog).getByText('대상 2명')).toBeInTheDocument()
  expect(within(dialog).getByText(/김태호/)).toHaveTextContent('연락처 없음')
  expect(within(dialog).getByText(/박지성/)).toHaveTextContent('이미 보냄')
  expect(vi.mocked(fetch)).toHaveBeenCalledWith(
    '/api/messages/send-batch/preview?session_id=9&recipients=guardian&include_already_sent=false',
    expect.anything(),
  )
})

// AC-49 ②③: 등록 → 폴링 → 학생별 결과, 실패만 다시 보내기
it('starts the batch, shows per-student results and resends only the failed ones', async () => {
  renderPage()
  await screen.findByRole('button', { name: '반 전체 발송' })
  await userEvent.click(screen.getByLabelText('학부모'))
  await userEvent.click(screen.getByRole('button', { name: '반 전체 발송' }))
  const dialog = await screen.findByRole('dialog')

  await userEvent.click(await within(dialog).findByRole('button', { name: '2명에게 보내기' }))

  expect(calls.find((call) => call.url === '/api/messages/send-batch')?.body).toEqual({
    session_id: 9, recipients: ['guardian'], include_already_sent: false,
  })
  const rows = await within(dialog).findAllByRole('row')
  expect(rows.map((row) => row.textContent)).toEqual(
    expect.arrayContaining([expect.stringMatching(/김나윤.*접수/), expect.stringMatching(/김정현.*실패.*수신 거부/)]),
  )

  await userEvent.click(within(dialog).getByRole('button', { name: '실패만 다시 보내기' }))

  const retry = calls.filter((call) => call.url === '/api/messages/send-batch').at(-1)
  expect(retry?.body).toEqual({ session_id: 9, recipients: ['guardian'], include_already_sent: false, student_ids: [4] })
})

it('offers to resend a single student when the send failed', async () => {
  sendResult = {
    channel: 'lms',
    results: [{ recipient_phone: '01011112222', recipient_type: 'guardian', status: 'failed', result_code: 'E', error: '수신 거부' }],
  }
  renderPage()
  await screen.findByRole('button', { name: '문자 발송' })
  await userEvent.click(screen.getByLabelText('학부모'))
  await userEvent.click(screen.getByRole('button', { name: '문자 발송' }))

  await userEvent.click(await screen.findByRole('button', { name: '다시 보내기' }))

  expect(calls.filter((call) => call.url === '/api/messages/send')).toHaveLength(2)
})
