import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { dayBefore, today } from '../lib/date'
import { StudentsPage } from './StudentsPage'

function renderPage(props: { isDirector?: boolean } = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <StudentsPage {...props} />
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
  // TASK-72: 탭 분리 뒤 학생 소속을 목록에서 바로 본다(사용자 결정 2026-09-25)
  it('shows the classes each student is assigned to today', async () => {
    const third = { ...student, id: 3, name: '이하준', omr_number: '90000003' }
    const classes = [
      { id: 5, name: '고1 인A', grade: '1', teacher_id: 1, is_active: true, schedules: [] },
      { id: 6, name: '고1 인B', grade: '1', teacher_id: 1, is_active: true, schedules: [] },
      { id: 2, name: '고2 윤B', grade: '고2', teacher_id: 1, is_active: false, schedules: [] },
    ]
    const members: Record<string, number[]> = { '5': [1], '6': [1], '2': [2] }
    stubFetch((url) => {
      const roster = url.match(/\/classes\/(\d+)\/enrollments\?on=/)
      if (roster) {
        return Response.json(
          members[roster[1]].map((id) => ({ id, student_id: id, start_date: '2026-03-02', end_date: null })),
        )
      }
      if (url.includes('/classes?include_inactive=true')) return Response.json(classes)
      return Response.json([student, { ...withdrawn, status: 'enrolled' }, third])
    })

    renderPage()

    expect(screen.getByRole('columnheader', { name: '반' })).toBeInTheDocument()
    const first = within(await screen.findByRole('row', { name: /김나윤/ }))
    expect(await first.findByText('고1 인A, 고1 인B')).toBeInTheDocument()
    const second = within(screen.getByRole('row', { name: /박서준/ }))
    expect(second.getByText('고2 윤B (비활성)')).toBeInTheDocument()
    expect(within(screen.getByRole('row', { name: /이하준/ })).getByText('미배정')).toBeInTheDocument()
  })

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

  it('deletes a withdrawn student after showing what goes with them and checking the name', async () => {
    const calls: { url: string; method: string; body: unknown }[] = []
    stubFetch((url, init) => {
      const method = init?.method ?? 'GET'
      calls.push({ url, method, body: init?.body ? JSON.parse(String(init.body)) : null })
      if (url.endsWith('/deletion-preview')) {
        return Response.json({
          deletable: true,
          reason: null,
          counts: { guardians: 1, enrollments: 1, daily_records: 24, exam_attempts: 2, omr_scans: 2, messages: 15, consults: 3 },
        })
      }
      if (method === 'DELETE') return new Response(null, { status: 204 })
      return Response.json(calls.some((c) => c.method === 'DELETE') ? [] : [withdrawn])
    })

    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: '퇴원 포함' }))
    await userEvent.click(await screen.findByRole('button', { name: '수정' }))
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: '삭제' }))

    const dialog = await screen.findByRole('dialog', { name: '박서준 학생 삭제' })
    expect(await within(dialog).findByText('출결·과제 기록 24건')).toBeInTheDocument()
    expect(within(dialog).getByText(/되돌릴 수 없습니다/)).toBeInTheDocument()
    const confirm = within(dialog).getByRole('button', { name: '영구 삭제' })
    expect(confirm).toBeDisabled()
    await userEvent.type(within(dialog).getByLabelText('확인용 이름'), '박서준')
    await userEvent.click(confirm)

    await waitFor(() => expect(screen.queryByText('박서준')).not.toBeInTheDocument())
    expect(calls.find((c) => c.method === 'DELETE')).toEqual({
      url: '/api/students/2',
      method: 'DELETE',
      body: { confirm_name: '박서준' },
    })
  })

  it('offers no delete button while the student is still enrolled', async () => {
    stubFetch(() => Response.json([student]))

    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: '수정' }))

    expect(within(screen.getByRole('dialog')).queryByRole('button', { name: '삭제' })).not.toBeInTheDocument()
  })
})

