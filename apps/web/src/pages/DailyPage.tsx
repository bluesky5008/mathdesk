import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import { AttendanceCell, AttendanceLockBanner } from '../components/AttendanceButtons'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Field } from '../components/ui/field'
import { Input } from '../components/ui/input'
import { KeyboardGrid } from '../components/ui/keyboard-grid'
import { Stat } from '../components/ui/stat'
import { Textarea } from '../components/ui/textarea'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from '../components/ui/table'
import { Toggle } from '../components/ui/toggle'
import {
  fetchDaily,
  saveDailyNotes,
  saveDailyRecords,
  saveRecheck,
  setAttendanceConfirmed,
  type DailyRecord,
  type NotesPatch,
  type RecordPatch,
} from '../api'
import { EmptyRosterNotice, useDailySelection } from './DailyLayout'

const GRADES = ['A+', 'A', 'B', 'C', 'D', 'F']
const PERIODS = [1, 2, 3, 4]
const NOTE_FIELDS = [
  ['homework', '오늘의 과제'],
  ['video_url', '수업 영상 링크'],
  // 강사 첨언은 문자에 반 공통 코멘트로 나간다(DCR-017)
  ['teacher_note', '선생님 코멘트 (문자 공통)'],
] as const
const EMPTY_NOTES: NotesPatch = {}

function describeRecheck(record: DailyRecord): string {
  if (!record.recheck.prev_grade || !record.recheck.prev_date) {
    return '재검사 대상 아님'
  }
  return `직전 ${record.recheck.prev_grade} · ${record.recheck.prev_date.slice(5).replace('-', '/')}`
}

