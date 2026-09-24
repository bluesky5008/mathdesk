import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { today } from '../lib/date'
import { ClassesPage, describeSchedules } from './ClassesPage'

describe('describeSchedules', () => {
  // 수업 길이가 같아 시작 시각만 보여 준다(FR-07, DCR-007). 종료 시각이 저장돼 있어도 쓰지 않는다
  it('shows the weekday and start time only', () => {
    expect(
      describeSchedules([{ weekday: 4, start_time: '18:00:00', end_time: '22:00:00' }]),
    ).toBe('금 18:00')
  })

  it('joins multiple schedules', () => {
    expect(
      describeSchedules([
        { weekday: 1, start_time: '18:00:00', end_time: null },
        { weekday: 5, start_time: '10:00:00', end_time: null },
      ]),
    ).toBe('화 18:00 · 토 10:00')
  })
})

// 반 등록·비활성·삭제는 원장 화면에만 있다(DCR-011). 기존 테스트는 원장 화면을 전제로 한다
function renderPage(isDirector = true) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <ClassesPage isDirector={isDirector} />
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
    // 시간표는 요일·시작 시각만 보낸다(DCR-007). 종료 시각은 쓰이지 않아 싣지 않는다
    expect(patched[0].body).toEqual({
      name: '고2 윤B',
      grade: '고2',
      teacher_id: 7,
      is_active: false,
      schedules: [{ weekday: 4, start_time: '18:00' }],
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

  // TASK-71: 지난 수업일에도 학생이 나오도록 배정 시작일을 고른다(FR-08)
  it('assigns a student from a chosen start date', async () => {
    const posted: { url: string; body: Record<string, unknown> }[] = []
    stubRoster([], posted)

    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: '명단' }))

    const dialog = within(await screen.findByRole('dialog'))
    expect(dialog.getByLabelText('시작일')).toHaveValue(today())
    await userEvent.selectOptions(await dialog.findByLabelText('학생'), '2')
    await userEvent.clear(dialog.getByLabelText('시작일'))
    await userEvent.type(dialog.getByLabelText('시작일'), '2026-09-01')
    await userEvent.click(dialog.getByRole('button', { name: '배정' }))

    await waitFor(() => expect(posted).toHaveLength(1))
    expect(posted[0].body).toEqual({ student_id: 2, start_date: '2026-09-01' })
  })

  it('keeps a future-dated assignment in the roster and drops ended ones', async () => {
    const rows = [
      { id: 21, student_id: 1, start_date: '2020-03-02', end_date: '2020-12-31' },
      { id: 22, student_id: 2, start_date: '2099-03-02', end_date: null },
    ]
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        if (url.includes('/enrollments')) {
          // 서버와 같은 기준: on이 있으면 start_date <= on <= end_date(없으면 무기한)
          const on = new URL(url, 'http://x').searchParams.get('on')
          return Response.json(
            on ? rows.filter((r) => r.start_date <= on && (!r.end_date || r.end_date >= on)) : rows,
          )
        }
        return Response.json(url.includes('/students') ? roster : [active])
      }),
    )

    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: '명단' }))

    const dialog = within(await screen.findByRole('dialog'))
    expect(await dialog.findByText('김정현')).toBeInTheDocument()
    expect(dialog.getByText('2099-03-02 배정')).toBeInTheDocument()
    expect(dialog.queryByRole('option', { name: '김정현' })).not.toBeInTheDocument()
    expect(dialog.queryByText('2020-12-31 종료')).not.toBeInTheDocument()
    expect(dialog.getByRole('option', { name: '김나윤' })).toBeInTheDocument()
  })

  // 시작 전인 배정은 종료일(오늘)이 시작일보다 앞서 해제할 수 없다. 이력이 없으니 취소(삭제)한다
  it('cancels a not-yet-started assignment instead of ending it', async () => {
    const calls: string[] = []
    let rows = [{ id: 22, student_id: 2, start_date: '2099-03-02', end_date: null as string | null }]
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        if (init?.method) calls.push(`${init.method} ${url}`)
        if (init?.method === 'DELETE') {
          rows = []
          return new Response(null, { status: 204 })
        }
        if (url.includes('/enrollments')) return Response.json(rows)
        return Response.json(url.includes('/students') ? roster : [active])
      }),
    )

    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: '명단' }))

    const dialog = within(await screen.findByRole('dialog'))
    await dialog.findByText('2099-03-02 배정')
    expect(dialog.queryByRole('button', { name: '해제' })).not.toBeInTheDocument()
    await userEvent.click(dialog.getByRole('button', { name: '취소' }))

    await waitFor(() => expect(calls).toContain('DELETE /api/classes/1/enrollments/22'))
    expect(await dialog.findByText('배정된 학생이 없습니다.')).toBeInTheDocument()
  })

  it('deactivates a class straight from the row after confirming', async () => {
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
    const confirm = vi.fn(() => true)
    vi.stubGlobal('confirm', confirm)

    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: '고2 윤B 비활성' }))

    expect(confirm).toHaveBeenCalledWith(expect.stringContaining('과거 기록은 남습니다'))
    await waitFor(() => expect(screen.queryByText(/고2 윤B/)).not.toBeInTheDocument())
    expect(patched[0].body).toEqual({
      name: '고2 윤B',
      grade: '고2',
      teacher_id: 7,
      is_active: false,
      schedules: active.schedules,
    })
  })

  it('offers no deactivate button for a class that is already inactive', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => Response.json([active, inactive])))

    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: '비활성 포함' }))

    expect(await screen.findByText(/고3 종강반/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '고3 종강반 비활성' })).not.toBeInTheDocument()
  })

  it('deletes an inactive class after the preview and name check', async () => {
    const calls: { url: string; method: string; body: unknown }[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        const method = init?.method ?? 'GET'
        calls.push({ url, method, body: init?.body ? JSON.parse(String(init.body)) : null })
        if (url.endsWith('/deletion-preview')) {
          return Response.json({
            deletable: true,
            reason: null,
            counts: { schedules: 0, enrollments: 3, sessions: 12, daily_records: 150, exams_unlinked: 1 },
          })
        }
        if (method === 'DELETE') return new Response(null, { status: 204 })
        return Response.json(calls.some((c) => c.method === 'DELETE') ? [] : [inactive])
      }),
    )

    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: '비활성 포함' }))
    await userEvent.click(await screen.findByRole('button', { name: '수정' }))
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: '삭제' }))

    const dialog = await screen.findByRole('dialog', { name: '고3 종강반 반 삭제' })
    expect(await within(dialog).findByText('학생 일일 기록 150건')).toBeInTheDocument()
    expect(within(dialog).getByText('반 연결이 끊기는 시험 1건')).toBeInTheDocument()
    await userEvent.type(within(dialog).getByLabelText('확인용 이름'), '고3 종강반')
    await userEvent.click(within(dialog).getByRole('button', { name: '영구 삭제' }))

    await waitFor(() => expect(calls.some((c) => c.method === 'DELETE' && c.url === '/api/classes/2')).toBe(true))
  })

  it('offers no delete button for an active class', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => Response.json([active])))

    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: '수정' }))

    expect(within(screen.getByRole('dialog')).queryByRole('button', { name: '삭제' })).not.toBeInTheDocument()
  })

  it('registers a class with weekday and start-time slots', async () => {
    const posted: Record<string, unknown>[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (_url: string, init?: RequestInit) => {
        if (init?.method === 'POST') {
          posted.push(JSON.parse(String(init.body)))
          return Response.json({ ...active, id: 9 }, { status: 201 })
        }
        return Response.json([])
      }),
    )

    renderPage()
    await userEvent.type(await screen.findByLabelText('반 이름'), '고1 인A')
    await userEvent.click(screen.getByRole('button', { name: '시간 추가' }))
    await userEvent.click(screen.getByRole('button', { name: '시간 추가' }))
    await userEvent.selectOptions(screen.getByLabelText('1번째 수업 요일'), '화')
    fireEvent.change(screen.getByLabelText('1번째 수업 시작 시각'), { target: { value: '18:00' } })
    await userEvent.selectOptions(screen.getByLabelText('2번째 수업 요일'), '토')
    fireEvent.change(screen.getByLabelText('2번째 수업 시작 시각'), { target: { value: '10:00' } })
    await userEvent.click(screen.getByRole('button', { name: '반 등록' }))

    await waitFor(() => expect(posted).toHaveLength(1))
    expect(posted[0].schedules).toEqual([
      { weekday: 1, start_time: '18:00' },
      { weekday: 5, start_time: '10:00' },
    ])
  })

  it('edits the schedule in the edit dialog', async () => {
    const patched: Record<string, unknown>[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (_url: string, init?: RequestInit) => {
        if (init?.method === 'PATCH') {
          patched.push(JSON.parse(String(init.body)))
          return Response.json(active)
        }
        return Response.json([active])
      }),
    )

    renderPage()
    expect(await screen.findByText(/금 18:00/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: '수정' }))
    const dialog = within(screen.getByRole('dialog'))
    await userEvent.click(dialog.getByRole('button', { name: '시간 추가' }))
    await userEvent.selectOptions(dialog.getByLabelText('2번째 수업 요일'), '토')
    fireEvent.change(dialog.getByLabelText('2번째 수업 시작 시각'), { target: { value: '10:00' } })
    await userEvent.click(dialog.getByRole('button', { name: '1번째 수업 삭제' }))
    await userEvent.click(dialog.getByRole('button', { name: '저장' }))

    await waitFor(() => expect(patched).toHaveLength(1))
    expect(patched[0]).toMatchObject({ teacher_id: 7, is_active: true, schedules: [{ weekday: 5, start_time: '10:00' }] })
  })
})