// TASK-78: 학생 목록의 반 칸에서 바로 반을 배정·해제한다(클라이언트 요구, 사용자 결정 2026-10-11)
describe('StudentsPage class picker', () => {
  const classes = [
    { id: 5, name: '고1 인A', grade: '1', teacher_id: 1, is_active: true, schedules: [] },
    { id: 6, name: '고1 인B', grade: '1', teacher_id: 1, is_active: true, schedules: [] },
    { id: 2, name: '고2 윤B', grade: '고2', teacher_id: 1, is_active: false, schedules: [] },
  ]

  /** 김나윤을 고1 인A(배정 11)에 두고, 쓰기 요청을 모아 둔다. */
  function stubRoster(startDate = '2026-03-02') {
    const calls: { method: string; url: string; body: unknown }[] = []
    stubFetch((url, init) => {
      if (init?.method && init.method !== 'GET') {
        calls.push({ method: init.method, url, body: init.body ? JSON.parse(String(init.body)) : null })
        return init.method === 'DELETE' ? new Response(null, { status: 204 }) : Response.json({})
      }
      const roster = url.match(/\/classes\/(\d+)\/enrollments\?on=/)
      if (roster) {
        return Response.json(
          roster[1] === '5' ? [{ id: 11, student_id: 1, start_date: startDate, end_date: null }] : [],
        )
      }
      if (url.includes('/classes?include_inactive=true')) return Response.json(classes)
      return Response.json([student, withdrawn])
    })
    return calls
  }

  async function openPicker() {
    const row = within(await screen.findByRole('row', { name: /김나윤/ }))
    await userEvent.click(await row.findByRole('button', { name: /고1 인A/ }))
    return row
  }

  it('lists active classes with the current ones checked', async () => {
    stubRoster()
    renderPage({ isDirector: true })

    const row = await openPicker()

    expect(row.getByRole('checkbox', { name: '고1 인A' })).toBeChecked()
    expect(row.getByRole('checkbox', { name: '고1 인B' })).not.toBeChecked()
    expect(row.queryByRole('checkbox', { name: '고2 윤B' })).not.toBeInTheDocument()
  })

  it('assigns a checked class from today', async () => {
    const calls = stubRoster()
    renderPage({ isDirector: true })

    const row = await openPicker()
    await userEvent.click(row.getByRole('checkbox', { name: '고1 인B' }))

    await waitFor(() =>
      expect(calls).toEqual([
        { method: 'POST', url: '/api/classes/6/enrollments', body: { student_id: 1, start_date: today() } },
      ]),
    )
  })

  it('releases an unchecked class from today on, after confirming', async () => {
    const calls = stubRoster()
    const confirm = vi.fn(() => true)
    vi.stubGlobal('confirm', confirm)
    renderPage({ isDirector: true })

    const row = await openPicker()
    await userEvent.click(row.getByRole('checkbox', { name: '고1 인A' }))

    expect(confirm).toHaveBeenCalledWith(expect.stringContaining('오늘 수업부터'))
    await waitFor(() =>
      expect(calls).toEqual([
        { method: 'PATCH', url: '/api/classes/5/enrollments/11', body: { end_date: dayBefore(today()) } },
      ]),
    )
  })

  it('removes an assignment that starts today when it is unchecked', async () => {
    const calls = stubRoster(today())
    vi.stubGlobal('confirm', vi.fn(() => true))
    renderPage({ isDirector: true })

    const row = await openPicker()
    await userEvent.click(row.getByRole('checkbox', { name: '고1 인A' }))

    await waitFor(() =>
      expect(calls).toEqual([{ method: 'DELETE', url: '/api/classes/5/enrollments/11', body: null }]),
    )
  })

  it('keeps the class when the release is not confirmed', async () => {
    const calls = stubRoster()
    vi.stubGlobal('confirm', vi.fn(() => false))
    renderPage({ isDirector: true })

    const row = await openPicker()
    await userEvent.click(row.getByRole('checkbox', { name: '고1 인A' }))

    expect(row.getByRole('checkbox', { name: '고1 인A' })).toBeChecked()
    expect(calls).toEqual([])
  })

  it('offers no picker to teachers or for withdrawn students', async () => {
    stubRoster()
    const { unmount } = renderPage()

    const row = within(await screen.findByRole('row', { name: /김나윤/ }))
    expect(await row.findByText('고1 인A')).toBeInTheDocument()
    expect(row.queryByRole('button', { name: /고1 인A/ })).not.toBeInTheDocument()
    unmount()

    renderPage({ isDirector: true })
    await userEvent.click(await screen.findByRole('button', { name: '퇴원 포함' }))
    const left = within(await screen.findByRole('row', { name: /박서준/ }))
    expect(left.queryByRole('button', { name: /미배정/ })).not.toBeInTheDocument()
  })
})

