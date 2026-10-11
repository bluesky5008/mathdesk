import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'

import { DatePickerButton, MonthCalendar } from './month-calendar'

// DCR-020 / AC-46: 수업일은 굵게, 기록이 있는 날은 점. 2026-09-14은 월요일, 09-19은 토요일
const isMonday = (date: string) => new Date(`${date}T00:00:00`).getDay() === 1
const recorded = new Set(['2026-09-19'])

function renderCalendar(onSelect = vi.fn(), onMonthChange = vi.fn()) {
  render(
    <MonthCalendar
      month="2026-09"
      selected="2026-09-18"
      onSelect={onSelect}
      onMonthChange={onMonthChange}
      emphasized={(date) => isMonday(date) || recorded.has(date)}
      dotted={(date) => recorded.has(date)}
    />,
  )
  return { onSelect, onMonthChange }
}

it('starts the week on Monday and lays September 2026 out from Tuesday', () => {
  renderCalendar()

  expect(screen.getAllByRole('columnheader').map((cell) => cell.textContent)).toEqual([
    '월', '화', '수', '목', '금', '토', '일',
  ])
  const firstRow = screen.getAllByRole('row')[1]
  expect(firstRow.textContent).toBe('123456')
})

it('emphasizes lesson days and dots recorded days', () => {
  renderCalendar()

  expect(screen.getByRole('button', { name: '9월 14일 수업일' })).toHaveClass('font-bold')
  expect(screen.getByRole('button', { name: '9월 19일 수업일 기록 있음' })).toHaveClass('font-bold')
  expect(screen.getByRole('button', { name: '9월 15일' })).not.toHaveClass('font-bold')
  expect(screen.getByRole('button', { name: '9월 18일' })).toHaveAttribute('aria-pressed', 'true')
})

it('reports the picked day and month moves', async () => {
  const { onSelect, onMonthChange } = renderCalendar()

  await userEvent.click(screen.getByRole('button', { name: '9월 21일 수업일' }))
  expect(onSelect).toHaveBeenCalledWith('2026-09-21')

  await userEvent.click(screen.getByRole('button', { name: '다음 달' }))
  expect(onMonthChange).toHaveBeenCalledWith('2026-10')
  await userEvent.click(screen.getByRole('button', { name: '이전 달' }))
  expect(onMonthChange).toHaveBeenCalledWith('2026-08')
})

it('opens the calendar from the date button and closes after a pick', async () => {
  const onChange = vi.fn()
  const onMonthChange = vi.fn()
  render(
    <DatePickerButton
      id="date"
      value="2026-09-18"
      onChange={onChange}
      onMonthChange={onMonthChange}
      emphasized={() => false}
      dotted={() => false}
    />,
  )
  expect(screen.getByRole('button', { name: '2026-09-18' })).toBeInTheDocument()
  expect(screen.queryByRole('grid')).not.toBeInTheDocument()

  await userEvent.click(screen.getByRole('button', { name: '2026-09-18' }))
  expect(screen.getByRole('grid')).toBeInTheDocument()
  expect(onMonthChange).toHaveBeenCalledWith('2026-09')

  await userEvent.click(screen.getByRole('button', { name: '9월 21일' }))
  expect(onChange).toHaveBeenCalledWith('2026-09-21')
  expect(screen.queryByRole('grid')).not.toBeInTheDocument()
})
