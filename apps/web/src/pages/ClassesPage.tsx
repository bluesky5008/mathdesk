import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'

import { PageHeader } from '../components/PageHeader'
import { Button } from '../components/ui/button'
import { Card, CardContent } from '../components/ui/card'
import { Dialog, DialogClose, DialogContent, DialogTitle } from '../components/ui/dialog'
import { Field } from '../components/ui/field'
import { Input } from '../components/ui/input'
import { Select } from '../components/ui/select'
import { Toggle } from '../components/ui/toggle'
import { createClass, fetchClasses, updateClass, type Klass, type Schedule } from '../api'

const WEEKDAYS = ['월', '화', '수', '목', '금', '토', '일']

export function describeSchedules(schedules: Schedule[]): string {
  return schedules
    .map(
      (schedule) =>
        `${WEEKDAYS[schedule.weekday]} ${schedule.start_time.slice(0, 5)}~${schedule.end_time.slice(0, 5)}`,
    )
    .join(', ')
}

export function ClassesPage() {
  const queryClient = useQueryClient()
  const [showInactive, setShowInactive] = useState(false)
  const classes = useQuery({
    queryKey: ['classes', showInactive],
    queryFn: () => fetchClasses(showInactive),
  })
  const [form, setForm] = useState({ name: '', grade: '' })
  const [edit, setEdit] = useState<Klass | null>(null)

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['classes'] })

  const create = useMutation({
    mutationFn: () => createClass({ name: form.name, grade: form.grade || null, schedules: [] }),
    onSuccess: () => {
      setForm({ name: '', grade: '' })
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
        schedules: klass.schedules,
      }),
    onSuccess: () => {
      setEdit(null)
      void refresh()
    },
  })

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
                <span className="text-sm">
                  {klass.name} · {klass.grade} ·{' '}
                  {describeSchedules(klass.schedules) || '시간표 없음'}
                  {!klass.is_active && <span className="ml-2 text-muted-fg">(비활성)</span>}
                </span>
                <Button type="button" variant="outline" size="sm" onClick={() => setEdit(klass)}>
                  수정
                </Button>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

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
              <p className="col-span-2 text-xs text-muted-fg">
                시간표: {describeSchedules(edit.schedules) || '없음'}
              </p>
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
    </section>
  )
}
