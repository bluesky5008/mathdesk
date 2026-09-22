import { Input } from './ui/input'
import { Toggle, type Tone } from './ui/toggle'

const ATTENDANCE = [
  ['present', '출석', 'success'],
  ['late', '지각', 'warning'],
  ['absent', '결석', 'danger'],
  ['early_leave', '조퇴', 'neutral'],
] as const satisfies readonly (readonly [string, string, Tone])[]

export function AttendanceButtons({
  value,
  disabled,
  onChange,
}: {
  value: string
  disabled?: boolean
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
            disabled={disabled}
            onClick={() => onChange(pressed ? 'unchecked' : status)}
          >
            {label}
          </Toggle>
        )
      })}
    </div>
  )
}

/** 출결 버튼과 사유 입력은 항상 한 칸에 함께 놓인다. */
export function AttendanceCell({
  name,
  status,
  reason,
  disabled,
  onStatusChange,
  onReasonChange,
}: {
  name: string
  status: string
  reason: string
  disabled?: boolean
  onStatusChange: (next: string) => void
  onReasonChange: (next: string) => void
}) {
  return (
    <div className="flex items-center gap-2">
      <AttendanceButtons value={status} disabled={disabled} onChange={onStatusChange} />
      <Input
        aria-label={`${name} 사유`}
        value={reason}
        disabled={disabled}
        placeholder="사유"
        className="h-7 w-28 text-xs"
        onChange={(event) => onReasonChange(event.target.value)}
      />
    </div>
  )
}
