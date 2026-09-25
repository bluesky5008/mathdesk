import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type MouseEvent } from 'react'
import { Link, useSearchParams } from 'react-router'

import { AttendanceCell, AttendanceLockBanner } from '../components/AttendanceButtons'
import { PageHeader } from '../components/PageHeader'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Field } from '../components/ui/field'
import { Input } from '../components/ui/input'
import { KeyboardGrid } from '../components/ui/keyboard-grid'
import { Select } from '../components/ui/select'
import { Stat } from '../components/ui/stat'
import { today, weekOf } from '../lib/date'
import { Table, TableBody, TableCell, TableRow } from '../components/ui/table'
import {
  fetchClasses,
  fetchDaily,
  fetchDashboard,
  saveDailyRecords,
  setAttendanceConfirmed,
  type RecordPatch,
} from '../api'

function signed(value: number): string {
  return `${value >= 0 ? '+' : ''}${value}`
}

export function DashboardPage() {
  const queryClient = useQueryClient()
  const classes = useQuery({ queryKey: ['classes'], queryFn: () => fetchClasses() })
  // 반·날짜는 주소에 둔다. 항목 링크로 갔다가 뒤로 오면 보던 반·날짜가 그대로다
  const [params, setParams] = useSearchParams()
  const classId = Number(params.get('class')) || null
  const date = params.get('date') || today()
  const activeClassId = classId ?? classes.data?.[0]?.id ?? null
  const select = (key: 'class' | 'date', value: string) =>
    setParams(
      (current) => {
        const next = new URLSearchParams(current)
        next.set(key, value)
        return next
      },
      { replace: true },
    )

  const dashboard = useQuery({
    queryKey: ['dashboard', activeClassId, date],
    queryFn: () => fetchDashboard(activeClassId!, date),
    enabled: activeClassId !== null,
  })
  const daily = useQuery({
    queryKey: ['daily', activeClassId, date],
    queryFn: () => fetchDaily(activeClassId!, date),
    enabled: activeClassId !== null,
  })
  const session = daily.data?.session
  const locked = Boolean(session?.attendance_confirmed_at)
  const [nudge, setNudge] = useState(0)

  const [drafts, setDrafts] = useState<Record<number, RecordPatch>>({})

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['daily', activeClassId, date] })
    void queryClient.invalidateQueries({ queryKey: ['dashboard', activeClassId, date] })
  }
  const saveRecords = useMutation({
    mutationFn: () => saveDailyRecords(session!.id, Object.values(drafts)),
    onSuccess: () => {
      setDrafts({})
      invalidate()
    },
  })
  const confirmation = useMutation({
    mutationFn: (confirmed: boolean) => setAttendanceConfirmed(session!.id, confirmed),
    onSuccess: invalidate,
  })

  function patch(studentId: number, change: Omit<RecordPatch, 'student_id'>) {
    setDrafts((current) => ({
      ...current,
      [studentId]: { ...current[studentId], student_id: studentId, ...change },
    }))
  }

  const kpi = dashboard.data
  const dailyLink = (on: string) => `/daily?class=${activeClassId}&date=${on}`
  const [weekStart, weekEnd] = weekOf(date)
  const weekLink = `/stats?class=${activeClassId}&start=${weekStart}&end=${weekEnd}`
  // 출결 체크의 미저장 입력은 이동하면 사라진다
  const leave = (event: MouseEvent) => {
    if (Object.keys(drafts).length > 0 && !window.confirm('저장하지 않은 출결 입력이 있습니다. 이동할까요?')) {
      event.preventDefault()
    }
  }
  const textLink = 'text-brand hover:underline'

  return (
    <section>
      <PageHeader title="종합 대시보드">
        <Field label="반" htmlFor="dashboard-class">
          <Select
            id="dashboard-class"
            value={activeClassId ?? ''}
            onChange={(event) => select('class', event.target.value)}
          >
            {classes.data?.map((klass) => (
              <option key={klass.id} value={klass.id}>
                {klass.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="날짜" htmlFor="dashboard-date">
          <Input
            id="dashboard-date"
            type="date"
            className="w-40"
            value={date}
            onChange={(event) => select('date', event.target.value)}
          />
        </Field>
      </PageHeader>

      {kpi && (
        <div className="mb-5 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Stat
            title="총 재원생 & 반 현황"
            value={
              <Link to="/students" onClick={leave} className="hover:text-brand hover:underline">
                {`${kpi.campus.enrolled_students}명`}
              </Link>
            }
          >
            <Link to="/students/classes" onClick={leave} className={textLink}>
              {`활성 ${kpi.campus.active_classes}개 반`}
            </Link>
          </Stat>
          <Stat
            to={dailyLink(date)}
            onClick={leave}
            title="선택한 반 등원 현황"
            value={
              kpi.attendance ? `${kpi.attendance.attending} / ${kpi.attendance.enrolled}명` : '—'
            }
          >
            <span>출석 + 지각 + 조퇴 · 출결 체크에 따라 반영</span>
          </Stat>
          <Stat
            to={weekLink}
            onClick={leave}
            title="금주 과제 완수율"
            value={
              kpi.homework.completion_rate === null ? '—' : `${kpi.homework.completion_rate}%`
            }
          >
            {kpi.homework.delta_points !== null && (
              <span>{`전주 대비 ${signed(kpi.homework.delta_points)}%p`}</span>
            )}
            <span>{`미제출 ${kpi.homework.missing}건 · 재검사 대상 ${kpi.homework.recheck_targets}명`}</span>
          </Stat>
          <Stat
            to={weekLink}
            onClick={leave}
            title="주간테스트 종합 평균"
            value={kpi.test.average === null ? '—' : `${kpi.test.average}점`}
          >
            {kpi.test.average !== null && (
              <span>
                {`N=${kpi.test.count} · MAX ${kpi.test.max} (${kpi.test.max_count}명) · MIN ${kpi.test.min}`}
              </span>
            )}
          </Stat>
        </div>
      )}

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <Card>
          <CardHeader className="flex-row items-start justify-between gap-3">
            <div className="flex flex-col gap-1">
              <CardTitle>반별 출결 체크</CardTitle>
              <CardDescription className="break-keep">
                선택한 출결을 다시 누르면 해제됩니다. 마지막에 [출결 확정]을 눌러 주세요.
              </CardDescription>
            </div>
            <Link to={dailyLink(date)} onClick={leave} className={`shrink-0 text-sm ${textLink}`}>
              일일 입력에서 열기
            </Link>
          </CardHeader>
          <CardContent className="px-0 pt-4 pb-0">
            {session?.attendance_confirmed_at && (
              <div className="px-5">
                <AttendanceLockBanner
                  sessionDate={session.session_date}
                  confirmedAt={session.attendance_confirmed_at}
                  nudge={nudge}
                  unlocking={confirmation.isPending}
                  onUnlock={() => confirmation.mutate(false)}
                />
              </div>
            )}
            <KeyboardGrid>
              <Table>
                <TableBody>
                  {daily.data?.records.map((record) => {
                    const draft = drafts[record.student_id]
                    return (
                      <TableRow key={record.student_id}>
                        <TableCell className="w-28 font-medium whitespace-nowrap">
                          {record.name}
                        </TableCell>
                        <TableCell>
                          <AttendanceCell
                            name={record.name}
                            status={draft?.attendance_status ?? record.attendance_status}
                            reason={String(
                              draft?.attendance_reason ?? record.attendance_reason ?? '',
                            )}
                            locked={locked}
                            onLocked={() => setNudge((n) => n + 1)}
                            onStatusChange={(next) =>
                              patch(record.student_id, { attendance_status: next })
                            }
                            onReasonChange={(next) =>
                              patch(record.student_id, { attendance_reason: next })
                            }
                          />
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </KeyboardGrid>
            <div className="flex items-center gap-2 px-5 py-4">
              <Button
                type="button"
                onClick={() => saveRecords.mutate()}
                disabled={!session || locked}
              >
                저장
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => confirmation.mutate(!locked)}
                disabled={!session || confirmation.isPending}
              >
                {locked ? '확정 해제' : '출결 확정'}
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="self-start">
          <CardHeader>
            <CardTitle>지난 수업 진도 &amp; 과제</CardTitle>
          </CardHeader>
          <CardContent className="pt-4">
            {kpi?.last_session ? (
              <div className="flex flex-col gap-3">
                <Link
                  to={dailyLink(kpi.last_session.session_date)}
                  onClick={leave}
                  className={`text-xs ${textLink}`}
                >
                  {`${kpi.last_session.session_date} 수업 열기`}
                </Link>
                <ul className="flex flex-col gap-1.5 text-sm">
                  {kpi.last_session.progress.map((item) => (
                    <li key={item.period}>{`[${item.period}교시] ${item.content ?? ''}`}</li>
                  ))}
                </ul>
                <div className="border-t pt-3">
                  <h4 className="mb-1 text-xs font-medium text-muted-fg">과제</h4>
                  <p className="text-sm">{kpi.last_session.homework}</p>
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-fg">지난 수업 기록이 없습니다.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </section>
  )
}
