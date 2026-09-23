import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { AttendanceCell } from '../components/AttendanceButtons'
import { PageHeader } from '../components/PageHeader'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Field } from '../components/ui/field'
import { Input } from '../components/ui/input'
import { KeyboardGrid } from '../components/ui/keyboard-grid'
import { Select } from '../components/ui/select'
import { Stat } from '../components/ui/stat'
import { Table, TableBody, TableCell, TableRow } from '../components/ui/table'
import {
  fetchClasses,
  fetchDaily,
  fetchDashboard,
  saveDailyRecords,
  setAttendanceConfirmed,
  type RecordPatch,
} from '../api'

function today(): string {
  return new Date().toISOString().slice(0, 10)
}

function signed(value: number): string {
  return `${value >= 0 ? '+' : ''}${value}`
}

export function DashboardPage() {
  const queryClient = useQueryClient()
  const classes = useQuery({ queryKey: ['classes'], queryFn: fetchClasses })
  const [classId, setClassId] = useState<number | null>(null)
  const [date, setDate] = useState(today())
  const activeClassId = classId ?? classes.data?.[0]?.id ?? null

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

  return (
    <section>
      <PageHeader title="종합 대시보드">
        <Field label="반" htmlFor="dashboard-class">
          <Select
            id="dashboard-class"
            value={activeClassId ?? ''}
            onChange={(event) => setClassId(Number(event.target.value))}
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
            onChange={(event) => setDate(event.target.value)}
          />
        </Field>
      </PageHeader>

      {kpi && (
        <div className="mb-5 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Stat title="총 재원생 & 반 현황" value={`${kpi.campus.enrolled_students}명`}>
            <span>{`활성 ${kpi.campus.active_classes}개 반`}</span>
          </Stat>
          <Stat
            title="선택한 반 등원 현황"
            value={
              kpi.attendance ? `${kpi.attendance.attending} / ${kpi.attendance.enrolled}명` : '—'
            }
          >
            <span>출석 + 지각 + 조퇴 · 출결 체크에 따라 반영</span>
          </Stat>
          <Stat
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
          <CardHeader>
            <CardTitle>반별 출결 체크</CardTitle>
            <CardDescription>
              선택한 출결을 다시 누르면 해제됩니다. 마지막에 확인을 눌러 출결을 확정해 주세요.
            </CardDescription>
          </CardHeader>
          <CardContent className="px-0 pt-4 pb-0">
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
                            disabled={locked}
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
                disabled={!session}
              >
                {locked ? '편집' : '확인'}
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
                <p className="text-xs text-muted-fg">{kpi.last_session.session_date}</p>
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
