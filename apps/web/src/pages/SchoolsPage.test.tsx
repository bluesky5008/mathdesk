import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { SchoolsPage } from './SchoolsPage'

afterEach(() => {
  vi.unstubAllGlobals()
})

const schools = [
  { id: 4, name: '대명고', student_count: 0 },
  { id: 3, name: '한영고', student_count: 12 },
]

type Call = { method: string; url: string; body?: unknown }

function stub(handler?: (call: Call) => Response | undefined) {
  const calls: Call[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      const call = { method: init?.method ?? 'GET', url, body: init?.body ? JSON.parse(String(init.body)) : undefined }
      calls.push(call)
      return handler?.(call) ?? (call.method === 'DELETE' ? new Response(null, { status: 204 }) : Response.json(schools))
    }),
  )
  return calls
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <SchoolsPage />
    </QueryClientProvider>,
  )
}

const writes = (calls: Call[]) => calls.filter((call) => call.method !== 'GET')

// TASK-83: 원장이 학교를 등록·수정·삭제한다(DCR-015, FR-43, AC-42)
describe('SchoolsPage', () => {
  it('lists schools with their student count', async () => {
    stub()
    renderPage()

    const row = within(await screen.findByRole('row', { name: /한영고/ }))
    expect(row.getByText('12')).toBeInTheDocument()
    expect(screen.getByRole('row', { name: /대명고/ })).toBeInTheDocument()
  })

  it('registers a school from the one-line form', async () => {
    const calls = stub()
    renderPage()

    await userEvent.type(await screen.findByLabelText('학교 이름'), '서현고')
    await userEvent.click(screen.getByRole('button', { name: '학교 등록' }))

    await waitFor(() => expect(writes(calls)).toEqual([{ method: 'POST', url: '/api/schools', body: { name: '서현고' } }]))
    await waitFor(() => expect(screen.getByLabelText('학교 이름')).toHaveValue(''))
  })

  it('shows the server message when the name is taken', async () => {
    stub((call) =>
      call.method === 'POST' ? Response.json({ detail: '이미 등록된 학교입니다.' }, { status: 409 }) : undefined,
    )
    renderPage()

    await userEvent.type(await screen.findByLabelText('학교 이름'), '한영고')
    await userEvent.click(screen.getByRole('button', { name: '학교 등록' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('이미 등록된 학교입니다.')
  })

  it('renames a school in its row', async () => {
    const calls = stub()
    renderPage()

    await userEvent.click(await screen.findByRole('button', { name: '한영고 수정' }))
    const input = screen.getByLabelText('한영고 새 이름')
    expect(input).toHaveValue('한영고')
    await userEvent.clear(input)
    await userEvent.type(input, '한영외고')
    await userEvent.click(screen.getByRole('button', { name: '저장' }))

    await waitFor(() =>
      expect(writes(calls)).toEqual([{ method: 'PATCH', url: '/api/schools/3', body: { name: '한영외고' } }]),
    )
    await waitFor(() => expect(screen.queryByLabelText('한영고 새 이름')).not.toBeInTheDocument())
  })

  it('cancels a rename without saving', async () => {
    const calls = stub()
    renderPage()

    await userEvent.click(await screen.findByRole('button', { name: '한영고 수정' }))
    await userEvent.click(screen.getByRole('button', { name: '취소' }))

    expect(screen.queryByLabelText('한영고 새 이름')).not.toBeInTheDocument()
    expect(writes(calls)).toEqual([])
  })

  it('deletes a school right away without asking', async () => {
    const confirm = vi.fn(() => true)
    vi.stubGlobal('confirm', confirm)
    const calls = stub()
    renderPage()

    await userEvent.click(await screen.findByRole('button', { name: '한영고 삭제' }))

    await waitFor(() => expect(writes(calls)).toEqual([{ method: 'DELETE', url: '/api/schools/3', body: undefined }]))
    expect(confirm).not.toHaveBeenCalled()
  })
})
