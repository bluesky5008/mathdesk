import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'

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
      <h2>반 관리</h2>

      <form onSubmit={submit}>
        <label htmlFor="class-name">
          반 이름
          <input
            id="class-name"
            value={form.name}
            onChange={(event) => setForm({ ...form, name: event.target.value })}
          />
        </label>
        <label htmlFor="class-grade">
          학년
          <input
            id="class-grade"
            value={form.grade}
            onChange={(event) => setForm({ ...form, grade: event.target.value })}
          />
        </label>
        <button type="submit">반 등록</button>
        {create.isError && <p role="alert">{create.error.message}</p>}
      </form>

      <p>활성 {classes.data?.length ?? 0}개 반</p>
      <ul>
        {classes.data?.map((klass) => (
          <li key={klass.id}>
            {klass.name} · {klass.grade} · {describeSchedules(klass.schedules) || '시간표 없음'}
          </li>
        ))}
      </ul>
    </section>
  )
}
