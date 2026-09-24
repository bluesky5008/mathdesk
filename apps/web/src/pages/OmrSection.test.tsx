import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { OmrScan } from '../api'
import { OmrSection } from './OmrSection'

function renderSection() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <OmrSection examId={5} />
    </QueryClientProvider>,
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
})

const answers = Object.fromEntries(Array.from({ length: 30 }, (_, i) => [String(i + 1), 1]))

const flagged: OmrScan = {
  id: 11,
  file_id: 1,
  page_no: 1,
  status: 'needs_review',
  student: { id: 3, name: '김하나' },
  exam_number: '75397513',
  form: 'odd',
  answers: { ...answers, '3': null, '22': null },
  flags: [
    { field: '3', code: 'multi' },
    { field: '22', code: 'blank' },
  ],
  error: null,
}

const clean: OmrScan = { ...flagged, id: 12, page_no: 2, status: 'read', student: { id: 4, name: '이두리' }, answers, flags: [] }

const stranger: OmrScan = {
  ...clean,
  id: 13,
  page_no: 3,
  status: 'needs_review',
  student: null,
  exam_number: '12000000',
  flags: [{ field: 'student', code: 'unmatched' }],
}

type Call = { url: string; method: string; body: unknown }

function stub(calls: Call[]) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? 'GET'
      const body = typeof init?.body === 'string' ? JSON.parse(init.body) : (init?.body ?? null)
      calls.push({ url, method, body })
      const reviewed = calls.some((c) => c.method === 'PATCH' && c.url.endsWith('/scans/11'))
      if (method === 'PATCH') return Response.json({ ...flagged, status: 'read', flags: [] })
      if (url.endsWith('/omr/scans')) {
        return Response.json([reviewed ? { ...flagged, status: 'read', flags: [] } : flagged, clean, stranger])
      }
      if (url.endsWith('/omr/uploads')) return Response.json({ file_id: 9, task_id: 77 }, { status: 202 })
      if (url.endsWith('/tasks/77')) {
        return Response.json({ id: 77, kind: 'omr_read', status: 'done', progress: 100, result: { pages: 3, failed: 0 }, error: null })
      }
      if (url.endsWith('/api/students')) {
        return Response.json([{ id: 7, name: '박세찬', school: null, grade: null, phone: null, status: 'enrolled', omr_number: '19000100' }])
      }
      return Response.json([])
    }),
  )
}

describe('OmrSection', () => {
  it('lists scans and keeps flagged sheets waiting for review', async () => {
    stub([])

    renderSection()

    const table = await screen.findByRole('table', { name: 'OMR 스캔' })
    const rows = within(table).getAllByRole('row').slice(1)
    expect(within(rows[0]).getByText('검수 필요')).toBeInTheDocument()
    expect(within(rows[0]).getByText('3번 복수마킹')).toBeInTheDocument()
    expect(within(rows[0]).getByText('22번 무마킹')).toBeInTheDocument()
    expect(within(rows[1]).getByText('판독 완료')).toBeInTheDocument()
    expect(within(rows[2]).getByText('학생 매칭 실패')).toBeInTheDocument()
    expect(screen.getByText('검수 대기 2 / 전체 3')).toBeInTheDocument()
  })

  it('shows the original crop next to each flagged value and saves the correction', async () => {
    const calls: Call[] = []
    stub(calls)
    const user = userEvent.setup()
    renderSection()

    const table = await screen.findByRole('table', { name: 'OMR 스캔' })
    await user.click(within(within(table).getAllByRole('row')[1]).getByRole('button', { name: '검수' }))

    const dialog = await screen.findByRole('dialog', { name: 'OMR 검수 · 1쪽 김하나' })
    expect(within(dialog).getByRole('img', { name: '3번 원본' })).toHaveAttribute(
      'src',
      '/api/exams/5/omr/scans/11/image?field=3',
    )
    await user.type(within(dialog).getByLabelText('3번 답'), '4')
    await user.click(within(dialog).getByRole('button', { name: '검수 완료' }))

    const patch = calls.find((c) => c.method === 'PATCH')!
    expect(patch.url).toBe('/api/exams/5/omr/scans/11')
    // 비워 둔 22번은 무응답으로 확인한다
    expect(patch.body).toEqual({ answers: { '3': 4, '22': null } })
    expect(await within(table).findAllByText('판독 완료')).toHaveLength(2)
  })

  it('assigns a student by hand when the exam number did not match', async () => {
    const calls: Call[] = []
    stub(calls)
    const user = userEvent.setup()
    renderSection()

    const table = await screen.findByRole('table', { name: 'OMR 스캔' })
    await user.click(within(within(table).getAllByRole('row')[3]).getByRole('button', { name: '검수' }))

    const dialog = await screen.findByRole('dialog', { name: 'OMR 검수 · 3쪽 학생 미지정' })
    expect(within(dialog).getByRole('img', { name: '수험번호 원본' })).toBeInTheDocument()
    await user.selectOptions(await within(dialog).findByLabelText('학생'), '박세찬 (19000100)')
    await user.click(within(dialog).getByRole('button', { name: '검수 완료' }))

    expect(calls.find((c) => c.method === 'PATCH')!.body).toEqual({ student_id: 7 })
  })

  it('uploads a scan file and reports the pages read', async () => {
    const calls: Call[] = []
    stub(calls)
    const user = userEvent.setup()
    renderSection()

    await user.upload(
      screen.getByLabelText('OMR 스캔 파일'),
      new File(['%PDF'], '9월.pdf', { type: 'application/pdf' }),
    )
    await user.click(screen.getByRole('button', { name: '업로드 후 판독' }))

    expect(await screen.findByText('3쪽을 판독했습니다.')).toBeInTheDocument()
    const upload = calls.find((c) => c.method === 'POST')!
    expect(upload.url).toBe('/api/exams/5/omr/uploads')
    expect(upload.body).toBeInstanceOf(FormData)
  })
})