// FR-07 담당 강사 (TASK-65) — 원장만 고른다. 선택지는 같은 캠퍼스의 사용 중인 강사다
describe('teacher assignment', () => {
  const accounts = [
    { id: 1, login_id: 'director', display_name: '원장', role: 'director', is_active: true },
    { id: 7, login_id: 'kim', display_name: '김강사', role: 'teacher', is_active: true },
    { id: 8, login_id: 'lee', display_name: '이강사', role: 'teacher', is_active: true },
    { id: 9, login_id: 'park', display_name: '박강사', role: 'teacher', is_active: false },
  ]

  function stub(classes: unknown[]) {
    const sent: { method: string; url: string; body: Record<string, unknown> }[] = []
    const urls: string[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        urls.push(url)
        if (init?.method && init.method !== 'GET') {
          const body = JSON.parse(String(init.body))
          sent.push({ method: init.method, url, body })
          return Response.json({ ...active, ...body })
        }
        if (url === '/api/users') return Response.json(accounts)
        return Response.json(classes)
      }),
    )
    return { sent, urls }
  }

  function renderAsDirector() {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    return render(
      <QueryClientProvider client={client}>
        <ClassesPage isDirector />
      </QueryClientProvider>,
    )
  }

  it('offers only active teachers and sends the chosen one on create', async () => {
    const { sent } = stub([])
    renderAsDirector()

    const select = await screen.findByLabelText('담당 강사')
    await screen.findByRole('option', { name: '김강사' })
    expect(within(select).getAllByRole('option').map((o) => o.textContent)).toEqual([
      '지정 안 함',
      '김강사',
      '이강사',
    ])

    await userEvent.type(screen.getByLabelText('반 이름'), '고1 윤D')
    await userEvent.selectOptions(select, '이강사')
    await userEvent.click(screen.getByRole('button', { name: '반 등록' }))

    await waitFor(() => expect(sent).toHaveLength(1))
    expect(sent[0]).toMatchObject({ method: 'POST', url: '/api/classes', body: { teacher_id: 8 } })
  })

  it('shows the teacher name in the list and changes it in the edit dialog', async () => {
    const { sent } = stub([active])
    renderAsDirector()

    expect(await screen.findByText('고2 윤B · 고2 · 김강사')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: '수정' }))
    const dialog = within(screen.getByRole('dialog'))
    expect(dialog.getByLabelText('담당 강사')).toHaveValue('7')
    await userEvent.selectOptions(dialog.getByLabelText('담당 강사'), '지정 안 함')
    await userEvent.click(dialog.getByRole('button', { name: '저장' }))

    await waitFor(() => expect(sent).toHaveLength(1))
    expect(sent[0]).toMatchObject({ method: 'PATCH', body: { teacher_id: null } })
  })

  it('keeps a teacher who was later deactivated as the current choice', async () => {
    stub([{ ...active, teacher_id: 9 }])
    renderAsDirector()

    await screen.findByText('고2 윤B · 고2 · 박강사')
    await userEvent.click(screen.getByRole('button', { name: '수정' }))
    const select = within(screen.getByRole('dialog')).getByLabelText('담당 강사')
    expect(select).toHaveValue('9')
    expect(within(select).getByRole('option', { name: '박강사 (사용 안 함)' })).toBeInTheDocument()
  })

  it('does not ask for accounts when a teacher is signed in', async () => {
    const { urls } = stub([active])
    renderPage(false)

    await screen.findByText(/고2 윤B/)
    expect(screen.queryByLabelText('담당 강사')).not.toBeInTheDocument()
    expect(urls).not.toContain('/api/users')
  })
})

