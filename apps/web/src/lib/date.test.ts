import { afterEach, expect, it, vi } from 'vitest'

import { today } from './date'

afterEach(() => {
  vi.useRealTimers()
})

// `toISOString()`은 UTC 날짜라 KST 오전 0~9시에는 어제가 나온다.
// 이 시각(KST 2026-09-24 00:30)에 UTC는 아직 09-23이다.
it('follows the local calendar day, not the UTC day', () => {
  vi.useFakeTimers()
  vi.setSystemTime(new Date('2026-09-23T15:30:00Z'))

  expect(today()).toBe(new Date().toLocaleDateString('sv-SE'))
})
