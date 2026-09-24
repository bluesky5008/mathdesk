import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Fragment, useState, type FormEvent } from 'react'

import { PageHeader } from '../components/PageHeader'
import { Button } from '../components/ui/button'
import { Card, CardContent } from '../components/ui/card'
import { Dialog, DialogClose, DialogContent, DialogTitle } from '../components/ui/dialog'
import { Field } from '../components/ui/field'
import { Input } from '../components/ui/input'
import { Select } from '../components/ui/select'
import { Toggle } from '../components/ui/toggle'
import {
  createClass,
  deleteClass,
  fetchClassDeletionPreview,
  createEnrollment,
  endEnrollment,
  fetchClasses,
  fetchEnrollments,
  fetchStudents,
  fetchUsers,
  updateClass,
  type AppUserAccount,
  type Klass,
  type Schedule,
} from '../api'
import { today } from '../lib/date'
import { DeleteDialog } from './DeleteDialog'

const WEEKDAYS = ['월', '화', '수', '목', '금', '토', '일']

export function describeSchedules(schedules: Schedule[]): string {
  // 수업 길이가 같아 시작 시각만 보여 준다(FR-07, DCR-007)
  return schedules
    .map((schedule) => `${WEEKDAYS[schedule.weekday]} ${schedule.start_time.slice(0, 5)}`)
    .join(' · ')
}

/** 시간표를 API로 보낼 모양으로 — 요일과 시작 시각(HH:MM)만. 종료 시각은 쓰지 않는다 */
function slots(schedules: Schedule[]): Schedule[] {
  return schedules.map(({ weekday, start_time }) => ({ weekday, start_time: start_time.slice(0, 5) }))
}

/** 요일·시작 시각 줄을 더하고 빼는 시간표 편집기(FR-07). 수업 길이가 같아 종료 시각은 받지 않는다 */
function ScheduleEditor({
  idPrefix,
  schedules,
  onChange,
}: {
  idPrefix: string
  schedules: Schedule[]
  onChange: (schedules: Schedule[]) => void
}) {
  function update(index: number, patch: Partial<Schedule>) {
    onChange(schedules.map((schedule, i) => (i === index ? { ...schedule, ...patch } : schedule)))
  }

  return (
    <fieldset className="grid gap-2">
      <legend className="mb-1 text-xs font-medium text-muted-fg">시간표</legend>
      {schedules.map((schedule, index) => {
        const nth = `${index + 1}번째 수업`
        return (
          <div key={index} className="flex flex-wrap items-center gap-2">
            <Select
              id={`${idPrefix}-weekday-${index}`}
              aria-label={`${nth} 요일`}
              value={schedule.weekday}
              onChange={(event) => update(index, { weekday: Number(event.target.value) })}
            >
              {WEEKDAYS.map((label, weekday) => (
                <option key={label} value={weekday}>
                  {label}
                </option>
              ))}
            </Select>
            <Input
              id={`${idPrefix}-start-${index}`}
              type="time"
              aria-label={`${nth} 시작 시각`}
              className="w-32"
              value={schedule.start_time.slice(0, 5)}
              onChange={(event) => update(index, { start_time: event.target.value })}
            />
            <Button
              type="button"
              variant="ghost"
              size="sm"
              aria-label={`${nth} 삭제`}
              onClick={() => onChange(schedules.filter((_, i) => i !== index))}
            >
              삭제
            </Button>
          </div>
        )
      })}
      <div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() =>
            onChange([
              ...schedules,
              // 새 줄은 마지막 줄의 시작 시각을 이어받는다(대개 같은 시각에 요일만 다르다)
              { weekday: 0, start_time: schedules.at(-1)?.start_time.slice(0, 5) ?? '18:00' },
            ])
          }
        >
          시간 추가
        </Button>
      </div>
    </fieldset>
  )
}

