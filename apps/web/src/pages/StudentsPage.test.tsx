import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { dayBefore, today } from '../lib/date'
import { StudentsPage } from './StudentsPage'

function renderPage(props: { isDirector?: boolean } = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <StudentsPage {...props} />
      </MemoryRouter>
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
  school_id: 3 as number | null,
  school: '한영고' as string | null,
  grade: '고2',
  phone: '010-1111-2222',
  status: 'enrolled',
  omr_number: '90000001',
  guardian_phone: '010-7777-8888' as string | null,
  score_note: '중간 85' as string | null,
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
      school_id: 3,
      phone: '010-1111-2222',
      omr_number: '90000001',
      status: 'withdrawn',
      guardian_phone: '010-7777-8888',
      score_note: '중간 85',
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
      school_id: 3,
      grade: '고2',
      phone: '010-1111-2222',
      omr_number: '90000001',
      status: 'withdrawn',
      guardian_phone: '010-7777-8888',
      score_note: '중간 85',
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

  // DCR-013: 학생 [삭제]는 확인 없이 바로 하드 삭제한다(기준선 v14)
  function stubDelete(rows: (typeof student)[]) {
    const calls: { url: string; method: string; body: unknown }[] = []
    stubFetch((url, init) => {
      const method = init?.method ?? 'GET'
      calls.push({ url, method, body: init?.body ?? null })
      if (method === 'DELETE') return new Response(null, { status: 204 })
      if (url === '/api/schools') return Response.json([])
      const deleted = calls.filter((c) => c.method === 'DELETE').map((c) => c.url)
      return Response.json(rows.filter((row) => !deleted.includes(`/api/students/${row.id}`)))
    })
    return calls
  }

  it('deletes a student straight from the row without asking', async () => {
    const calls = stubDelete([student, withdrawn])
    const confirm = vi.fn(() => true)
    vi.stubGlobal('confirm', confirm)
    renderPage({ isDirector: true })

    await userEvent.click(await screen.findByRole('button', { name: '김나윤 삭제' }))

    await waitFor(() => expect(screen.queryByText('김나윤')).not.toBeInTheDocument())
    expect(calls.filter((c) => c.method === 'DELETE')).toEqual([
      { url: '/api/students/1', method: 'DELETE', body: null },
    ])
    expect(confirm).not.toHaveBeenCalled()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('deletes a student from the edit dialog right away', async () => {
    const calls = stubDelete([withdrawn])
    renderPage({ isDirector: true })

    await userEvent.click(await screen.findByRole('button', { name: '퇴원 포함' }))
    await userEvent.click(await screen.findByRole('button', { name: '수정' }))
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: '삭제' }))

    await waitFor(() => expect(screen.queryByText('박서준')).not.toBeInTheDocument())
    expect(calls.filter((c) => c.method === 'DELETE').map((c) => c.url)).toEqual(['/api/students/2'])
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('offers delete on every row and in the edit dialog to directors only', async () => {
    stubFetch(() => Response.json([student, withdrawn]))
    const { unmount } = renderPage({ isDirector: true })

    await userEvent.click(await screen.findByRole('button', { name: '퇴원 포함' }))
    expect(screen.getByRole('button', { name: '김나윤 삭제' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '박서준 삭제' })).toBeInTheDocument()
    await userEvent.click(screen.getAllByRole('button', { name: '수정' })[0])
    expect(within(screen.getByRole('dialog')).getByRole('button', { name: '삭제' })).toBeInTheDocument()
    unmount()

    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: '퇴원 포함' }))
    expect(screen.queryByRole('button', { name: /삭제$/ })).not.toBeInTheDocument()
    await userEvent.click(screen.getAllByRole('button', { name: '수정' })[1])
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
  return {
    name: s.name,
    school_id: s.school_id,
    grade: s.grade,
    phone: s.phone,
    omr_number: s.omr_number,
    status: s.status,
    guardian_phone: s.guardian_phone,
    score_note: s.score_note,
  }
}

