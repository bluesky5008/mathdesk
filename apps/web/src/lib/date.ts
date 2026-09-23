/**
 * 오늘 날짜를 로컬 달력 기준 `YYYY-MM-DD`로 준다.
 * `toISOString()`은 UTC라 KST 오전 0~9시에 하루 이른 날짜를 준다.
 */
export function today(): string {
  const now = new Date()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  return `${now.getFullYear()}-${month}-${String(now.getDate()).padStart(2, '0')}`
}
