import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'

import { PageHeader } from '../components/PageHeader'
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
import { createStudent, fetchStudents, updateStudent, type Student } from '../api'

const FIELDS = [
  ['name', '이름'],
  ['school', '학교'],
  ['grade', '학년'],
  ['phone', '연락처'],
  ['omr_number', '수험번호'],
] as const

// 재원 상태는 FR-05가 정한 3종이다. 퇴원은 지우지 않고 상태로만 남겨 과거 기록을 보존한다.
const STATUS = { enrolled: '재원', paused: '휴원', withdrawn: '퇴원' } as const

const EMPTY = { name: '', school: '', grade: '', phone: '', omr_number: '' }

type Form = typeof EMPTY

function toPayload(form: Form, status: string) {
  return {
    name: form.name,
    school: form.school || null,
    grade: form.grade || null,
    phone: form.phone || null,
    omr_number: form.omr_number || null,
    status,
  }
}

function toForm(student: Student): Form {
  return {
    name: student.name,
    school: student.school ?? '',
    grade: student.grade ?? '',
    phone: student.phone ?? '',
    omr_number: student.omr_number ?? '',
  }
}

function StudentFields({
  prefix,
  form,
  onChange,
  className,
}: {
  prefix: string
  form: Form
  onChange: (form: Form) => void
  className?: string
}) {
  return FIELDS.map(([field, label]) => (
    <Field key={field} label={label} htmlFor={prefix + field} className={className}>
      <Input
        id={prefix + field}
        className="w-full"
        value={form[field]}
        onChange={(event) => onChange({ ...form, [field]: event.target.value })}
      />
    </Field>
  ))
}

export function StudentsPage() {
  const queryClient = useQueryClient()
  const students = useQuery({ queryKey: ['students'], queryFn: fetchStudents })
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

  // 목록에서 바로 퇴원시킨다. 지우지 않고 상태만 바꾸므로 과거 기록은 그대로다(FR-05)
  const withdraw = useMutation({
    mutationFn: (student: Student) => updateStudent(student.id, toPayload(toForm(student), 'withdrawn')),
    onSuccess: () => void refresh(),
  })

  function confirmWithdraw(student: Student) {
    const message =
      `${student.name} 학생을 퇴원 처리할까요?\n` +
      '기본 목록에서 빠지고 과거 기록은 남습니다. [수정]에서 다시 재원으로 바꿀 수 있습니다.'
    if (window.confirm(message)) withdraw.mutate(student)
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
    <section className="mb-8">
      <PageHeader title="학생 관리" />

      <Card className="mb-5">
        <CardContent className="py-4">
          <form className="flex flex-wrap items-end gap-3" onSubmit={submit}>
            <StudentFields
              prefix=""
              form={form}
              onChange={setForm}
              className="min-w-36 flex-1 xl:w-36 xl:flex-none"
            />
            <Button type="submit">학생 등록</Button>
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
                <TableHeaderCell>수험번호</TableHeaderCell>
                <TableHeaderCell>상태</TableHeaderCell>
                <TableHeaderCell />
              </TableRow>
            </TableHead>
            <TableBody>
              {visible.map((student) => (
                <TableRow key={student.id}>
                  <TableCell className="font-medium whitespace-nowrap">{student.name}</TableCell>
                  <TableCell className="text-muted-fg">{student.school}</TableCell>
                  <TableCell className="text-muted-fg">{student.grade}</TableCell>
                  <TableCell className="tabular-nums">{student.omr_number}</TableCell>
                  <TableCell className="text-muted-fg">
                    {STATUS[student.status as keyof typeof STATUS] ?? student.status}
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
                        disabled={withdraw.isPending}
                        onClick={() => confirmWithdraw(student)}
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
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {withdraw.isError && (
            <p role="alert" className="px-5 py-3 text-sm text-danger">
              {withdraw.error.message}
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
              <div className="col-span-2 mt-2 flex justify-end gap-2">
                <DialogClose asChild>
                  <Button type="button" variant="outline">
                    취소
                  </Button>
                </DialogClose>
                <Button type="submit">저장</Button>
              </div>
            </form>
          )}
        </DialogContent>
      </Dialog>

      {consulting && <ConsultDialog student={consulting} onClose={() => setConsulting(null)} />}
    </section>
  )
}