// TASK-82: 학부모 연락처와 성적을 등록 한 줄·수정 창에서 넣고 목록 열에 보인다(DCR-014, AC-41)
describe('StudentsPage guardian phone and score note', () => {
  function stubWrites(rows = [student]) {
    const writes: { method: string; body: Record<string, unknown> }[] = []
    stubFetch((url, init) => {
      if (init?.method === 'POST' || init?.method === 'PATCH') {
        writes.push({ method: init.method, body: JSON.parse(String(init.body)) })
        return Response.json(student)
      }
      return Response.json(url.includes('/students') ? rows : [])
    })
    return writes
  }

  it('registers guardian phone and score note from the one-line form', async () => {
    const writes = stubWrites([])
    renderPage({ isDirector: true })

    await userEvent.type(await screen.findByLabelText('이름'), '홍길동')
    await userEvent.type(screen.getByLabelText('학생 연락처'), '010-1234-5678')
    await userEvent.type(screen.getByLabelText('학부모 연락처'), '010-8765-4321')
    await userEvent.type(screen.getByLabelText('성적'), '모의 3등급')
    await userEvent.click(screen.getByRole('button', { name: '학생 등록' }))

    await waitFor(() =>
      expect(writes[0]?.body).toMatchObject({
        name: '홍길동',
        phone: '010-1234-5678',
        guardian_phone: '010-8765-4321',
        score_note: '모의 3등급',
      }),
    )
  })

  it('edits guardian phone and score note in the edit dialog', async () => {
    const writes = stubWrites()
    renderPage({ isDirector: true })

    await userEvent.click(await screen.findByRole('button', { name: '수정' }))
    const dialog = within(screen.getByRole('dialog'))
    expect(dialog.getByLabelText('학부모 연락처')).toHaveValue('010-7777-8888')
    expect(dialog.getByLabelText('성적')).toHaveValue('중간 85')
    await userEvent.clear(dialog.getByLabelText('학부모 연락처'))
    await userEvent.clear(dialog.getByLabelText('성적'))
    await userEvent.type(dialog.getByLabelText('성적'), '기말 92')
    await userEvent.click(dialog.getByRole('button', { name: '저장' }))

    await waitFor(() => expect(writes[0]?.body).toMatchObject({ guardian_phone: null, score_note: '기말 92' }))
  })

  it('shows student phone, guardian phone and score note as columns', async () => {
    const note = '중간 85, 서술형 감점 많음. 다음 달 상담 때 오답 노트 확인하기로 함'
    stubWrites([{ ...student, score_note: note }])
    renderPage()

    for (const header of ['학생 연락처', '학부모 연락처', '성적']) {
      expect(screen.getByRole('columnheader', { name: header })).toBeInTheDocument()
    }
    const row = within(await screen.findByRole('row', { name: /김나윤/ }))
    expect(row.getByText('010-1111-2222')).toBeInTheDocument()
    expect(row.getByText('010-7777-8888')).toBeInTheDocument()
    expect(row.getByText(note)).toHaveAttribute('title', note)
  })
})

// TASK-83: 학교는 등록된 학교 중에서 고른다(DCR-015, FR-05, AC-42)
describe('StudentsPage school dropdown', () => {
  const schools = [
    { id: 4, name: '대명고', student_count: 0 },
    { id: 3, name: '한영고', student_count: 1 },
  ]

  function stubWrites(rows = [student], registered = schools) {
    const writes: { method: string; body: Record<string, unknown> }[] = []
    const urls: string[] = []
    stubFetch((url, init) => {
      urls.push(url)
      if (init?.method === 'POST' || init?.method === 'PATCH') {
        writes.push({ method: init.method, body: JSON.parse(String(init.body)) })
        return Response.json(student)
      }
      if (url === '/api/schools') return Response.json(registered)
      return Response.json(url.includes('/students') ? rows : [])
    })
    return { writes, urls }
  }

  const optionsOf = (select: HTMLElement) =>
    within(select).getAllByRole('option').map((option) => option.textContent)

  it('picks a registered school when registering', async () => {
    const { writes } = stubWrites([])
    renderPage({ isDirector: true })

    const school = screen.getByLabelText('학교')
    await waitFor(() => expect(optionsOf(school)).toEqual(['선택', '대명고', '한영고']))
    await userEvent.type(screen.getByLabelText('이름'), '홍길동')
    await userEvent.selectOptions(school, '대명고')
    await userEvent.click(screen.getByRole('button', { name: '학생 등록' }))

    await waitFor(() => expect(writes[0]?.body).toMatchObject({ name: '홍길동', school_id: 4 }))
    expect(writes[0].body).not.toHaveProperty('school')
  })

  it('registers without a school when none is picked', async () => {
    const { writes } = stubWrites([])
    renderPage({ isDirector: true })

    await userEvent.type(await screen.findByLabelText('이름'), '홍길동')
    await userEvent.click(screen.getByRole('button', { name: '학생 등록' }))

    await waitFor(() => expect(writes[0]?.body).toMatchObject({ name: '홍길동', school_id: null }))
  })

  it('shows the current school in the edit dialog and saves a new pick', async () => {
    const { writes } = stubWrites()
    renderPage({ isDirector: true })

    await userEvent.click(await screen.findByRole('button', { name: '수정' }))
    const school = within(screen.getByRole('dialog')).getByLabelText('학교')
    await waitFor(() => expect(school).toHaveValue('3'))
    await userEvent.selectOptions(school, '대명고')
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: '저장' }))

    await waitFor(() => expect(writes[0]?.body).toMatchObject({ school_id: 4 }))
  })

  it('points to the school tab when no school is registered yet', async () => {
    stubWrites([], [])
    renderPage({ isDirector: true })

    const link = await screen.findByRole('link', { name: '학교 탭' })
    expect(link).toHaveAttribute('href', '/students/schools')
    expect(link.closest('p')).toHaveTextContent('학교 탭에서 먼저 학교를 등록하세요')
  })

  it('does not ask teachers for the school list but keeps showing school names', async () => {
    const { urls } = stubWrites()
    renderPage()

    const row = within(await screen.findByRole('row', { name: /김나윤/ }))
    expect(row.getByText('한영고')).toBeInTheDocument()
    expect(urls).not.toContain('/api/schools')
    expect(screen.queryByRole('link', { name: '학교 탭' })).not.toBeInTheDocument()
  })
})
