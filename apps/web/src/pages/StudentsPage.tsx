import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'

import { createStudent, fetchStudents } from '../api'

const EMPTY = { name: '', school: '', grade: '', omr_number: '' }

export function StudentsPage() {
  const queryClient = useQueryClient()
  const students = useQuery({ queryKey: ['students'], queryFn: fetchStudents })
  const [form, setForm] = useState(EMPTY)

  const create = useMutation({
    mutationFn: () =>
      createStudent({
        name: form.name,
        school: form.school || null,
        grade: form.grade || null,
        omr_number: form.omr_number || null,
      }),
    onSuccess: () => {
      setForm(EMPTY)
      void queryClient.invalidateQueries({ queryKey: ['students'] })
    },
  })

  function submit(event: FormEvent) {
    event.preventDefault()
    create.mutate()
  }

  return (
    <section>
      <h2>학생 관리</h2>

      <form onSubmit={submit}>
        {(
          [
            ['name', '이름'],
            ['school', '학교'],
            ['grade', '학년'],
            ['omr_number', '수험번호'],
          ] as const
        ).map(([field, label]) => (
          <label key={field} htmlFor={field}>
            {label}
            <input
              id={field}
              value={form[field]}
              onChange={(event) => setForm({ ...form, [field]: event.target.value })}
            />
          </label>
        ))}
        <button type="submit">학생 등록</button>
        {create.isError && <p role="alert">{create.error.message}</p>}
      </form>

      <p>총 {students.data?.length ?? 0}명</p>
      <table>
        <thead>
          <tr>
            <th>이름</th>
            <th>학교</th>
            <th>학년</th>
            <th>수험번호</th>
            <th>상태</th>
          </tr>
        </thead>
        <tbody>
          {students.data?.map((student) => (
            <tr key={student.id}>
              <td>{student.name}</td>
              <td>{student.school}</td>
              <td>{student.grade}</td>
              <td>{student.omr_number}</td>
              <td>{student.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
