import { useQueries, useQuery } from '@tanstack/react-query'

import { fetchClasses, fetchEnrollments, type Klass } from '../api'
import { today } from './date'

/**
 * 오늘 기준 학생별 배정 반(비활성 반 포함). 반마다 오늘 명단을 한 번씩 불러 합친다.
 * 볼 수 있는 반의 범위는 서버의 반 목록 스코프를 그대로 따른다.
 */
export function useCurrentClasses(): Map<number, Klass[]> {
  const on = today()
  const classes = useQuery({ queryKey: ['classes', true], queryFn: () => fetchClasses(true) })
  const rosters = useQueries({
    queries: (classes.data ?? []).map((klass) => ({
      queryKey: ['enrollments', klass.id, on],
      queryFn: () => fetchEnrollments(klass.id, on),
    })),
  })

  const byStudent = new Map<number, Klass[]>()
  rosters.forEach((roster, index) => {
    const klass = classes.data![index]
    for (const row of roster.data ?? []) {
      byStudent.set(row.student_id, [...(byStudent.get(row.student_id) ?? []), klass])
    }
  })
  return byStudent
}

export function describeClasses(classes: Klass[] | undefined): string {
  if (!classes?.length) return '—'
  return classes.map((klass) => (klass.is_active ? klass.name : `${klass.name} (비활성)`)).join(', ')
}