// TASK-79: 학년은 고르고, 목록에서 학년·상태를 바로 바꾼다(클라이언트 요구, 사용자 결정 2026-10-11)
describe('StudentsPage grade and status dropdowns', () => {
  function stubWrites(rows = [student]) {
    const writes: { method: string; url: string; body: unknown }[] = []
    stubFetch((url, init) => {
      if (init?.method === 'POST' || init?.method === 'PATCH') {
        writes.push({ method: init.method, url, body: JSON.parse(String(init.body)) })
        return Response.json(student)
      }
      return Response.json(url.includes('/students') ? rows : [])
    })
    return writes
  }

  it('picks the grade from a fixed list when registering', async () => {
    const writes = stubWrites([])
    renderPage({ isDirector: true })

    const grade = await screen.findByLabelText('학년')
    expect(within(grade).getAllByRole('option').map((option) => option.textContent)).toEqual([
      '선택',
      '예비고1',
      '고1',
      '고2',
      '고3',
    ])
    await userEvent.type(screen.getByLabelText('이름'), '홍길동')
    await userEvent.selectOptions(grade, '예비고1')
    await userEvent.click(screen.getByRole('button', { name: '학생 등록' }))

    await waitFor(() => expect(writes[0]?.body).toMatchObject({ name: '홍길동', grade: '예비고1' }))
  })

  it('keeps a grade outside the list when editing', async () => {
    stubWrites([{ ...student, grade: '중3' }])
    renderPage({ isDirector: true })

    await userEvent.click(await screen.findByRole('button', { name: '수정' }))

    expect(within(screen.getByRole('dialog')).getByLabelText('학년')).toHaveValue('중3')
  })

  it('changes grade and status straight from the row', async () => {
    const writes = stubWrites()
    renderPage({ isDirector: true })

    await userEvent.selectOptions(await screen.findByLabelText('김나윤 학년'), '고3')
    await waitFor(() => expect(writes).toHaveLength(1))
    await userEvent.selectOptions(screen.getByLabelText('김나윤 상태'), 'paused')

    await waitFor(() => expect(writes).toHaveLength(2))
    expect(writes[0]).toEqual({
      method: 'PATCH',
      url: '/api/students/1',
      body: { ...toPayloadOf(student), grade: '고3' },
    })
    expect(writes[1].body).toEqual({ ...toPayloadOf(student), status: 'paused' })
  })

  it('asks before withdrawing from the status dropdown', async () => {
    const writes = stubWrites()
    const confirm = vi.fn(() => false)
    vi.stubGlobal('confirm', confirm)
    renderPage({ isDirector: true })

    const status = await screen.findByLabelText('김나윤 상태')
    await userEvent.selectOptions(status, 'withdrawn')

    expect(confirm).toHaveBeenCalledWith(expect.stringContaining('과거 기록은 남습니다'))
    expect(status).toHaveValue('enrolled')
    expect(writes).toEqual([])

    confirm.mockReturnValue(true)
    await userEvent.selectOptions(status, 'withdrawn')
    await waitFor(() => expect(writes[0]?.body).toEqual({ ...toPayloadOf(student), status: 'withdrawn' }))
  })

  it('shows plain grade and status to teachers', async () => {
    stubWrites()
    renderPage()

    const row = within(await screen.findByRole('row', { name: /김나윤/ }))
    expect(row.getByText('고2')).toBeInTheDocument()
    expect(row.getByText('재원')).toBeInTheDocument()
    expect(row.queryByRole('combobox')).not.toBeInTheDocument()
  })
})

function toPayloadOf(s: typeof student) {
  return { name: s.name, school: s.school, grade: s.grade, phone: s.phone, omr_number: s.omr_number, status: s.status }
}
