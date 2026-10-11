import { useQueries, useQuery } from '@tanstack/react-query'

import {
  cancelEnrollment,
  endEnrollment,
  fetchClasses,
  fetchEnrollments,
  type Enrollment,
  type Klass,
} from '../api'
import { dayBefore, today } from './date'

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
  if (!classes?.length) return '미배정'
  return classes.map((klass) => (klass.is_active ? klass.name : `${klass.name} (비활성)`)).join(', ')
}

/** 해제 전 확인 문구. 반 명단과 학생 목록이 같은 문구를 쓴다. */
export function releaseNotice(studentName: string, className: string): string {
  return (
    `${studentName} 학생을 ${className}에서 해제합니다. 오늘 수업부터 명단에서 빠집니다.\n` +
    '오늘 이미 입력한 출결·과제는 일일 입력 화면에 보이지 않게 됩니다(기록은 남습니다).'
  )
}

/**
 * 해제는 "오늘 수업부터 이 반이 아님"이라 어제까지로 기간을 끊는다(TASK-77).
 * 오늘 이후 시작하는 배정은 끊을 기간이 없어 지운다.
 */
export async function releaseFromToday(classId: number, row: Enrollment): Promise<void> {
  const on = today()
  if (row.start_date >= on) await cancelEnrollment(classId, row.id)
  else await endEnrollment(classId, row.id, dayBefore(on))
}
