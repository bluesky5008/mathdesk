import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { AlimtalkSettings } from '../api'
import { AlimtalkTemplates } from './AlimtalkTemplates'

const saved: AlimtalkSettings = {
  fallback_to_sms: true,
  alimtalk: [{ code: 'TPL_DAILY_01', body: '#{학생명} 학생 수업 안내', variables: { 학생명: 'student_name' } }],
  fields: [
    { key: 'student_name', label: '학생 이름' },
    { key: 'homework', label: '오늘의 과제' },
  ],
}

type Call = { url: string; method: string; body: unknown }

function stub(calls: Call[]) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? 'GET'
      const body = init?.body ? JSON.parse(String(init.body)) : null
      calls.push({ url, method, body })
      return Response.json(method === 'PUT' ? { ...saved, ...body } : saved)
    }),
  )
}

function renderCard() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <AlimtalkTemplates />
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('AlimtalkTemplates', () => {
  it('lists approved templates and the fallback setting', async () => {
    stub([])
    renderCard()

    const table = await screen.findByRole('table', { name: '알림톡 템플릿' })
    expect(within(table).getByText('TPL_DAILY_01')).toBeInTheDocument()
    expect(within(table).getByText('#{학생명} → 학생 이름')).toBeInTheDocument()
    expect(screen.getByLabelText('알림톡이 실패하면 문자로 대체 발송')).toBeChecked()
  })

  it('adds a template and maps each variable found in the body', async () => {
    const calls: Call[] = []
    stub(calls)
    const user = userEvent.setup()
    renderCard()

    await user.click(await screen.findByRole('button', { name: '템플릿 추가' }))
    const dialog = await screen.findByRole('dialog', { name: '알림톡 템플릿' })
    await user.type(within(dialog).getByLabelText('템플릿 코드'), 'TPL_HW')
    // user-event는 {를 특수 문자로 읽는다. {{는 글자 {다
    await user.type(within(dialog).getByLabelText('승인된 템플릿 본문'), '과제: #{{과제}')
    await user.selectOptions(within(dialog).getByLabelText('#{과제}'), '오늘의 과제')
    await user.click(within(dialog).getByRole('button', { name: '저장' }))

    const put = calls.find((c) => c.method === 'PUT')!
    expect(put.url).toBe('/api/messages/templates')
    expect(put.body).toEqual({
      fallback_to_sms: true,
      alimtalk: [saved.alimtalk[0], { code: 'TPL_HW', body: '과제: #{과제}', variables: { 과제: 'homework' } }],
    })
  })

  it('turns the SMS fallback off', async () => {
    const calls: Call[] = []
    stub(calls)
    const user = userEvent.setup()
    renderCard()

    await user.click(await screen.findByLabelText('알림톡이 실패하면 문자로 대체 발송'))

    expect(calls.find((c) => c.method === 'PUT')!.body).toEqual({ fallback_to_sms: false, alimtalk: saved.alimtalk })
  })
})
