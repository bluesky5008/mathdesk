/** 날짜를 로컬 달력 기준 `YYYY-MM-DD`로 준다. `toISOString()`은 UTC라 KST 오전 0~9시에 하루 이른 날짜를 준다. */
function isoDate(day: Date): string {
  const month = String(day.getMonth() + 1).padStart(2, '0')
  return `${day.getFullYear()}-${month}-${String(day.getDate()).padStart(2, '0')}`
}

/** 오늘 날짜(로컬 달력 기준 `YYYY-MM-DD`). */
export function today(): string {
  return isoDate(new Date())
}

/** `YYYY-MM-DD`의 전날. */
export function dayBefore(date: string): string {
  const day = new Date(`${date}T00:00:00`)
  day.setDate(day.getDate() - 1)
  return isoDate(day)
}
