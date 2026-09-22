import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
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
  phone: null,
  status: 'enrolled',
  omr_number: '90000001',
}

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
})
