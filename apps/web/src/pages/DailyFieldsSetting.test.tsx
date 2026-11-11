import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'

import type { DailyFields } from '../api'
import { DailyFieldsSetting } from './DailyFieldsSetting'

afterEach(() => vi.unstubAllGlobals())

function mount(fields: DailyFields = { recheck: true, extra: [] }) {
  const calls: unknown[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (_url: string, init?: RequestInit) => {
      if (init?.method === 'PUT') {
        calls.push(JSON.parse(String(init.body)))
        return Response.json(fields)
      }
      return Response.json(fields)
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <DailyFieldsSetting />
    </QueryClientProvider>,
  )
  return calls
}

// FR-50 / AC-54 ② — 재검사를 끄고 "수업태도"를 추가한다
it('turns the recheck off and adds a field', async () => {
  const calls = mount()

  const recheck = await screen.findByRole('checkbox', { name: '이전 과제 재검사 보이기' })
  expect(recheck).toBeChecked()
  await userEvent.click(recheck)
  await userEvent.type(screen.getByLabelText('새 항목 이름'), '수업태도')
  await userEvent.click(screen.getByRole('button', { name: '항목 추가' }))
  await userEvent.click(screen.getByRole('button', { name: '일일 기록 항목 저장' }))

  expect(calls).toEqual([{ recheck: false, extra: [{ label: '수업태도' }] }])
  expect(await screen.findByRole('status')).toHaveTextContent('저장했습니다')
})

// AC-54 ⑤ — 이름을 바꾸면 id를 그대로 보내 값이 유지되고, 삭제는 확인을 거친다
it('renames a field keeping its id and deletes one after confirming', async () => {
  const confirm = vi.fn(() => true)
  vi.stubGlobal('confirm', confirm)
  const calls = mount({
    recheck: false,
    extra: [
      { id: 'x1', label: '수업태도' },
      { id: 'x2', label: '준비물' },
    ],
  })

  const name = await screen.findByLabelText('항목 1 이름')
  await userEvent.clear(name)
  await userEvent.type(name, '태도')
  await userEvent.click(screen.getByRole('button', { name: '준비물 삭제' }))
  await userEvent.click(screen.getByRole('button', { name: '일일 기록 항목 저장' }))

  expect(confirm).toHaveBeenCalledWith(expect.stringContaining('준비물'))
  expect(calls).toEqual([{ recheck: false, extra: [{ id: 'x1', label: '태도' }] }])
})

it('stops adding at five fields', async () => {
  mount({ recheck: true, extra: [1, 2, 3, 4, 5].map((n) => ({ id: `x${n}`, label: `항목${n}` })) })

  await screen.findByLabelText('항목 5 이름')
  expect(screen.getByRole('button', { name: '항목 추가' })).toBeDisabled()
})