/** 오늘 기준 명단을 보여주고, 배정은 오늘부터·해제는 오늘까지로 기간을 끊는다. */
function RosterDialog({ klass, onClose }: { klass: Klass; onClose: () => void }) {
  const queryClient = useQueryClient()
  const on = today()
  const enrollments = useQuery({
    queryKey: ['enrollments', klass.id, on],
    queryFn: () => fetchEnrollments(klass.id, on),
  })
  const students = useQuery({ queryKey: ['students'], queryFn: fetchStudents })
  const [picked, setPicked] = useState('')

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['enrollments', klass.id] })
  const assign = useMutation({
    mutationFn: (studentId: number) => createEnrollment(klass.id, studentId, on),
    onSuccess: () => {
      setPicked('')
      void refresh()
    },
  })
  const release = useMutation({
    mutationFn: (enrollmentId: number) => endEnrollment(klass.id, enrollmentId, on),
    onSuccess: () => void refresh(),
  })

  const byId = new Map((students.data ?? []).map((student) => [student.id, student]))
  const enrolled = new Set((enrollments.data ?? []).map((row) => row.student_id))
  const error = assign.error ?? release.error

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogTitle className="mb-4 text-base font-semibold">반 명단 — {klass.name}</DialogTitle>

        <div className="mb-4 flex items-end gap-2">
          <Field label="학생" htmlFor="roster-student" className="flex-1">
            <Select
              id="roster-student"
              className="w-full"
              value={picked}
              onChange={(event) => setPicked(event.target.value)}
            >
              <option value="">학생 선택</option>
              {(students.data ?? [])
                .filter((student) => !enrolled.has(student.id) && student.status !== 'withdrawn')
                .map((student) => (
                  <option key={student.id} value={student.id}>
                    {student.name}
                  </option>
                ))}
            </Select>
          </Field>
          <Button type="button" disabled={!picked} onClick={() => assign.mutate(Number(picked))}>
            배정
          </Button>
        </div>

        <ul className="divide-y border-t">
          {(enrollments.data ?? []).map((row) => (
            <li key={row.id} className="flex items-center justify-between gap-3 py-2 text-sm">
              <span>
                {byId.get(row.student_id)?.name ?? `학생 ${row.student_id}`}
                <span className="ml-2 text-xs text-muted-fg">
                  {row.end_date ? `${row.end_date} 종료` : `${row.start_date} 배정`}
                </span>
              </span>
              {!row.end_date && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => release.mutate(row.id)}
                >
                  해제
                </Button>
              )}
            </li>
          ))}
        </ul>
        {enrollments.data?.length === 0 && (
          <p className="py-3 text-sm text-muted-fg">배정된 학생이 없습니다.</p>
        )}

        {error && (
          <p role="alert" className="mt-3 text-sm text-danger">
            {error.message}
          </p>
        )}
        <div className="mt-4 flex justify-end">
          <DialogClose asChild>
            <Button type="button" variant="outline">
              닫기
            </Button>
          </DialogClose>
        </div>
      </DialogContent>
    </Dialog>
  )
}

const DELETE_LABELS = {
  schedules: '시간표',
  enrollments: '반 배정',
  sessions: '수업',
  daily_records: '학생 일일 기록',
  exams_unlinked: '반 연결이 끊기는 시험',
}

// 담당 강사 선택지: 사용 중인 강사. 이미 지정된 강사가 나중에 사용 안 함이 되었으면 그 사람도 남겨
// 반을 고칠 때 담당이 저절로 지워지지 않게 한다(서버도 기존 지정은 그대로 허용한다)
function TeacherSelect({
  id,
  accounts,
  value,
  onChange,
}: {
  id: string
  accounts: AppUserAccount[]
  value: number | null
  onChange: (teacherId: number | null) => void
}) {
  const options = accounts.filter(
    (account) => account.role === 'teacher' && (account.is_active || account.id === value),
  )
  return (
    <Select
      id={id}
      className="w-full"
      value={value === null ? '' : String(value)}
      onChange={(event) => onChange(event.target.value ? Number(event.target.value) : null)}
    >
      <option value="">지정 안 함</option>
      {options.map((account) => (
        <option key={account.id} value={account.id}>
          {account.is_active ? account.display_name : `${account.display_name} (사용 안 함)`}
        </option>
      ))}
    </Select>
  )
}

