import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Link } from 'react-router'

import { PageHeader } from '../components/PageHeader'
import { describeClasses, releaseFromToday, releaseNotice, useCurrentClasses } from '../lib/currentClasses'
import { today } from '../lib/date'
import { ConsultDialog } from './ConsultDialog'
import { Button } from '../components/ui/button'
import { Card, CardContent } from '../components/ui/card'
import { Dialog, DialogClose, DialogContent, DialogTitle } from '../components/ui/dialog'
import { Field } from '../components/ui/field'
import { Input } from '../components/ui/input'
import { Select } from '../components/ui/select'
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
  createEnrollment,
  createStudent,
  deleteStudent,
  fetchClasses,
  fetchEnrollments,
  fetchSchools,
  fetchStudents,
  updateStudent,
  type Klass,
  type School,
  type Student,
} from '../api'

const FIELDS = [
  ['name', '이름'],
  ['school_id', '학교'],
  ['grade', '학년'],
  ['phone', '학생 연락처'],
  ['guardian_phone', '학부모 연락처'],
  ['omr_number', '수험번호'],
  ['score_note', '성적'],
] as const

// 재원 상태는 FR-05가 정한 3종이다. 퇴원은 지우지 않고 상태로만 남겨 과거 기록을 보존한다.
const STATUS = { enrolled: '재원', paused: '휴원', withdrawn: '퇴원' } as const

// 학년은 고른다(TASK-79). 서버는 자유 문자열이라 목록 밖의 기존 값은 그 학생의 선택지에 남긴다
const GRADES = ['예비고1', '고1', '고2', '고3']

function gradeOptions(current: string) {
  return current && !GRADES.includes(current) ? [...GRADES, current] : GRADES
}

// 목록 칸의 드롭다운은 평소에는 글자처럼 보이고 가리키면 테두리가 보인다
const INLINE_SELECT = '-ml-2 h-8 border-transparent bg-transparent text-muted-fg hover:border-border'

// school은 고른 학교의 이름이다. 목록에 없는 현재 학교를 선택지에 남길 때만 쓰고 보내지 않는다
const EMPTY = { name: '', school_id: '', school: '', grade: '', phone: '', guardian_phone: '', omr_number: '', score_note: '' }

type Form = typeof EMPTY

function toPayload(form: Form, status: string) {
  return {
    name: form.name,
    school_id: form.school_id ? Number(form.school_id) : null,
    grade: form.grade || null,
    phone: form.phone || null,
    omr_number: form.omr_number || null,
    status,
    guardian_phone: form.guardian_phone || null,
    score_note: form.score_note || null,
  }
}

function toForm(student: Student): Form {
  return {
    name: student.name,
    school_id: student.school_id ? String(student.school_id) : '',
    school: student.school ?? '',
    grade: student.grade ?? '',
    phone: student.phone ?? '',
    guardian_phone: student.guardian_phone ?? '',
    omr_number: student.omr_number ?? '',
    score_note: student.score_note ?? '',
  }
}

// 학교는 등록된 학교 중에서 고른다(DCR-015). 목록에 없는 현재 학교는 그 학생의 선택지에 남긴다
function schoolOptions(schools: School[], form: Form) {
  const current = form.school_id && !schools.some((school) => String(school.id) === form.school_id)
  return current ? [...schools, { id: Number(form.school_id), name: form.school }] : schools
}

function StudentFields({
  prefix,
  form,
  onChange,
  schools,
  className,
}: {
  prefix: string
  form: Form
  onChange: (form: Form) => void
  schools: School[]
  className?: string
}) {
  return FIELDS.map(([field, label]) => (
    <Field key={field} label={label} htmlFor={prefix + field} className={className}>
      {field === 'school_id' ? (
        <Select
          id={prefix + field}
          className="w-full"
          value={form.school_id}
          onChange={(event) => onChange({ ...form, school_id: event.target.value })}
        >
          <option value="">선택</option>
          {schoolOptions(schools, form).map((school) => (
            <option key={school.id} value={school.id}>
              {school.name}
            </option>
          ))}
        </Select>
      ) : field === 'grade' ? (
        <Select
          id={prefix + field}
          className="w-full"
          value={form.grade}
          onChange={(event) => onChange({ ...form, grade: event.target.value })}
        >
          <option value="">선택</option>
          {gradeOptions(form.grade).map((grade) => (
            <option key={grade}>{grade}</option>
          ))}
        </Select>
      ) : (
        <Input
          id={prefix + field}
          className="w-full"
          value={form[field]}
          onChange={(event) => onChange({ ...form, [field]: event.target.value })}
        />
      )}
    </Field>
  ))
}

