import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'

import { Button } from '../components/ui/button'
import { Dialog, DialogClose, DialogContent, DialogTitle } from '../components/ui/dialog'
import { Field } from '../components/ui/field'
import { Input } from '../components/ui/input'
import { Textarea } from '../components/ui/textarea'
import { createConsult, fetchConsults, updateConsult, type Consult, type ConsultInput } from '../api'
import { today } from '../lib/date'

type Draft = { consulted_on: string; content: string; follow_up: string }

function toInput(draft: Draft): ConsultInput {
  return { consulted_on: draft.consulted_on, content: draft.content, follow_up: draft.follow_up || null }
}

/** 날짜·내용·후속 조치 입력칸. 새 기록과 수정이 함께 쓴다. */
function ConsultFields({ prefix, draft, onChange }: { prefix: string; draft: Draft; onChange: (draft: Draft) => void }) {
  return (
    <>
      <Field label="상담일" htmlFor={`${prefix}-date`}>
        <Input
          id={`${prefix}-date`}
          type="date"
          className="w-40"
          value={draft.consulted_on}
          onChange={(event) => onChange({ ...draft, consulted_on: event.target.value })}
        />
      </Field>
      <Field label="상담 내용" htmlFor={`${prefix}-content`}>
        <Textarea
          id={`${prefix}-content`}
          value={draft.content}
          onChange={(event) => onChange({ ...draft, content: event.target.value })}
        />
      </Field>
      <Field label="후속 조치" htmlFor={`${prefix}-follow-up`}>
        <Input
          id={`${prefix}-follow-up`}
          value={draft.follow_up}
          onChange={(event) => onChange({ ...draft, follow_up: event.target.value })}
        />
      </Field>
    </>
  )
}

function Entry({ studentId, consult }: { studentId: number; consult: Consult }) {
  const queryClient = useQueryClient()
  const [draft, setDraft] = useState<Draft | null>(null)
  const save = useMutation({
    mutationFn: (input: ConsultInput) => updateConsult(studentId, consult.id, input),
    onSuccess: () => {
      setDraft(null)
      void queryClient.invalidateQueries({ queryKey: ['consults', studentId] })
    },
  })

  function submit(event: FormEvent) {
    event.preventDefault()
    if (draft) save.mutate(toInput(draft))
  }

  return (
    <article aria-label={`${consult.consulted_on} 상담`} className="rounded-md border px-4 py-3">
      {draft ? (
        <form className="grid gap-3" onSubmit={submit}>
          <ConsultFields prefix={`consult-${consult.id}`} draft={draft} onChange={setDraft} />
          {save.isError && (
            <p role="alert" className="text-sm text-danger">
              {save.error.message}
            </p>
          )}
          <div className="flex justify-end gap-2">
            <Button type="button" size="sm" variant="outline" onClick={() => setDraft(null)}>
              취소
            </Button>
            <Button type="submit" size="sm" disabled={!draft.content.trim() || save.isPending}>
              저장
            </Button>
          </div>
        </form>
      ) : (
        <>
          <div className="flex items-start justify-between gap-3">
            <div className="text-xs text-muted-fg">
              <span className="font-medium text-fg tabular-nums">{consult.consulted_on}</span>
              {consult.author && <span className="ml-2">{consult.author.name}</span>}
            </div>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() =>
                setDraft({
                  consulted_on: consult.consulted_on,
                  content: consult.content,
                  follow_up: consult.follow_up ?? '',
                })
              }
            >
              수정
            </Button>
          </div>
          <p className="mt-1 text-sm whitespace-pre-wrap">{consult.content}</p>
          {consult.follow_up && <p className="mt-1 text-sm text-muted-fg">후속 조치: {consult.follow_up}</p>}
        </>
      )}
    </article>
  )
}

/** 학생 한 명의 상담일지(FR-39). 학생 목록의 [상담]에서 연다. */
export function ConsultDialog({
  student,
  onClose,
}: {
  student: { id: number; name: string }
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const consults = useQuery({ queryKey: ['consults', student.id], queryFn: () => fetchConsults(student.id) })
  const empty: Draft = { consulted_on: today(), content: '', follow_up: '' }
  const [draft, setDraft] = useState<Draft>(empty)
  const create = useMutation({
    mutationFn: (input: ConsultInput) => createConsult(student.id, input),
    onSuccess: () => {
      setDraft(empty)
      void queryClient.invalidateQueries({ queryKey: ['consults', student.id] })
    },
  })

  function submit(event: FormEvent) {
    event.preventDefault()
    create.mutate(toInput(draft))
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[90vh] max-w-xl overflow-y-auto">
        <DialogTitle className="mb-4 text-base font-semibold">{student.name} 상담일지</DialogTitle>
        <form className="mb-5 grid gap-3" onSubmit={submit}>
          <ConsultFields prefix="consult-new" draft={draft} onChange={setDraft} />
          {create.isError && (
            <p role="alert" className="text-sm text-danger">
              {create.error.message}
            </p>
          )}
          <div className="flex justify-end">
            <Button type="submit" disabled={!draft.content.trim() || !draft.consulted_on || create.isPending}>
              상담 기록
            </Button>
          </div>
        </form>

        <div className="grid gap-3">
          {consults.data?.length === 0 && <p className="text-sm text-muted-fg">아직 상담 기록이 없습니다.</p>}
          {consults.data?.map((consult) => <Entry key={consult.id} studentId={student.id} consult={consult} />)}
        </div>
        <div className="mt-5 flex justify-end">
          <DialogClose asChild>
            <Button type="button" variant="outline">
              닫기
            </Button>
          </DialogClose>
        </div>
      </DialogContent>
    </Dialog>
  )
}
