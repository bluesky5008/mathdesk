import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'

import { Button } from '../components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Field } from '../components/ui/field'
import { Input } from '../components/ui/input'
import { fetchTimetable, saveClassMinutes } from '../api'

// FR-42 — 학원 전체에 하나인 수업 길이. 주간 시간표 블록의 길이가 된다(원장 전용)
export function ClassMinutesSetting() {
  const queryClient = useQueryClient()
  const timetable = useQuery({ queryKey: ['timetable'], queryFn: fetchTimetable })
  const [edited, setEdited] = useState<string | null>(null)
  const value = edited ?? String(timetable.data?.class_minutes ?? '')

  const save = useMutation({
    mutationFn: () => saveClassMinutes(Number(value)),
    onSuccess: () => {
      setEdited(null)
      void queryClient.invalidateQueries({ queryKey: ['timetable'] })
    },
  })

  function submit(event: FormEvent) {
    event.preventDefault()
    save.mutate()
  }

  return (
    <Card className="mt-5 max-w-2xl">
      <CardHeader>
        <CardTitle>수업 길이</CardTitle>
        <CardDescription>
          모든 반에 같은 길이를 씁니다. 주간 시간표는 시작 시각부터 이 길이만큼 수업을 그립니다.
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-4">
        <form className="flex flex-wrap items-end gap-3" onSubmit={submit}>
          <Field label="수업 길이(분)" htmlFor="class-minutes">
            <Input
              id="class-minutes"
              type="number"
              min={30}
              max={480}
              step={5}
              className="w-28"
              value={value}
              onChange={(event) => setEdited(event.target.value)}
            />
          </Field>
          <Button type="submit" disabled={save.isPending}>
            수업 길이 저장
          </Button>
          {save.isSuccess && (
            <span role="status" className="text-sm text-success">
              저장했습니다
            </span>
          )}
        </form>
        {save.isError && (
          <p role="alert" className="mt-3 text-sm text-danger">
            {save.error.message}
          </p>
        )}
      </CardContent>
    </Card>
  )
}
