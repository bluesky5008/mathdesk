import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'

import { ClassMinutesSetting } from './ClassMinutesSetting'

afterEach(() => {
  vi.unstubAllGlobals()
})

// FR-42 — 원장이 학원의 수업 길이를 바꾼다(주간 시간표 블록 길이)
it('shows the current class length and saves a new one', async () => {
  const sent: { url: string; method?: string; body: unknown }[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      if (init?.method === 'PUT') {
        sent.push({ url, method: init.method, body: JSON.parse(String(init.body)) })
        return Response.json(JSON.parse(String(init.body)))
      }
      return Response.json({ class_minutes: 120, slots: [], unscheduled: [] })
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <ClassMinutesSetting />
    </QueryClientProvider>,
  )

  const input = await screen.findByDisplayValue('120')
  await userEvent.clear(input)
  await userEvent.type(input, '90')
  await userEvent.click(screen.getByRole('button', { name: '수업 길이 저장' }))

  expect(sent).toEqual([
    { url: '/api/settings/class-minutes', method: 'PUT', body: { class_minutes: 90 } },
  ])
  expect(await screen.findByRole('status')).toHaveTextContent('저장했습니다')
})
