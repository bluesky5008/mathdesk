import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'

import { ATTENDANCE } from '../components/AttendanceButtons'
import { Card, CardContent } from '../components/ui/card'
import { Field } from '../components/ui/field'
import { WEEKDAYS, weekdayOf } from '../components/ui/month-calendar'
import { Select } from '../components/ui/select'
import { Stat } from '../components/ui/stat'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from '../components/ui/table'
import { TONE } from '../components/ui/toggle'
import { fetchDaily, fetchDailyHistory, type DailyHistoryRow } from '../api'
import { EmptyRosterNotice, useDailySelection } from './DailyLayout'

const ATTENDING = ['present', 'late', 'early_leave']
const RECHECK_RESULT = { pass: '합격', fail: '불합격' } as const

function shortDate(date: string): string {
  return `${date.slice(5).replace('-', '/')}(${WEEKDAYS[weekdayOf(date)]})`
}

function AttendanceBadge({ row }: { row: DailyHistoryRow }) {
  const entry = ATTENDANCE.find(([status]) => status === row.attendance_status)
  if (!entry) return <span className="text-muted-fg">미확인</span>
  const [, label, tone] = entry
  return (
    <span className="flex items-center gap-2">
      <span className={`inline-flex h-7 items-center rounded-md px-2 text-xs font-medium ${TONE[tone]}`}>
        {label}
      </span>
      {row.attendance_reason && <span className="text-xs text-muted-fg">{row.attendance_reason}</span>}
    </span>
  )
}

function RecheckCell({ row }: { row: DailyHistoryRow }) {
  const { recheck } = row
  if (!recheck.target || !recheck.prev_grade || !recheck.prev_date) return <>—</>
  return (
    <span className="flex items-center gap-2 whitespace-nowrap">
      <span className="text-xs text-muted-fg">
        직전 {recheck.prev_grade} · {recheck.prev_date.slice(5).replace('-', '/')}
      </span>
      {recheck.result ? (
        <span className="font-medium">{RECHECK_RESULT[recheck.result as keyof typeof RECHECK_RESULT]}</span>
      ) : (
        <span className="text-xs text-muted-fg">미입력</span>
      )}
    </span>
  )
}

/** [학생별 정보] 탭 — 한 학생의 날짜별 기록을 읽기 전용으로 보인다(FR-45). 고치려면 날짜 링크로 [반별 정보]에 간다. */
export function StudentDailyPage() {
  const { classId, date, studentId, select } = useDailySelection()
  const daily = useQuery({
    queryKey: ['daily', classId, date],
    queryFn: () => fetchDaily(classId!, date),
    enabled: classId !== null,
  })
  const roster = daily.data?.records ?? []
  const activeStudentId = studentId ?? roster[0]?.student_id ?? null
  const history = useQuery({
    queryKey: ['daily-history', classId, activeStudentId, date],
    queryFn: () => fetchDailyHistory(classId!, activeStudentId!, date),
    enabled: classId !== null && activeStudentId !== null,
  })
  const rows = history.data?.rows ?? []
  const attending = rows.filter((row) => ATTENDING.includes(row.attendance_status)).length
  const scores = rows.map((row) => row.test_score_num).filter((score) => score != null).map(Number)
  const average = scores.length ? Math.round((scores.reduce((sum, s) => sum + s, 0) / scores.length) * 10) / 10 : null

  return (
    <>
      <div className="mb-5 flex flex-wrap items-end gap-3">
        <Field label="학생" htmlFor="daily-student">
          <Select
            id="daily-student"
            value={activeStudentId ?? ''}
            onChange={(event) => select({ studentId: Number(event.target.value) })}
          >
            {roster.map((record) => (
              <option key={record.student_id} value={record.student_id}>
                {record.name}
              </option>
            ))}
          </Select>
        </Field>
      </div>

      {daily.data && roster.length === 0 ? (
        <Card>
          <EmptyRosterNotice />
        </Card>
      ) : (
        <>
          <div className="mb-5 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Stat title="출석" value={`${attending} / ${rows.length}회`} />
            <Stat title="테스트 평균" value={average === null ? '—' : `${average}점 (${scores.length}회)`} />
          </div>
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHead>
                  <TableRow>
                    <TableHeaderCell className="w-28">날짜</TableHeaderCell>
                    <TableHeaderCell>출결</TableHeaderCell>
                    <TableHeaderCell>이전 과제 재검사</TableHeaderCell>
                    <TableHeaderCell className="w-24">과제피드백</TableHeaderCell>
                    <TableHeaderCell>테스트</TableHeaderCell>
                    <TableHeaderCell>코멘트</TableHeaderCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {rows.map((row) => (
                    <TableRow key={row.date}>
                      <TableCell className="whitespace-nowrap">
                        <Link
                          to={`/daily?class=${classId}&date=${row.date}`}
                          className="font-medium text-brand underline-offset-2 hover:underline"
                        >
                          {shortDate(row.date)}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <AttendanceBadge row={row} />
                      </TableCell>
                      <TableCell>
                        <RecheckCell row={row} />
                      </TableCell>
                      <TableCell className="tabular-nums">{row.homework_grade}</TableCell>
                      <TableCell className="whitespace-nowrap">
                        {row.test_name && <div className="text-xs text-muted-fg">{row.test_name}</div>}
                        <span className="tabular-nums">
                          {row.test_score_num == null
                            ? '—'
                            : `${Number(row.test_score_num)} / ${row.class_average ?? '—'}`}
                        </span>
                      </TableCell>
                      <TableCell className="min-w-64 text-sm">{row.comment}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              {history.isSuccess && rows.length === 0 && (
                <p className="px-5 py-6 text-sm text-muted-fg">선택한 날짜까지 기록이 있는 수업이 없습니다.</p>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </>
  )
}
