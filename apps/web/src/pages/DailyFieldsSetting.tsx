import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'

import { Button } from '../components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Input } from '../components/ui/input'
import { DEFAULT_DAILY_FIELDS, fetchDailyFields, saveDailyFields, type DailyFieldsPayload } from '../api'

const LIMIT = 5

// FR-50 — 학원마다 다른 일일 기록 항목. 재검사 표시 여부와 학생별 한 줄 추가 항목(원장 전용)
export function DailyFieldsSetting() {
  const queryClient = useQueryClient()
  const stored = useQuery({ queryKey: ['daily-fields'], queryFn: fetchDailyFields })
  const [edited, setEdited] = useState<DailyFieldsPayload | null>(null)
  const [label, setLabel] = useState('')
  const form: DailyFieldsPayload = edited ?? stored.data ?? DEFAULT_DAILY_FIELDS

  const save = useMutation({
    mutationFn: () => saveDailyFields(form),
    onSuccess: () => {
      setEdited(null)
      void queryClient.invalidateQueries({ queryKey: ['daily-fields'] })
      // 일일 입력·학생별 정보·대시보드가 이 설정으로 열을 그린다
      for (const key of ['daily', 'daily-history', 'dashboard']) {
        void queryClient.invalidateQueries({ queryKey: [key] })
      }
    },
  })

  function submit(event: FormEvent) {
    event.preventDefault()
    save.mutate()
  }

  function add() {
    if (!label.trim()) return
    setEdited({ ...form, extra: [...form.extra, { label: label.trim() }] })
    setLabel('')
  }

  function remove(index: number) {
    const item = form.extra[index]
    // 저장된 항목은 값이 딸려 있다. 같은 이름으로 다시 만들어도 옛 값은 돌아오지 않는다
    if (
      item.id &&
      !window.confirm(
        `"${item.label}" 항목을 삭제할까요? 지금까지 입력한 값이 모든 화면에서 사라지고, 같은 이름으로 다시 만들어도 돌아오지 않습니다.`,
      )
    ) {
      return
    }
    setEdited({ ...form, extra: form.extra.filter((_, at) => at !== index) })
  }

  return (
    <Card className="mt-5 max-w-2xl">
      <CardHeader>
        <CardTitle>일일 기록 항목</CardTitle>
        <CardDescription>
          일일 입력 표, 학생별 정보와 그 이미지, 학생·학부모 화면, 알림문자에 함께 반영됩니다. 추가 항목은
          학생마다 그날 한 줄(100자)로 적으며 학부모에게 보입니다.
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-4">
        <form className="flex flex-col gap-4" onSubmit={submit}>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              className="size-4"
              checked={form.recheck}
              onChange={(event) => setEdited({ ...form, recheck: event.target.checked })}
            />
            이전 과제 재검사 보이기
          </label>
          <p className="-mt-2 text-xs text-muted-fg">
            꺼도 저장된 합격·불합격은 지워지지 않습니다. 다시 켜면 그대로 보입니다.
          </p>

          <ul className="flex flex-col gap-2">
            {form.extra.map((item, index) => (
              <li key={item.id ?? `new-${index}`} className="flex items-center gap-2">
                <Input
                  aria-label={`항목 ${index + 1} 이름`}
                  maxLength={20}
                  className="w-48"
                  value={item.label}
                  onChange={(event) =>
                    setEdited({
                      ...form,
                      extra: form.extra.map((other, at) =>
                        at === index ? { ...other, label: event.target.value } : other,
                      ),
                    })
                  }
                />
                <Button type="button" variant="ghost" aria-label={`${item.label} 삭제`} onClick={() => remove(index)}>
                  삭제
                </Button>
              </li>
            ))}
          </ul>

          <div className="flex items-center gap-2">
            <Input
              aria-label="새 항목 이름"
              placeholder="예: 수업태도"
              maxLength={20}
              className="w-48"
              value={label}
              onChange={(event) => setLabel(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  event.preventDefault()
                  add()
                }
              }}
            />
            <Button type="button" variant="outline" disabled={form.extra.length >= LIMIT} onClick={add}>
              항목 추가
            </Button>
            <span className="text-xs text-muted-fg">{`${form.extra.length} / ${LIMIT}개`}</span>
          </div>

          <div className="flex items-center gap-3">
            <Button type="submit" disabled={save.isPending}>
              일일 기록 항목 저장
            </Button>
            {save.isSuccess && edited === null && (
              <span role="status" className="text-sm text-success">
                저장했습니다
              </span>
            )}
          </div>
          {save.isError && (
            <p role="alert" className="text-sm text-danger">
              {save.error.message}
            </p>
          )}
        </form>
      </CardContent>
    </Card>
  )
}