// AC-40 — 강사는 담당 반의 이름·학년·시간표만 고친다(DCR-011)
describe('teacher view', () => {
  function stubClasses(classes: unknown[]) {
    const patched: Record<string, unknown>[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (_url: string, init?: RequestInit) => {
        if (init?.method === 'PATCH') {
          patched.push(JSON.parse(String(init.body)))
          return Response.json(active)
        }
        return Response.json(classes)
      }),
    )
    return patched
  }

  it('hides what only a director can do', async () => {
    stubClasses([active])
    renderPage(false)

    await screen.findByText(/고2 윤B/)
    expect(screen.queryByRole('button', { name: '반 등록' })).not.toBeInTheDocument()
    expect(screen.queryByLabelText('반 이름')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '고2 윤B 비활성' })).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: '수정' }))
    const dialog = within(screen.getByRole('dialog'))
    expect(dialog.getByLabelText('반 이름')).toBeInTheDocument()
    expect(dialog.getByLabelText('학년')).toBeInTheDocument()
    expect(dialog.getByRole('button', { name: '시간 추가' })).toBeInTheDocument()
    expect(dialog.queryByLabelText('활성 여부')).not.toBeInTheDocument()
    expect(dialog.queryByLabelText('담당 강사')).not.toBeInTheDocument()
  })

  it('offers no delete even for an inactive class', async () => {
    stubClasses([inactive])
    renderPage(false)

    await userEvent.click(await screen.findByRole('button', { name: '수정' }))
    expect(within(screen.getByRole('dialog')).queryByRole('button', { name: '삭제' })).not.toBeInTheDocument()
  })

  it('renames the class and keeps the assignment and active state', async () => {
    const patched = stubClasses([active])
    renderPage(false)

    await userEvent.click(await screen.findByRole('button', { name: '수정' }))
    const dialog = within(screen.getByRole('dialog'))
    await userEvent.clear(dialog.getByLabelText('반 이름'))
    await userEvent.type(dialog.getByLabelText('반 이름'), '인B')
    await userEvent.click(dialog.getByRole('button', { name: '저장' }))

    await waitFor(() => expect(patched).toHaveLength(1))
    expect(patched[0]).toMatchObject({ name: '인B', teacher_id: 7, is_active: true })
  })
})