// 담당 강사 지정은 원장만 한다 — 계정 목록(`/users`)도 원장만 볼 수 있다(FR-02·FR-07)
export function ClassesPage({ isDirector = false }: { isDirector?: boolean } = {}) {
  const queryClient = useQueryClient()
  const accounts = useQuery({ queryKey: ['users'], queryFn: fetchUsers, enabled: isDirector })
  const teacherName = (id: number | null) =>
    accounts.data?.find((account) => account.id === id)?.display_name
  const [showInactive, setShowInactive] = useState(false)
  const classes = useQuery({
    queryKey: ['classes', showInactive],
    queryFn: () => fetchClasses(showInactive),
  })
  const [form, setForm] = useState<{
    name: string
    grade: string
    teacher_id: number | null
    schedules: Schedule[]
  }>({ name: '', grade: '', teacher_id: null, schedules: [] })
  const [edit, setEdit] = useState<Klass | null>(null)
  const [deleting, setDeleting] = useState<Klass | null>(null)
  const [roster, setRoster] = useState<Klass | null>(null)

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['classes'] })

  const create = useMutation({
    mutationFn: () =>
      createClass({
        name: form.name,
        grade: form.grade || null,
        teacher_id: form.teacher_id,
        schedules: slots(form.schedules),
      }),
    onSuccess: () => {
      setForm({ name: '', grade: '', teacher_id: null, schedules: [] })
      void refresh()
    },
  })

  // PATCH는 전치환이라 보내지 않은 시간표·담당 강사는 지워진다. 수정 대상 반의 값을 그대로 함께 보낸다.
  const save = useMutation({
    mutationFn: (klass: Klass) =>
      updateClass(klass.id, {
        name: klass.name,
        grade: klass.grade,
        teacher_id: klass.teacher_id,
        is_active: klass.is_active,
        schedules: slots(klass.schedules),
      }),
    onSuccess: () => {
      setEdit(null)
      void refresh()
    },
  })

  // 목록에서 바로 비활성으로 돌린다. 지우지 않으므로 이 반의 과거 기록은 그대로다(FR-07)
  const deactivate = useMutation({
    mutationFn: (klass: Klass) =>
      updateClass(klass.id, {
        name: klass.name,
        grade: klass.grade,
        teacher_id: klass.teacher_id,
        is_active: false,
        schedules: klass.schedules,
      }),
    onSuccess: () => void refresh(),
  })

  function confirmDeactivate(klass: Klass) {
    const message =
      `${klass.name} 반을 비활성으로 바꿀까요?\n` +
      '기본 목록과 활성 반 수에서 빠지고 과거 기록은 남습니다. [수정]에서 다시 활성으로 바꿀 수 있습니다.'
    if (window.confirm(message)) deactivate.mutate(klass)
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    create.mutate()
  }

  function submitEdit(event: FormEvent) {
    event.preventDefault()
    if (edit) save.mutate(edit)
  }

  return (
    <section>
      <PageHeader title="반 관리" />

      <Card className="mb-5">
        <CardContent className="py-4">
          <form className="flex flex-wrap items-end gap-3" onSubmit={submit}>
            <Field label="반 이름" htmlFor="class-name" className="min-w-40 flex-1 xl:flex-none">
              <Input
                id="class-name"
                className="w-full xl:w-48"
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
              />
            </Field>
            <Field label="학년" htmlFor="class-grade" className="min-w-28 flex-1 xl:flex-none">
              <Input
                id="class-grade"
                className="w-full xl:w-28"
                value={form.grade}
                onChange={(event) => setForm({ ...form, grade: event.target.value })}
              />
            </Field>
            {isDirector && (
              <Field label="담당 강사" htmlFor="class-teacher" className="min-w-36 flex-1 xl:flex-none">
                <TeacherSelect
                  id="class-teacher"
                  accounts={accounts.data ?? []}
                  value={form.teacher_id}
                  onChange={(teacher_id) => setForm({ ...form, teacher_id })}
                />
              </Field>
            )}
            <div className="basis-full">
              <ScheduleEditor
                idPrefix="class-schedule"
                schedules={form.schedules}
                onChange={(schedules) => setForm({ ...form, schedules })}
              />
            </div>
            <Button type="submit">반 등록</Button>
          </form>
          {create.isError && (
            <p role="alert" className="mt-3 text-sm text-danger">
              {create.error.message}
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          <div className="flex items-center justify-between gap-3 border-b px-5 py-3">
            <p className="text-sm text-muted-fg">
              {showInactive ? '총' : '활성'} {classes.data?.length ?? 0}개 반
            </p>
            <Toggle pressed={showInactive} onClick={() => setShowInactive(!showInactive)}>
              비활성 포함
            </Toggle>
          </div>
          <ul className="divide-y">
            {classes.data?.map((klass) => (
              <li key={klass.id} className="flex items-center justify-between gap-3 px-5 py-3">
                {/* 첫 줄은 반, 둘째 줄은 시간표 — 시간표가 길어도 반 이름 줄이 흔들리지 않는다 */}
                <span className="grid min-w-0 gap-0.5 text-sm">
                  <span>
                    {[klass.name, klass.grade, teacherName(klass.teacher_id)].filter(Boolean).join(' · ')}
                    {!klass.is_active && <span className="ml-2 text-muted-fg">(비활성)</span>}
                  </span>
                  <span className="text-xs text-muted-fg tabular-nums">
                    {klass.schedules.length === 0
                      ? '시간표 없음'
                      : klass.schedules.map((schedule, index) => (
                          // 수업 하나("화 18:00")는 줄바꿈으로 쪼개지 않는다
                          <Fragment key={index}>
                            {index > 0 && ' · '}
                            <span className="whitespace-nowrap">{describeSchedules([schedule])}</span>
                          </Fragment>
                        ))}
                  </span>
                </span>
                <span className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setRoster(klass)}
                  >
                    명단
                  </Button>
                  {klass.is_active && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      aria-label={`${klass.name} 비활성`}
                      disabled={deactivate.isPending}
                      onClick={() => confirmDeactivate(klass)}
                    >
                      비활성
                    </Button>
                  )}
                  <Button type="button" variant="outline" size="sm" onClick={() => setEdit(klass)}>
                    수정
                  </Button>
                </span>
              </li>
            ))}
          </ul>
          {deactivate.isError && (
            <p role="alert" className="px-5 py-3 text-sm text-danger">
              {deactivate.error.message}
            </p>
          )}
        </CardContent>
      </Card>

      {roster && <RosterDialog klass={roster} onClose={() => setRoster(null)} />}

      <Dialog open={edit !== null} onOpenChange={(open) => !open && setEdit(null)}>
        <DialogContent>
          <DialogTitle className="mb-4 text-base font-semibold">반 수정</DialogTitle>
          {edit && (
            <form className="grid grid-cols-2 gap-3" onSubmit={submitEdit}>
              <Field label="반 이름" htmlFor="edit-class-name">
                <Input
                  id="edit-class-name"
                  className="w-full"
                  value={edit.name}
                  onChange={(event) => setEdit({ ...edit, name: event.target.value })}
                />
              </Field>
              <Field label="학년" htmlFor="edit-class-grade">
                <Input
                  id="edit-class-grade"
                  className="w-full"
                  value={edit.grade ?? ''}
                  onChange={(event) => setEdit({ ...edit, grade: event.target.value || null })}
                />
              </Field>
              <Field label="활성 여부" htmlFor="edit-class-active">
                <Select
                  id="edit-class-active"
                  className="w-full"
                  value={String(edit.is_active)}
                  onChange={(event) => setEdit({ ...edit, is_active: event.target.value === 'true' })}
                >
                  <option value="true">활성</option>
                  <option value="false">비활성</option>
                </Select>
              </Field>
              {isDirector && (
                <Field label="담당 강사" htmlFor="edit-class-teacher">
                  <TeacherSelect
                    id="edit-class-teacher"
                    accounts={accounts.data ?? []}
                    value={edit.teacher_id}
                    onChange={(teacher_id) => setEdit({ ...edit, teacher_id })}
                  />
                </Field>
              )}
              <div className="col-span-2">
                <ScheduleEditor
                  idPrefix="edit-class-schedule"
                  schedules={edit.schedules}
                  onChange={(schedules) => setEdit({ ...edit, schedules })}
                />
              </div>
              {save.isError && (
                <p role="alert" className="col-span-2 text-sm text-danger">
                  {save.error.message}
                </p>
              )}
              <div className="col-span-2 mt-2 flex justify-between gap-2">
                {/* 퇴원·비활성으로 저장된 대상만 삭제할 수 있다(DCR-006). 선행 조건은 서버도 다시 확인한다 */}
                {classes.data?.find((c) => c.id === edit.id)?.is_active === false ? (
                  <Button type="button" variant="ghost" className="text-danger" onClick={() => {
                      setDeleting(classes.data?.find((c) => c.id === edit.id) ?? null)
                      setEdit(null)
                    }}>
                    삭제
                  </Button>
                ) : (
                  <span />
                )}
                <div className="flex gap-2">
                  <DialogClose asChild>
                    <Button type="button" variant="outline">
                      취소
                    </Button>
                  </DialogClose>
                  <Button type="submit">저장</Button>
                </div>
              </div>
            </form>
          )}
        </DialogContent>
      </Dialog>

      {deleting && (
        <DeleteDialog
          title={`${deleting.name} 반 삭제`}
          name={deleting.name}
          labels={DELETE_LABELS}
          preview={() => fetchClassDeletionPreview(deleting.id)}
          remove={(confirmName) => deleteClass(deleting.id, confirmName)}
          onDone={() => {
            setDeleting(null)
            void refresh()
          }}
          onClose={() => setDeleting(null)}
        />
      )}
    </section>
  )
}