/** [반별 정보] 탭 — 반·날짜 선택은 DailyLayout의 머리말이 소유한다(FR-45) */
export function DailyPage() {
  const queryClient = useQueryClient()
  const { classId: activeClassId, date, guard } = useDailySelection()

  const daily = useQuery({
    queryKey: ['daily', activeClassId, date],
    queryFn: () => fetchDaily(activeClassId!, date),
    enabled: activeClassId !== null,
  })
  const session = daily.data?.session

  // 표 편집과 메모 편집은 서로 다른 저장 단위다. 한쪽 저장이 다른 쪽 미저장 입력을 지우면 안 된다.
  const [drafts, setDrafts] = useState<Record<number, RecordPatch>>({})
  const [notes, setNotes] = useState<NotesPatch>(EMPTY_NOTES)

  useEffect(() => {
    setDrafts({})
    setNotes(EMPTY_NOTES)
  }, [activeClassId, date])

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['daily-calendar', activeClassId] })
    return queryClient.invalidateQueries({ queryKey: ['daily', activeClassId, date] })
  }

  const saveRecords = useMutation({
    mutationFn: () => saveDailyRecords(session!.id, Object.values(drafts)),
    onSuccess: () => {
      setDrafts({})
      void invalidate()
    },
  })
  const saveNotes = useMutation({
    mutationFn: () => saveDailyNotes(session!.id, notes),
    onSuccess: () => {
      setNotes(EMPTY_NOTES)
      void invalidate()
    },
  })
  const recheck = useMutation({
    mutationFn: (input: { studentId: number; result: string | null }) =>
      saveRecheck(session!.id, input.studentId, input.result),
    onSuccess: () => void invalidate(),
  })
  const confirmation = useMutation({
    mutationFn: (confirmed: boolean) => setAttendanceConfirmed(session!.id, confirmed),
    onSuccess: () => void invalidate(),
  })

  const dirty = Object.keys(drafts).length > 0 || Object.keys(notes).length > 0

  // 반·날짜·탭을 바꾸기 전에 머리말이 묻는다(FR-14 상세)
  useEffect(() => {
    guard.current = () => !dirty || window.confirm('저장하지 않은 입력이 있습니다. 이동할까요?')
    return () => {
      guard.current = null
    }
  }, [dirty, guard])

  function patch(studentId: number, change: Omit<RecordPatch, 'student_id'>) {
    setDrafts((current) => ({
      ...current,
      [studentId]: { ...current[studentId], student_id: studentId, ...change },
    }))
  }

  function valueOf<K extends keyof RecordPatch>(record: DailyRecord, field: K) {
    const draft = drafts[record.student_id]
    return draft && field in draft ? draft[field] : (record[field as keyof DailyRecord] as never)
  }

  const locked = Boolean(session?.attendance_confirmed_at)
  const [nudge, setNudge] = useState(0)

  return (
    <>

      {daily.data && (
        <div className="mb-5 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Stat
            title="등원 현황"
            value={`${daily.data.summary.attending} / ${daily.data.summary.enrolled}명`}
          />
          <Stat title="당일 테스트 평균" value={daily.data.summary.test_average ?? '—'} />
        </div>
      )}

      {session?.attendance_confirmed_at && (
        <AttendanceLockBanner
          sessionDate={session.session_date}
          confirmedAt={session.attendance_confirmed_at}
          nudge={nudge}
          unlocking={confirmation.isPending}
          onUnlock={() => confirmation.mutate(false)}
        >
          과제·테스트·코멘트는 그대로 입력할 수 있습니다.
        </AttendanceLockBanner>
      )}

      <Card className="mb-5">
        <CardContent className="p-0">
          <KeyboardGrid>
            <Table>
              <TableHead>
                <TableRow>
                  <TableHeaderCell className="w-28">학생</TableHeaderCell>
                  <TableHeaderCell>{locked ? '출결 상태 🔒' : '출결 상태'}</TableHeaderCell>
                  <TableHeaderCell>이전 과제 재검사</TableHeaderCell>
                  <TableHeaderCell>과제피드백</TableHeaderCell>
                  <TableHeaderCell className="w-24">테스트</TableHeaderCell>
                  <TableHeaderCell>코멘트</TableHeaderCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {daily.data?.records.map((record) => (
                  <TableRow key={record.student_id}>
                    <TableCell className="font-medium whitespace-nowrap">{record.name}</TableCell>
                    <TableCell>
                      <AttendanceCell
                        name={record.name}
                        status={String(valueOf(record, 'attendance_status'))}
                        reason={String(valueOf(record, 'attendance_reason') ?? '')}
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
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <span className="text-xs whitespace-nowrap text-muted-fg">
                          {describeRecheck(record)}
                        </span>
                        {record.recheck.target &&
                          (
                            [
                              ['pass', '합격', 'success'],
                              ['fail', '불합격', 'danger'],
                            ] as const
                          ).map(([value, label, tone]) => (
                            <Toggle
                              key={value}
                              pressed={record.recheck.result === value}
                              tone={tone}
                              onClick={() =>
                                recheck.mutate({
                                  studentId: record.student_id,
                                  result: record.recheck.result === value ? null : value,
                                })
                              }
                            >
                              {label}
                            </Toggle>
                          ))}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        {GRADES.map((grade) => (
                          <Toggle
                            key={grade}
                            pressed={valueOf(record, 'homework_grade') === grade}
                            className="w-9 tabular-nums"
                            onClick={() =>
                              patch(record.student_id, {
                                homework_grade:
                                  valueOf(record, 'homework_grade') === grade ? null : grade,
                              })
                            }
                          >
                            {grade}
                          </Toggle>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Input
                        aria-label={`${record.name} 점수`}
                        inputMode="numeric"
                        className="h-7 w-20 text-right tabular-nums"
                        value={String(valueOf(record, 'test_score_num') ?? '')}
                        onChange={(event) =>
                          patch(record.student_id, {
                            test_score_num:
                              event.target.value === '' ? null : Number(event.target.value),
                          })
                        }
                      />
                    </TableCell>
                    {/* 학생별 코멘트는 그 학생 문자의 개별 구획 끝에 붙는다(FR-44) */}
                    <TableCell>
                      <Input
                        aria-label={`${record.name} 코멘트`}
                        maxLength={500}
                        className="h-7 min-w-64"
                        value={String(valueOf(record, 'comment') ?? '')}
                        onChange={(event) => patch(record.student_id, { comment: event.target.value })}
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </KeyboardGrid>
          {daily.data?.records.length === 0 && <EmptyRosterNotice />}
        </CardContent>
      </Card>

      <div className="mb-5 flex items-center gap-2">
        <Button type="button" onClick={() => saveRecords.mutate()} disabled={!session}>
          표 저장
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={() => confirmation.mutate(!locked)}
          disabled={!session || confirmation.isPending}
        >
          {locked ? '확정 해제' : '출결 확정'}
        </Button>
        <span className="text-xs text-muted-fg">
          위아래 방향키와 Enter로 같은 열의 다음 학생으로 이동합니다.
        </span>
        {saveRecords.isError && (
          <p role="alert" className="text-sm text-danger">
            {saveRecords.error.message}
          </p>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>오늘 진도</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {PERIODS.map((period) => (
            <Field key={period} label={`${period}교시`} htmlFor={`period-${period}`}>
              <Textarea
                id={`period-${period}`}
                rows={2}
               
                value={
                  notes.progress?.find((item) => item.period === period)?.content ??
                  session?.progress.find((item) => item.period === period)?.content ??
                  ''
                }
                onChange={(event) =>
                  setNotes((current) => {
                    const base =
                      current.progress ??
                      PERIODS.map((value) => ({
                        period: value,
                        content:
                          session?.progress.find((item) => item.period === value)?.content ?? null,
                      }))
                    return {
                      ...current,
                      progress: base.map((item) =>
                        item.period === period ? { ...item, content: event.target.value } : item,
                      ),
                    }
                  })
                }
              />
            </Field>
          ))}
          {/* 테스트명은 반 공통 값이라 표가 아니라 이 카드에서 저장한다(DCR-019). 만점 칸은 두지 않는다 */}
          <Field label="테스트명" htmlFor="notes-test_name">
            <Input
              id="notes-test_name"
              maxLength={100}
              value={String(notes.test_name ?? session?.test_name ?? '')}
              onChange={(event) => setNotes({ ...notes, test_name: event.target.value })}
            />
          </Field>
          {NOTE_FIELDS.map(([field, label]) => (
            <Field key={field} label={label} htmlFor={`notes-${field}`}>
              <Textarea
                id={`notes-${field}`}
                rows={2}
               
                value={String(notes[field] ?? session?.[field] ?? '')}
                onChange={(event) => setNotes({ ...notes, [field]: event.target.value })}
              />
            </Field>
          ))}
          <div className="sm:col-span-2">
            <Button type="button" onClick={() => saveNotes.mutate()} disabled={!session}>
              메모 저장
            </Button>
          </div>
        </CardContent>
      </Card>
    </>
  )
}
