import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ClassesPage, describeSchedules } from './ClassesPage'

describe('describeSchedules', () => {
  it('formats weekday and time range', () => {
    expect(
      describeSchedules([{ weekday: 4, start_time: '18:00:00', end_time: '22:00:00' }]),
    ).toBe('금 18:00~22:00')
  })

  it('joins multiple schedules', () => {
    expect(
      describeSchedules([
        { weekday: 1, start_time: '18:00:00', end_time: '22:00:00' },
        { weekday: 5, start_time: '10:00:00', end_time: '13:00:00' },
      ]),
    ).toBe('화 18:00~22:00, 토 10:00~13:00')
  })
})

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <ClassesPage />
    </QueryClientProvider>,
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
})

const active = {
  id: 1,
  name: '고2 윤B',
  grade: '고2',
  teacher_id: 7,
  is_active: true,
  schedules: [{ weekday: 4, start_time: '18:00:00', end_time: '22:00:00' }],
}

const inactive = { ...active, id: 2, name: '고3 종강반', is_active: false, schedules: [] }

describe('ClassesPage', () => {
  it('hides inactive classes until the filter is on', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) =>
        Response.json(url.includes('include_inactive=true') ? [active, inactive] : [active]),
      ),
    )

    renderPage()

    expect(await screen.findByText(/고2 윤B/)).toBeInTheDocument()
    expect(screen.queryByText(/고3 종강반/)).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: '비활성 포함' }))

    expect(await screen.findByText(/고3 종강반/)).toBeInTheDocument()
  })

  it('deactivates a class without dropping its schedules', async () => {
    const patched: { url: string; body: Record<string, unknown> }[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        if (init?.method === 'PATCH') {
          patched.push({ url, body: JSON.parse(String(init.body)) })
          return Response.json({ ...active, is_active: false })
        }
        return Response.json(patched.length ? [] : [active])
      }),
    )

    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: '수정' }))

    const dialog = within(screen.getByRole('dialog'))
    await userEvent.selectOptions(dialog.getByLabelText('활성 여부'), 'false')
    await userEvent.click(dialog.getByRole('button', { name: '저장' }))

    await waitFor(() => expect(screen.queryByText(/고2 윤B/)).not.toBeInTheDocument())
    expect(patched).toHaveLength(1)
    expect(patched[0].url).toBe('/api/classes/1')
    expect(patched[0].body).toEqual({
      name: '고2 윤B',
      grade: '고2',
      teacher_id: 7,
      is_active: false,
      schedules: active.schedules,
    })
  })
})
