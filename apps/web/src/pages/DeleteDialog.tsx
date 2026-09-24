import { useMutation, useQuery } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'

import { Button } from '../components/ui/button'
import { Dialog, DialogClose, DialogContent, DialogTitle } from '../components/ui/dialog'
import { Field } from '../components/ui/field'
import { Input } from '../components/ui/input'
import type { DeletionPreview } from '../api'

/**
 * 되돌릴 수 없는 삭제의 마지막 확인(DCR-006). 함께 지워질 건수를 보여 주고
 * 이름을 그대로 입력해야 삭제한다. 서버도 같은 이름을 다시 확인한다.
 */
export function DeleteDialog({
  title,
  name,
  labels,
  preview,
  remove,
  onDone,
  onClose,
}: {
  title: string
  name: string
  labels: Record<string, string>
  preview: () => Promise<DeletionPreview>
  remove: (confirmName: string) => Promise<void>
  onDone: () => void
  onClose: () => void
}) {
  const counts = useQuery({ queryKey: ['deletion-preview', title], queryFn: () => preview() })
  const [typed, setTyped] = useState('')
  const destroy = useMutation({ mutationFn: () => remove(typed), onSuccess: onDone })
  const total = Object.values(counts.data?.counts ?? {}).reduce((sum, n) => sum + n, 0)

  function submit(event: FormEvent) {
    event.preventDefault()
    if (typed === name) destroy.mutate()
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogTitle className="mb-4 text-base font-semibold">{title}</DialogTitle>
        {counts.data && !counts.data.deletable ? (
          <p role="alert" className="text-sm text-danger">
            {counts.data.reason}
          </p>
        ) : (
          <form className="grid gap-4" onSubmit={submit}>
            <div className="text-sm">
              <p className="mb-2">다음이 함께 삭제됩니다.</p>
              <ul className="list-disc pl-5 text-muted-fg">
                {Object.entries(counts.data?.counts ?? {})
                  .filter(([, n]) => n > 0)
                  .map(([key, n]) => (
                    <li key={key}>{`${labels[key] ?? key} ${n}건`}</li>
                  ))}
              </ul>
              {total > 0 && (
                <p className="mt-2 text-muted-fg">반 평균·문항 정답률·성적 통계가 남은 기록으로 다시 계산됩니다.</p>
              )}
              <p className="mt-2 font-medium text-danger">되돌릴 수 없습니다. 백업에서 복원해야만 되살릴 수 있습니다.</p>
            </div>
            <Field label="확인용 이름" htmlFor="delete-confirm-name">
              <Input
                id="delete-confirm-name"
                placeholder={name}
                value={typed}
                onChange={(event) => setTyped(event.target.value)}
              />
            </Field>
            {destroy.isError && (
              <p role="alert" className="text-sm text-danger">
                {destroy.error.message}
              </p>
            )}
            <div className="flex justify-end gap-2">
              <DialogClose asChild>
                <Button type="button" variant="outline">
                  취소
                </Button>
              </DialogClose>
              <Button type="submit" variant="danger" disabled={typed !== name || !counts.data || destroy.isPending}>
                영구 삭제
              </Button>
            </div>
          </form>
        )}
      </DialogContent>
    </Dialog>
  )
}
