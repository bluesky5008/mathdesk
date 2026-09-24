import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { StudentsPage } from './StudentsPage'

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <StudentsPage />
    </QueryClientProvider>,
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
})

function stubFetch(handler: (url: string, init?: RequestInit) => Response) {
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => handler(url, init)))
}

const student = {
  id: 1,
  name: '김나윤',
  school: '한영고',
  grade: '고2',
  phone: '010-1111-2222',
  status: 'enrolled',
  omr_number: '90000001',
}

const withdrawn = { ...student, id: 2, name: '박서준', status: 'withdrawn', omr_number: '90000002' }

describe('StudentsPage', () => {
  it('lists students from the API', async () => {
    stubFetch(() => Response.json([student]))

    renderPage()

    expect(await screen.findByText('김나윤')).toBeInTheDocument()
    expect(screen.getByText('90000001')).toBeInTheDocument()
  })

  it('shows the server message when the omr number is out of range', async () => {
    stubFetch((url, init) =>
      init?.method === 'POST'
        ? Response.json({ detail: '3열은 0~5만 마킹할 수 있습니다.' }, { status: 422 })
        : Response.json([]),
    )

    renderPage()
    await screen.findByRole('button', { name: '학생 등록' })
    await userEvent.type(screen.getByLabelText('이름'), '홍길동')
    await userEvent.type(screen.getByLabelText('수험번호'), '18600001')
    await userEvent.click(screen.getByRole('button', { name: '학생 등록' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('3열은 0~5만 마킹할 수 있습니다.')
  })

  it('hides withdrawn students until the filter is on', async () => {
    stubFetch(() => Response.json([student, withdrawn]))

    renderPage()

    expect(await screen.findByText('김나윤')).toBeInTheDocument()
    expect(screen.queryByText('박서준')).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: '퇴원 포함' }))

    expect(screen.getByText('박서준')).toBeInTheDocument()
  })

  it('withdraws a student through the edit dialog', async () => {
    const patched: { url: string; body: unknown }[] = []
    stubFetch((url, init) => {
      if (init?.method === 'PATCH') {
        patched.push({ url, body: JSON.parse(String(init.body)) })
        return Response.json({ ...student, status: 'withdrawn' })
      }
      return Response.json([patched.length ? { ...student, status: 'withdrawn' } : student])
    })

    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: '수정' }))

    const dialog = within(screen.getByRole('dialog'))
    await userEvent.selectOptions(dialog.getByLabelText('상태'), 'withdrawn')
    await userEvent.click(dialog.getByRole('button', { name: '저장' }))

    await waitFor(() => expect(screen.queryByText('김나윤')).not.toBeInTheDocument())
    expect(patched).toHaveLength(1)
    expect(patched[0].url).toBe('/api/students/1')
    expect(patched[0].body).toMatchObject({
      name: '김나윤',
      school: '한영고',
      phone: '010-1111-2222',
      omr_number: '90000001',
      status: 'withdrawn',
    })
  })

  it('withdraws a student straight from the row after confirming', async () => {
    const patched: { url: string; body: unknown }[] = []
    stubFetch((url, init) => {
      if (init?.method === 'PATCH') {
        patched.push({ url, body: JSON.parse(String(init.body)) })
        return Response.json({ ...student, status: 'withdrawn' })
      }
      return Response.json([patched.length ? { ...student, status: 'withdrawn' } : student])
    })
    const confirm = vi.fn(() => true)
    vi.stubGlobal('confirm', confirm)

    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: '김나윤 퇴원' }))

    expect(confirm).toHaveBeenCalledWith(expect.stringContaining('과거 기록은 남습니다'))
    await waitFor(() => expect(screen.queryByText('김나윤')).not.toBeInTheDocument())
    expect(patched[0].body).toEqual({
      name: '김나윤',
      school: '한영고',
      grade: '고2',
      phone: '010-1111-2222',
      omr_number: '90000001',
      status: 'withdrawn',
    })
  })

  it('keeps the student when the confirmation is cancelled', async () => {
    const methods: string[] = []
    stubFetch((_url, init) => {
      methods.push(init?.method ?? 'GET')
      return Response.json([student])
    })
    vi.stubGlobal('confirm', vi.fn(() => false))

    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: '김나윤 퇴원' }))

    expect(methods).not.toContain('PATCH')
    expect(screen.getByText('김나윤')).toBeInTheDocument()
  })

  it('offers no withdraw button for a student who already left', async () => {
    stubFetch(() => Response.json([withdrawn]))

    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: '퇴원 포함' }))

    expect(await screen.findByText('박서준')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '박서준 퇴원' })).not.toBeInTheDocument()
  })
})

