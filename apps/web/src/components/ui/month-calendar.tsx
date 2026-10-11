import { useEffect, useRef, useState } from 'react'

import { isoDate, today } from '../../lib/date'
import { cn } from '../../lib/utils'
import { Button } from './button'

// 반 시간표(`class_schedule.weekday`)와 같은 번호다: 0=월 … 6=일
export const WEEKDAYS = ['월', '화', '수', '목', '금', '토', '일']

/** `YYYY-MM-DD`의 요일 번호(0=월). `Date.getDay()`는 0=일이라 돌려 맞춘다. */
export function weekdayOf(date: string): number {
  return (new Date(`${date}T00:00:00`).getDay() + 6) % 7
}

function shiftMonth(month: string, by: number): string {
  const [year, monthNumber] = month.split('-').map(Number)
  return isoDate(new Date(year, monthNumber - 1 + by, 1)).slice(0, 7)
}

type Marks = {
  /** 굵게 표시할 날(수업일) */
  emphasized: (date: string) => boolean
  /** 아래에 점을 찍을 날(기록 있음) */
  dotted: (date: string) => boolean
}

/**
 * 월 달력. 브라우저 기본 날짜 입력은 특정 날짜를 굵게 표시할 수 없어 직접 그린다(DCR-020, DES-24).
 * 어느 날을 굵게 하고 점을 찍을지는 호출하는 쪽이 정한다.
 */
export function MonthCalendar({
  month,
  selected,
  onSelect,
  onMonthChange,
  emphasized,
  dotted,
}: Marks & {
  month: string
  selected: string | null
  onSelect: (date: string) => void
  onMonthChange: (month: string) => void
}) {
  const [year, monthNumber] = month.split('-').map(Number)
  const leading = weekdayOf(`${month}-01`)
  const count = new Date(year, monthNumber, 0).getDate()
  const cells: (string | null)[] = [
    ...Array<null>(leading).fill(null),
    ...Array.from({ length: count }, (_, index) => isoDate(new Date(year, monthNumber - 1, index + 1))),
  ]
  while (cells.length % 7) cells.push(null)
  const weeks = Array.from({ length: cells.length / 7 }, (_, index) => cells.slice(index * 7, index * 7 + 7))
  const todayIso = today()

  return (
    <div className="w-72 text-sm">
      <div className="mb-2 flex items-center justify-between">
        <Button type="button" variant="ghost" size="sm" aria-label="이전 달" onClick={() => onMonthChange(shiftMonth(month, -1))}>
          ‹
        </Button>
        <strong>
          {year}년 {monthNumber}월
        </strong>
        <div className="flex items-center gap-1">
          <Button type="button" variant="ghost" size="sm" onClick={() => onSelect(todayIso)}>
            오늘
          </Button>
          <Button type="button" variant="ghost" size="sm" aria-label="다음 달" onClick={() => onMonthChange(shiftMonth(month, 1))}>
            ›
          </Button>
        </div>
      </div>
      <table role="grid" className="w-full table-fixed border-collapse text-center">
        <thead>
          <tr>
            {WEEKDAYS.map((label) => (
              <th key={label} className="py-1 text-xs font-medium text-muted-fg">
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {weeks.map((week, row) => (
            <tr key={row}>
              {week.map((date, column) => (
                <td key={column} className="p-0.5">
                  {date && (
                    <button
                      type="button"
                      aria-label={[
                        `${monthNumber}월 ${Number(date.slice(8))}일`,
                        emphasized(date) && '수업일',
                        dotted(date) && '기록 있음',
                      ]
                        .filter(Boolean)
                        .join(' ')}
                      aria-pressed={date === selected}
                      onClick={() => onSelect(date)}
                      className={cn(
                        'relative h-9 w-full rounded-md tabular-nums outline-none transition-colors',
                        'hover:bg-accent focus-visible:outline-2 focus-visible:outline-ring',
                        emphasized(date) ? 'font-bold' : 'text-muted-fg',
                        date === todayIso && 'ring-1 ring-brand ring-inset',
                        date === selected && 'bg-brand text-brand-fg hover:bg-brand',
                      )}
                    >
                      {Number(date.slice(8))}
                      {dotted(date) && (
                        <span
                          aria-hidden
                          className="absolute bottom-1 left-1/2 h-1 w-1 -translate-x-1/2 rounded-full bg-current"
                        />
                      )}
                    </button>
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/** 날짜를 보이는 버튼. 누르면 아래에 월 달력이 열리고, 고르면 닫힌다. 바깥 클릭·Esc로도 닫힌다. */
export function DatePickerButton({
  id,
  value,
  onChange,
  onMonthChange,
  emphasized,
  dotted,
  className,
}: Marks & {
  id: string
  value: string
  onChange: (date: string) => void
  /** 달력에 보이는 달이 바뀔 때(열릴 때 포함). 그 달의 표시 데이터를 준비하라는 신호다 */
  onMonthChange: (month: string) => void
  className?: string
}) {
  const [open, setOpen] = useState(false)
  const [month, setMonth] = useState(value.slice(0, 7))
  const container = useRef<HTMLDivElement>(null)

  function moveTo(next: string) {
    setMonth(next)
    onMonthChange(next)
  }

  useEffect(() => {
    if (!open) return
    const onPointerDown = (event: MouseEvent) => {
      if (!container.current?.contains(event.target as Node)) setOpen(false)
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  return (
    <div ref={container} className={cn('relative', className)}>
      <Button
        id={id}
        type="button"
        variant="outline"
        aria-haspopup="dialog"
        aria-expanded={open}
        className="w-40 justify-between font-normal tabular-nums"
        onClick={() => {
          if (open) return setOpen(false)
          moveTo(value.slice(0, 7))
          setOpen(true)
        }}
      >
        {value}
        <span aria-hidden className="text-muted-fg">
          ▾
        </span>
      </Button>
      {open && (
        <div
          role="dialog"
          aria-label="날짜 선택"
          className="absolute top-full left-0 z-20 mt-1 rounded-md border bg-surface p-3 shadow-lg sm:left-auto sm:right-0"
        >
          <MonthCalendar
            month={month}
            selected={value}
            onSelect={(date) => {
              setOpen(false)
              onChange(date)
            }}
            onMonthChange={moveTo}
            emphasized={emphasized}
            dotted={dotted}
          />
        </div>
      )}
    </div>
  )
}
