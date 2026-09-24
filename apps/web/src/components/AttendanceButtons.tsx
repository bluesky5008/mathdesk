import { useEffect, useState, type ReactNode } from 'react'

import { Button } from './ui/button'
import { Input } from './ui/input'
import { Toggle, type Tone } from './ui/toggle'

// 잠긴 칸은 disabled 대신 aria-disabled로 둔다. disabled는 클릭 이벤트가 없어 왜 안 눌리는지 알려 줄 수 없다
const LOCKED = 'cursor-not-allowed opacity-50'

const ATTENDANCE = [
  ['present', '출석', 'success'],
  ['late', '지각', 'warning'],
  ['absent', '결석', 'danger'],
  ['early_leave', '조퇴', 'neutral'],
] as const satisfies readonly (readonly [string, string, Tone])[]

export function AttendanceButtons({
  value,
  locked,
  onLocked,
  onChange,
}: {
  value: string
  locked?: boolean
  onLocked: () => void
  onChange: (next: string) => void
}) {
  return (
    <div className="flex gap-1">
      {ATTENDANCE.map(([status, label, tone]) => {
        const pressed = value === status
        return (
          <Toggle
            key={status}
            pressed={pressed}
            tone={tone}
            aria-disabled={locked || undefined}
            className={locked ? LOCKED : undefined}
            onClick={() => (locked ? onLocked() : onChange(pressed ? 'unchecked' : status))}
          >
            {label}
          </Toggle>
        )
      })}
    </div>
  )
}

/** 출결 버튼과 사유 입력은 항상 한 칸에 함께 놓인다. 잠긴 칸을 누르면 칸 옆에 이유를 보이고 onLocked를 부른다. */
export function AttendanceCell({
  name,
  status,
  reason,
  locked,
  onLocked,
  onStatusChange,
  onReasonChange,
}: {
  name: string
  status: string
  reason: string
  locked?: boolean
  onLocked: () => void
  onStatusChange: (next: string) => void
  onReasonChange: (next: string) => void
}) {
  const [tried, setTried] = useState(false)
  useEffect(() => {
    if (!locked) setTried(false)
  }, [locked])
  const nudge = () => {
    setTried(true)
    onLocked()
  }

  return (
    <div className="flex items-center gap-2">
      <AttendanceButtons value={status} locked={locked} onLocked={nudge} onChange={onStatusChange} />
      <Input
        aria-label={`${name} 사유`}
        value={reason}
        readOnly={locked}
        aria-disabled={locked || undefined}
        placeholder="사유"
        className={locked ? `h-7 w-28 text-xs ${LOCKED}` : 'h-7 w-28 text-xs'}
        onClick={locked ? nudge : undefined}
        onChange={(event) => onReasonChange(event.target.value)}
      />
      {tried && (
        <span className="text-xs whitespace-nowrap text-muted-fg">확정됨 · [확정 해제] 후 수정</span>
      )}
    </div>
  )
}

/** "M/D"와 "M/D HH:MM"(로컬 시각). */
function shortDate(isoDate: string): string {
  const [, month, day] = isoDate.split('-')
  return `${Number(month)}/${Number(day)}`
}
function shortDateTime(iso: string): string {
  const at = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${at.getMonth() + 1}/${at.getDate()} ${pad(at.getHours())}:${pad(at.getMinutes())}`
}

/**
 * 출결 확정(FR-09) 잠금을 표 바로 위에 알린다. 잠긴 칸을 누를 때마다 nudge를 올리면 잠깐 깜빡인다.
 * 확정한 사람 이름은 보이지 않는다(사용자 결정 2026-09-25).
 */
export function AttendanceLockBanner({
  sessionDate,
  confirmedAt,
  nudge,
  unlocking,
  onUnlock,
  children,
}: {
  sessionDate: string
  confirmedAt: string
  nudge: number
  unlocking: boolean
  onUnlock: () => void
  children?: ReactNode
}) {
  const [flash, setFlash] = useState(false)
  useEffect(() => {
    if (nudge === 0) return
    setFlash(true)
    const timer = setTimeout(() => setFlash(false), 1200)
    return () => clearTimeout(timer)
  }, [nudge])

  return (
    <div
      className={[
        'mb-3 flex flex-wrap items-center gap-3 rounded-md border border-warning bg-warning/15 px-4 py-2.5 text-sm',
        flash ? 'animate-pulse ring-2 ring-warning' : '',
      ].join(' ')}
    >
      <p>
        {`🔒 ${shortDate(sessionDate)} 출결이 확정되어 잠겨 있습니다(${shortDateTime(confirmedAt)} 확정).`}
        {children && <> {children}</>}
      </p>
      <Button type="button" variant="outline" size="sm" disabled={unlocking} onClick={onUnlock}>
        확정 해제
      </Button>
    </div>
  )
}