/**
 * 반 칸에서 바로 배정·해제한다(TASK-78). 운영 중인 반과 지금 배정된 반을 체크 목록으로 펼친다.
 * 체크는 오늘부터 배정, 체크 해제는 반 명단의 [해제]와 같은 규칙이다. 시작일 지정·반 옮기기는 반 탭에서 한다.
 * 표 감싸개가 가로 스크롤이라 띄우는 목록은 잘리므로 칸 안에서 펼친다.
 */
function ClassPicker({ student, current }: { student: Student; current: Klass[] }) {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const classes = useQuery({ queryKey: ['classes', true], queryFn: () => fetchClasses(true) })
  const assigned = new Set(current.map((klass) => klass.id))
  const options = (classes.data ?? []).filter((klass) => klass.is_active || assigned.has(klass.id))

  const toggle = useMutation({
    mutationFn: async ({ klass, assign }: { klass: Klass; assign: boolean }) => {
      const on = today()
      if (assign) {
        await createEnrollment(klass.id, student.id, on)
        return
      }
      const row = (await fetchEnrollments(klass.id, on)).find((r) => r.student_id === student.id)
      if (row) await releaseFromToday(klass.id, row)
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['enrollments'] }),
  })

  function change(klass: Klass) {
    const assign = !assigned.has(klass.id)
    if (assign || window.confirm(releaseNotice(student.name, klass.name))) toggle.mutate({ klass, assign })
  }

  return (
    <div>
      <button
        type="button"
        aria-expanded={open}
        className="rounded-sm text-left underline-offset-4 outline-none hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
        onClick={() => setOpen(!open)}
      >
        {describeClasses(current)}
        <span aria-hidden className="ml-1 text-muted-fg">
          {open ? '▴' : '▾'}
        </span>
      </button>
      {open && (
        <div className="mt-2 grid gap-1.5 rounded-md border bg-surface p-2">
          {options.map((klass) => (
            <label key={klass.id} className="flex items-center gap-2 whitespace-nowrap">
              <input
                type="checkbox"
                checked={assigned.has(klass.id)}
                disabled={toggle.isPending}
                onChange={() => change(klass)}
              />
              {klass.is_active ? klass.name : `${klass.name} (비활성)`}
            </label>
          ))}
          {classes.isSuccess && options.length === 0 && (
            <p className="text-xs text-muted-fg">운영 중인 반이 없습니다.</p>
          )}
        </div>
      )}
      {toggle.isError && (
        <p role="alert" className="mt-1 text-xs text-danger">
          {toggle.error.message}
        </p>
      )}
    </div>
  )
}

