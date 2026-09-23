import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { today } from '../lib/date'
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

const roster = [
  { id: 1, name: '김나윤', school: null, grade: null, phone: null, status: 'enrolled', omr_number: null },
  { id: 2, name: '김정현', school: null, grade: null, phone: null, status: 'enrolled', omr_number: null },
]

/** 반 1개·학생 2명·배정 1건(김나윤)을 주고 PATCH·POST 호출을 모아 둔다. */
function stubRoster(
  patched: { url: string; body: Record<string, unknown> }[] = [],
  posted: { url: string; body: Record<string, unknown> }[] = [],
) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      const body = init?.body ? JSON.parse(String(init.body)) : {}
      if (init?.method === 'PATCH') {
        patched.push({ url, body })
        return Response.json({ id: 11, student_id: 1, start_date: '2026-03-02', end_date: today() })
      }
      if (init?.method === 'POST') {
        posted.push({ url, body })
        return Response.json({ id: 12, ...body, end_date: null })
      }
      if (url.includes('/enrollments')) {
        // 서버는 `end_date >= on`으로 거른다. 오늘 종료한 배정은 오늘 명단에 종료일을 달고 남는다.
        return Response.json([
          {
            id: 11,
            student_id: 1,
            start_date: '2026-03-02',
            end_date: patched.length ? today() : null,
          },
        ])
      }
      return Response.json(url.includes('/students') ? roster : [active])
    }),
  )
}

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

  it('releases a member by ending the enrollment period', async () => {
    const patched: { url: string; body: Record<string, unknown> }[] = []
    stubRoster(patched)

    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: '명단' }))

    const dialog = within(await screen.findByRole('dialog'))
    expect(await dialog.findByText('김나윤')).toBeInTheDocument()
    await userEvent.click(dialog.getByRole('button', { name: '해제' }))

    await waitFor(() => expect(patched).toHaveLength(1))
    expect(patched[0].url).toBe('/api/classes/1/enrollments/11')
    expect(patched[0].body).toEqual({ end_date: today() })
    expect(await dialog.findByText(`${today()} 종료`)).toBeInTheDocument()
    expect(dialog.queryByRole('button', { name: '해제' })).not.toBeInTheDocument()
  })

  it('assigns a student who is not in the class', async () => {
    const posted: { url: string; body: Record<string, unknown> }[] = []
    stubRoster([], posted)

    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: '명단' }))

    const dialog = within(await screen.findByRole('dialog'))
    await userEvent.selectOptions(await dialog.findByLabelText('학생'), '2')
    await userEvent.click(dialog.getByRole('button', { name: '배정' }))

    await waitFor(() => expect(posted).toHaveLength(1))
    expect(posted[0].url).toBe('/api/classes/1/enrollments')
    expect(posted[0].body).toEqual({ student_id: 2, start_date: today() })
  })
})
