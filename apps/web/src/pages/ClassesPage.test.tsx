import { describe, expect, it } from 'vitest'

import { describeSchedules } from './ClassesPage'

describe('describeSchedules', () => {
  it('formats weekday and time range', () => {
    expect(
      describeSchedules([{ weekday: 4, start_time: '18:00:00', end_time: '22:00:00' }]),
    ).toBe('금 18:00~22:00')
  })

  it('joins multiple schedules', () => {
    expect(
      describeSchedules([
        { weekday: 1, start_time: '18:00:00', end_time: '22:00:00' },
        { weekday: 5, start_time: '10:00:00', end_time: '13:00:00' },
      ]),
    ).toBe('화 18:00~22:00, 토 10:00~13:00')
  })
})
