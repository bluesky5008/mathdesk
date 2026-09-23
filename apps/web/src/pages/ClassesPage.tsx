import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'

import { PageHeader } from '../components/PageHeader'
import { Button } from '../components/ui/button'
import { Card, CardContent } from '../components/ui/card'
import { Field } from '../components/ui/field'
import { Input } from '../components/ui/input'
import { createClass, fetchClasses, type Schedule } from '../api'

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
  const classes = useQuery({ queryKey: ['classes'], queryFn: fetchClasses })
  const [form, setForm] = useState({ name: '', grade: '' })

  const create = useMutation({
    mutationFn: () => createClass({ name: form.name, grade: form.grade || null, schedules: [] }),
    onSuccess: () => {
      setForm({ name: '', grade: '' })
      void queryClient.invalidateQueries({ queryKey: ['classes'] })
    },
  })

  function submit(event: FormEvent) {
    event.preventDefault()
    create.mutate()
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
          <p className="border-b px-5 py-3 text-sm text-muted-fg">
            활성 {classes.data?.length ?? 0}개 반
          </p>
          <ul className="divide-y">
            {classes.data?.map((klass) => (
              <li key={klass.id} className="px-5 py-3 text-sm">
                {klass.name} · {klass.grade} · {describeSchedules(klass.schedules) || '시간표 없음'}
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </section>
  )
}
