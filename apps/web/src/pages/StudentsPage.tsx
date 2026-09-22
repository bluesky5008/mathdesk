import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'

import { PageHeader } from '../components/PageHeader'
import { Button } from '../components/ui/button'
import { Card, CardContent } from '../components/ui/card'
import { Field } from '../components/ui/field'
import { Input } from '../components/ui/input'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from '../components/ui/table'
import { createStudent, fetchStudents } from '../api'

const FIELDS = [
  ['name', '이름'],
  ['school', '학교'],
  ['grade', '학년'],
  ['omr_number', '수험번호'],
] as const

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
    <section className="mb-8">
      <PageHeader title="학생 관리" />

      <Card className="mb-5">
        <CardContent className="py-4">
          <form className="flex items-end gap-3" onSubmit={submit}>
            {FIELDS.map(([field, label]) => (
              <Field key={field} label={label} htmlFor={field}>
                <Input
                  id={field}
                  className="w-36"
                  value={form[field]}
                  onChange={(event) => setForm({ ...form, [field]: event.target.value })}
                />
              </Field>
            ))}
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
          <p className="border-b px-5 py-3 text-sm text-muted-fg">
            총 {students.data?.length ?? 0}명
          </p>
          <Table>
            <TableHead>
              <TableRow>
                <TableHeaderCell>이름</TableHeaderCell>
                <TableHeaderCell>학교</TableHeaderCell>
                <TableHeaderCell>학년</TableHeaderCell>
                <TableHeaderCell>수험번호</TableHeaderCell>
                <TableHeaderCell>상태</TableHeaderCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {students.data?.map((student) => (
                <TableRow key={student.id}>
                  <TableCell className="font-medium">{student.name}</TableCell>
                  <TableCell className="text-muted-fg">{student.school}</TableCell>
                  <TableCell className="text-muted-fg">{student.grade}</TableCell>
                  <TableCell className="tabular-nums">{student.omr_number}</TableCell>
                  <TableCell className="text-muted-fg">{student.status}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </section>
  )
}
