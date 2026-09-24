import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'

import type { Timetable } from '../api'
import { TimetablePage } from './TimetablePage'

afterEach(() => {
  vi.unstubAllGlobals()
})

const kim = { id: 7, name: '김강사' }
const lee = { id: 8, name: '이강사' }

function slot(
  class_id: number,
  class_name: string,
  teacher: { id: number; name: string } | null,
  weekday: number,
  start_time: string,
  end_time: string,
) {
  return { class_id, class_name, grade: '고2', teacher, weekday, start_time, end_time }
}

const TIMETABLE: Timetable = {
  class_minutes: 120,
  slots: [
    slot(1, '고2 윤B', kim, 1, '18:00:00', '20:00:00'),
    slot(2, '고3 윤A', lee, 1, '19:00:00', '21:00:00'),
    slot(1, '고2 윤B', kim, 4, '18:00:00', '20:00:00'),
    slot(3, '고1 윤D', null, 5, '10:00:00', '12:00:00'),
  ],
  unscheduled: [{ class_id: 4, class_name: '중3 특강', grade: '중3', teacher: null }],
}

function mount(isDirector: boolean, data: Timetable = TIMETABLE) {
  vi.stubGlobal('fetch', vi.fn(async () => Response.json(data)))
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <TimetablePage isDirector={isDirector} />
    </QueryClientProvider>,
  )
}

async function grid() {
  return within(await screen.findByRole('region', { name: '주간 시간표 격자' }))
}

function block(scope: ReturnType<typeof within>, weekday: string, name: string) {
  return within(scope.getByRole('list', { name: `${weekday}요일 수업` }))
    .getAllByRole('listitem')
    .find((item) => item.textContent?.includes(name))!
}

// AC-38 — 요일 열에 시작 시각부터 수업 길이만큼 블록을 그린다
it('draws each class in its weekday column for the class length', async () => {
  mount(false)
  const g = await grid()

  // 시간 축은 가장 이른 시작(10시)부터 가장 늦은 끝(21시)까지
  const tuesday = block(g, '화', '고2 윤B')
  expect(tuesday).toHaveTextContent('18:00~20:00')
  expect(tuesday.style.top).toBe(`${8 * 60}px`)
  expect(tuesday.style.height).toBe('120px')
  expect(block(g, '금', '고2 윤B').style.top).toBe(`${8 * 60}px`)
  expect(block(g, '토', '고1 윤D').style.top).toBe('0px')
  expect(within(g.getByRole('list', { name: '시각' })).getAllByRole('listitem').map((h) => h.textContent)).toEqual(
    ['10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20'].map((h) => `${h}:00`),
  )
})

it('puts overlapping classes side by side', async () => {
  mount(false)
  const g = await grid()

  const first = block(g, '화', '고2 윤B')
  const second = block(g, '화', '고3 윤A')
  expect(first.style.width).toBe('50%')
  expect(second.style.width).toBe('50%')
  expect(first.style.left).not.toBe(second.style.left)
  expect(block(g, '금', '고2 윤B').style.width).toBe('100%')
})

it('lists classes without a schedule separately', async () => {
  mount(false)

  const section = await screen.findByRole('region', { name: '시간표 미등록' })
  expect(section).toHaveTextContent('중3 특강')
})

it('switches to a day-by-day list on narrow screens', async () => {
  mount(false)

  const list = within(await screen.findByRole('region', { name: '요일별 시간표' }))
  expect(list.getAllByRole('heading').map((h) => h.textContent)).toEqual(['화', '금', '토'])
  expect(list.getByText(/19:00~21:00/)).toBeInTheDocument()
})

it('does not show a teacher filter or names to a teacher', async () => {
  mount(false)
  await grid()

  expect(screen.queryByLabelText('강사')).not.toBeInTheDocument()
  expect(screen.queryByText(/김강사/)).not.toBeInTheDocument()
})

// AC-38 ② — 원장은 강사 이름을 보고 강사별로 거른다
it('lets a director filter by teacher', async () => {
  mount(true)
  const g = await grid()
  expect(block(g, '화', '고2 윤B')).toHaveTextContent('김강사')

  await userEvent.selectOptions(screen.getByLabelText('강사'), '이강사')

  expect(within(g.getByRole('list', { name: '화요일 수업' })).getAllByRole('listitem')).toHaveLength(1)
  expect(block(g, '화', '고3 윤A').style.width).toBe('100%')
  expect(within(g.getByRole('list', { name: '금요일 수업' })).queryAllByRole('listitem')).toHaveLength(0)

  await userEvent.selectOptions(screen.getByLabelText('강사'), '담당 없음')
  expect(within(g.getByRole('list', { name: '토요일 수업' })).getAllByRole('listitem')).toHaveLength(1)
  expect(screen.getByRole('region', { name: '시간표 미등록' })).toHaveTextContent('중3 특강')
})

it('says so when nothing is scheduled', async () => {
  mount(false, { class_minutes: 120, slots: [], unscheduled: [] })

  expect(await screen.findByText('등록된 수업이 없습니다')).toBeInTheDocument()
})
