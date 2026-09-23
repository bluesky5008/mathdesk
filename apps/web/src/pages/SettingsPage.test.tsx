import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'

import type { Brand } from '../api'
import { SettingsPage } from './SettingsPage'

afterEach(() => {
  vi.unstubAllGlobals()
})

function mount(
  brand: Brand = { campus_name: '한영수학', brand_colour: null, logo_data_url: null },
) {
  const calls: { url: string; body: unknown }[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      if (init?.method === 'PUT') {
        calls.push({ url, body: JSON.parse(String(init.body)) })
        return Response.json({ ...brand, ...JSON.parse(String(init.body)) })
      }
      return Response.json(brand)
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <SettingsPage />
    </QueryClientProvider>,
  )
  return calls
}

// FR-40 — 학원명·로고·시그니처 색을 설정한다.
it('현재 브랜드 설정을 불러와 보여준다', async () => {
  mount({ campus_name: '전병훈 수학학원 고등관', brand_colour: '#C3457F', logo_data_url: null })

  // 입력란은 즉시 렌더되고 값만 나중에 채워지므로 값으로 기다린다
  await screen.findByDisplayValue('전병훈 수학학원 고등관')
  expect(screen.getByLabelText('학원명')).toHaveValue('전병훈 수학학원 고등관')
  expect(screen.getByLabelText('시그니처 색')).toHaveValue('#C3457F')
})

it('학원명과 시그니처 색을 저장한다', async () => {
  const calls = mount()

  await screen.findByDisplayValue('한영수학')
  const name = screen.getByLabelText('학원명')
  await userEvent.clear(name)
  await userEvent.type(name, '전병훈 수학학원')
  await userEvent.click(screen.getByRole('button', { name: '브랜드 저장' }))

  expect(calls).toHaveLength(1)
  expect(calls[0].body).toMatchObject({ campus_name: '전병훈 수학학원' })
})

it('로고가 없으면 학원명으로 대체된다고 알려준다', async () => {
  mount()

  expect(await screen.findByText(/로고를 올리지 않으면 학원명/)).toBeInTheDocument()
})
