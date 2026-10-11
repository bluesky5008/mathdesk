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
import { createSchool, deleteSchool, fetchSchools, updateSchool } from '../api'

/**
 * 원장이 학교를 등록·수정·삭제한다(FR-43, DCR-015). 학생의 학교 드롭다운은 이 목록에서 고른다.
 * 이름을 바꾸거나 지우면 학생 목록의 학교 표시도 바뀌므로 학생 조회도 새로 고친다.
 */
export function SchoolsPage() {
  const queryClient = useQueryClient()
  const schools = useQuery({ queryKey: ['schools'], queryFn: fetchSchools })
  const [name, setName] = useState('')
  const [edit, setEdit] = useState<{ id: number; name: string } | null>(null)

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['schools'] })
    void queryClient.invalidateQueries({ queryKey: ['students'] })
  }

  const create = useMutation({
    mutationFn: () => createSchool(name),
    onSuccess: () => {
      setName('')
      refresh()
    },
  })

  const rename = useMutation({
    mutationFn: (target: { id: number; name: string }) => updateSchool(target.id, target.name),
    onSuccess: () => {
      setEdit(null)
      refresh()
    },
  })

  // 확인 없이 바로 지운다. 그 학교 학생들의 학교는 비고 다른 정보는 그대로다(사용자 결정)
  const remove = useMutation({ mutationFn: deleteSchool, onSuccess: refresh })

  function submit(event: FormEvent) {
    event.preventDefault()
    create.mutate()
  }

  function submitRename(event: FormEvent) {
    event.preventDefault()
    if (edit) rename.mutate(edit)
  }

  const error = rename.error ?? remove.error

  return (
    <section>
      <PageHeader title="학교 관리" />

      <Card className="mb-5 max-w-2xl">
        <CardContent className="py-4">
          <form className="flex flex-wrap items-end gap-3" onSubmit={submit}>
            <Field label="학교 이름" htmlFor="school-name" className="min-w-48 flex-1">
              <Input id="school-name" value={name} onChange={(event) => setName(event.target.value)} />
            </Field>
            <Button type="submit" disabled={create.isPending}>
              학교 등록
            </Button>
          </form>
          {create.isError && (
            <p role="alert" className="mt-3 text-sm text-danger">
              {create.error.message}
            </p>
          )}
        </CardContent>
      </Card>

      <Card className="max-w-2xl">
        <CardContent className="p-0">
          <Table>
            <TableHead>
              <TableRow>
                <TableHeaderCell>학교 이름</TableHeaderCell>
                <TableHeaderCell>학생 수</TableHeaderCell>
                <TableHeaderCell />
              </TableRow>
            </TableHead>
            <TableBody>
              {(schools.data ?? []).map((school) => (
                <TableRow key={school.id}>
                  {edit?.id === school.id ? (
                    <TableCell colSpan={3}>
                      <form className="flex flex-wrap items-center gap-2" onSubmit={submitRename}>
                        <Input
                          aria-label={`${school.name} 새 이름`}
                          className="min-w-40 flex-1"
                          value={edit.name}
                          onChange={(event) => setEdit({ ...edit, name: event.target.value })}
                        />
                        <Button type="submit" size="sm" disabled={rename.isPending}>
                          저장
                        </Button>
                        <Button type="button" variant="ghost" size="sm" onClick={() => setEdit(null)}>
                          취소
                        </Button>
                      </form>
                    </TableCell>
                  ) : (
                    <>
                      <TableCell className="font-medium break-keep">{school.name}</TableCell>
                      <TableCell className="tabular-nums text-muted-fg">{school.student_count}</TableCell>
                      <TableCell className="text-right whitespace-nowrap">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          aria-label={`${school.name} 수정`}
                          onClick={() => {
                            rename.reset()
                            setEdit({ id: school.id, name: school.name })
                          }}
                        >
                          수정
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="ml-1 text-danger"
                          aria-label={`${school.name} 삭제`}
                          disabled={remove.isPending}
                          onClick={() => remove.mutate(school.id)}
                        >
                          삭제
                        </Button>
                      </TableCell>
                    </>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {schools.isSuccess && schools.data.length === 0 && (
            <p className="px-5 py-4 text-sm text-muted-fg">등록된 학교가 없습니다.</p>
          )}
          {error && (
            <p role="alert" className="px-5 py-3 text-sm text-danger">
              {error.message}
            </p>
          )}
        </CardContent>
      </Card>
    </section>
  )
}
