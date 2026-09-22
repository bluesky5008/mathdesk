export const ATTENDANCE = [
  ['present', '출석'],
  ['late', '지각'],
  ['absent', '결석'],
  ['early_leave', '조퇴'],
] as const

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
    <>
      {ATTENDANCE.map(([status, label]) => {
        const pressed = value === status
        return (
          <button
            key={status}
            type="button"
            aria-pressed={pressed}
            disabled={disabled}
            onClick={() => onChange(pressed ? 'unchecked' : status)}
          >
            {label}
          </button>
        )
      })}
    </>
  )
}