export function StudentsPage({ isDirector = false }: { isDirector?: boolean } = {}) {
  const queryClient = useQueryClient()
  const students = useQuery({ queryKey: ['students'], queryFn: fetchStudents })
  // 학교 목록은 원장만 읽는다(강사는 학생을 등록·수정하지 않는다)
  const schools = useQuery({ queryKey: ['schools'], queryFn: fetchSchools, enabled: isDirector })
  const currentClasses = useCurrentClasses()
  const [form, setForm] = useState(EMPTY)
  const [showWithdrawn, setShowWithdrawn] = useState(false)
  const [edit, setEdit] = useState<{ id: number; form: Form; status: string } | null>(null)
  const [consulting, setConsulting] = useState<{ id: number; name: string } | null>(null)

  const visible = (students.data ?? []).filter(
    (student) => showWithdrawn || student.status !== 'withdrawn',
  )

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['students'] })

  const create = useMutation({
    mutationFn: () => createStudent(toPayload(form, 'enrolled')),
    onSuccess: () => {
      setForm(EMPTY)
      void refresh()
    },
  })

  const save = useMutation({
    mutationFn: (target: { id: number; form: Form; status: string }) =>
      updateStudent(target.id, toPayload(target.form, target.status)),
    onSuccess: () => {
      setEdit(null)
      void refresh()
    },
  })

  // 목록에서 바로 바꾼다(학교·학년·상태, [퇴원]). 퇴원은 지우지 않고 상태만 바꾸므로 과거 기록은 그대로다(FR-05)
  const quick = useMutation({
    mutationFn: ({ student, form, status }: { student: Student; form: Form; status: string }) =>
      updateStudent(student.id, toPayload(form, status)),
    onSuccess: () => void refresh(),
  })

  // 학생은 확인 없이 바로 하드 삭제한다(DCR-013). 되살리려면 백업에서 복원해야 한다
  const remove = useMutation({
    mutationFn: (id: number) => deleteStudent(id),
    onSuccess: () => void refresh(),
  })

  function changeStatus(student: Student, status: string) {
    const message =
      `${student.name} 학생을 퇴원 처리할까요?\n` +
      '기본 목록에서 빠지고 과거 기록은 남습니다. [수정]에서 다시 재원으로 바꿀 수 있습니다.'
    if (status !== 'withdrawn' || window.confirm(message)) {
      quick.mutate({ student, form: toForm(student), status })
    }
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
      <PageHeader title="학생 관리" />

      <Card className="mb-5">
        <CardContent className="py-4">
          <form className="flex flex-wrap items-end gap-3" onSubmit={submit}>
            <StudentFields
              prefix=""
              form={form}
              onChange={setForm}
              schools={schools.data ?? []}
              className="min-w-36 flex-1 xl:w-36 xl:flex-none"
            />
            <Button type="submit">학생 등록</Button>
          </form>
          {schools.isSuccess && schools.data.length === 0 && (
            <p className="mt-3 text-xs text-muted-fg">
              등록된 학교가 없습니다.{' '}
              <Link to="/students/schools" className="underline underline-offset-4">
                학교 탭
              </Link>
              에서 먼저 학교를 등록하세요.
            </p>
          )}
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
            <p className="text-sm text-muted-fg">총 {visible.length}명</p>
            <Toggle pressed={showWithdrawn} onClick={() => setShowWithdrawn(!showWithdrawn)}>
              퇴원 포함
            </Toggle>
          </div>
          <Table>
            <TableHead>
              <TableRow>
                <TableHeaderCell>이름</TableHeaderCell>
                <TableHeaderCell>학교</TableHeaderCell>
                <TableHeaderCell>학년</TableHeaderCell>
                <TableHeaderCell>반</TableHeaderCell>
                <TableHeaderCell>학생 연락처</TableHeaderCell>
                <TableHeaderCell>학부모 연락처</TableHeaderCell>
                <TableHeaderCell>수험번호</TableHeaderCell>
                <TableHeaderCell>상태</TableHeaderCell>
                <TableHeaderCell>성적</TableHeaderCell>
                <TableHeaderCell />
              </TableRow>
            </TableHead>
            <TableBody>
              {visible.map((student) => (
                <TableRow key={student.id}>
                  <TableCell className="font-medium whitespace-nowrap">{student.name}</TableCell>
                  <TableCell className="break-keep text-muted-fg">
                    {isDirector ? (
                      <Select
                        aria-label={`${student.name} 학교`}
                        className={INLINE_SELECT}
                        value={student.school_id ?? ''}
                        disabled={quick.isPending}
                        onChange={(event) =>
                          quick.mutate({
                            student,
                            form: { ...toForm(student), school_id: event.target.value },
                            status: student.status,
                          })
                        }
                      >
                        <option value="">—</option>
                        {schoolOptions(schools.data ?? [], toForm(student)).map((school) => (
                          <option key={school.id} value={school.id}>
                            {school.name}
                          </option>
                        ))}
                      </Select>
                    ) : (
                      student.school
                    )}
                  </TableCell>
                  <TableCell className="text-muted-fg">
                    {isDirector ? (
                      <Select
                        aria-label={`${student.name} 학년`}
                        className={INLINE_SELECT}
                        value={student.grade ?? ''}
                        disabled={quick.isPending}
                        onChange={(event) =>
                          quick.mutate({
                            student,
                            form: { ...toForm(student), grade: event.target.value },
                            status: student.status,
                          })
                        }
                      >
                        <option value="">—</option>
                        {gradeOptions(student.grade ?? '').map((grade) => (
                          <option key={grade}>{grade}</option>
                        ))}
                      </Select>
                    ) : (
                      student.grade
                    )}
                  </TableCell>
                  <TableCell className="min-w-24 break-keep">
                    {isDirector && student.status !== 'withdrawn' ? (
                      <ClassPicker student={student} current={currentClasses.get(student.id) ?? []} />
                    ) : (
                      describeClasses(currentClasses.get(student.id))
                    )}
                  </TableCell>
                  <TableCell className="tabular-nums whitespace-nowrap">{student.phone}</TableCell>
                  <TableCell className="tabular-nums whitespace-nowrap">{student.guardian_phone}</TableCell>
                  <TableCell className="tabular-nums">{student.omr_number}</TableCell>
                  <TableCell className="text-muted-fg">
                    {isDirector ? (
                      <Select
                        aria-label={`${student.name} 상태`}
                        className={INLINE_SELECT}
                        value={student.status}
                        disabled={quick.isPending}
                        onChange={(event) => changeStatus(student, event.target.value)}
                      >
                        {Object.entries(STATUS).map(([value, label]) => (
                          <option key={value} value={value}>
                            {label}
                          </option>
                        ))}
                      </Select>
                    ) : (
                      (STATUS[student.status as keyof typeof STATUS] ?? student.status)
                    )}
                  </TableCell>
                  {/* 성적은 두 줄까지만 보이고 전체는 마우스를 올리거나 수정 창에서 본다 */}
                  <TableCell className="min-w-32 max-w-56 text-muted-fg">
                    {student.score_note && (
                      <p className="line-clamp-2 break-keep" title={student.score_note}>
                        {student.score_note}
                      </p>
                    )}
                  </TableCell>
                  <TableCell className="text-right whitespace-nowrap">
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="mr-1"
                      onClick={() => setConsulting({ id: student.id, name: student.name })}
                    >
                      상담
                    </Button>
                    {student.status !== 'withdrawn' && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="mr-1"
                        aria-label={`${student.name} 퇴원`}
                        disabled={quick.isPending}
                        onClick={() => changeStatus(student, 'withdrawn')}
                      >
                        퇴원
                      </Button>
                    )}
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        setEdit({ id: student.id, form: toForm(student), status: student.status })
                      }
                    >
                      수정
                    </Button>
                    {isDirector && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="ml-1 text-danger"
                        aria-label={`${student.name} 삭제`}
                        disabled={remove.isPending}
                        onClick={() => remove.mutate(student.id)}
                      >
                        삭제
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {quick.isError && (
            <p role="alert" className="px-5 py-3 text-sm text-danger">
              {quick.error.message}
            </p>
          )}
          {remove.isError && (
            <p role="alert" className="px-5 py-3 text-sm text-danger">
              {remove.error.message}
            </p>
          )}
        </CardContent>
      </Card>

      <Dialog open={edit !== null} onOpenChange={(open) => !open && setEdit(null)}>
        <DialogContent>
          <DialogTitle className="mb-4 text-base font-semibold">학생 수정</DialogTitle>
          {edit && (
            <form className="grid grid-cols-2 gap-3" onSubmit={submitEdit}>
              <StudentFields
                prefix="edit-"
                form={edit.form}
                onChange={(form) => setEdit({ ...edit, form })}
                schools={schools.data ?? []}
              />
              <Field label="상태" htmlFor="edit-status">
                <Select
                  id="edit-status"
                  className="w-full"
                  value={edit.status}
                  onChange={(event) => setEdit({ ...edit, status: event.target.value })}
                >
                  {Object.entries(STATUS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </Select>
              </Field>
              {save.isError && (
                <p role="alert" className="col-span-2 text-sm text-danger">
                  {save.error.message}
                </p>
              )}
              <div className="col-span-2 mt-2 flex justify-between gap-2">
                {/* 원장은 상태와 관계없이 학생을 확인 없이 바로 삭제한다(DCR-012·DCR-013) */}
                {isDirector ? (
                  <Button type="button" variant="ghost" className="text-danger" onClick={() => {
                      remove.mutate(edit.id)
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

      {consulting && <ConsultDialog student={consulting} onClose={() => setConsulting(null)} />}
    </section>
  )
}
