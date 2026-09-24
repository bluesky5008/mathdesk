import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'

import { ClassesPage } from './ClassesPage'
import { StudentsPage } from './StudentsPage'

const students = Array.from({ length: 47 }, (_, index) => ({
  id: index + 1,
  name: `학생${index + 1}`,
  school: '한영고',
  grade: '고2',
  phone: null,
  status: 'enrolled',
  omr_number: `1000${String(index + 1).padStart(2, '0')}00`,
}))

const classes = ['고3 윤A', '고2 윤B', '고2 윤C', '고1 윤D'].map((name, index) => ({
  id: index + 1,
  name,
  grade: '고2',
  teacher_id: 1,
  is_active: true,
  schedules: [{ weekday: 4, start_time: '18:00:00', end_time: '22:00:00' }],
}))

afterEach(() => {
  vi.unstubAllGlobals()
})

// AC-05: 반 4개와 학생 47명이 화면 목록에 그대로 반영되는지.
it('renders the seeded roster of 47 students in 4 classes', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) =>
      Response.json(url.includes('/students') ? students : classes),
    ),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })

  render(
    <QueryClientProvider client={client}>
      <StudentsPage />
      <ClassesPage />
    </QueryClientProvider>,
  )

  expect(await screen.findByText('총 47명')).toBeInTheDocument()
  expect(await screen.findByText('활성 4개 반')).toBeInTheDocument()
  expect(screen.getByText('고2 윤B · 고2 · 금 18:00')).toBeInTheDocument()
})
