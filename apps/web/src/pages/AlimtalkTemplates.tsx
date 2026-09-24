import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'

import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Dialog, DialogClose, DialogContent, DialogTitle } from '../components/ui/dialog'
import { Field } from '../components/ui/field'
import { Input } from '../components/ui/input'
import { Select } from '../components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from '../components/ui/table'
import { Textarea } from '../components/ui/textarea'
import {
  fetchAlimtalkSettings,
  saveAlimtalkSettings,
  type AlimtalkSettings,
  type AlimtalkTemplate,
} from '../api'

/** 본문의 `#{변수}` 이름을 나온 순서대로, 겹치지 않게. 서버의 검사와 같은 규칙이다. */
function variablesIn(body: string): string[] {
  return [...new Set([...body.matchAll(/#\{([^}]+)\}/g)].map((match) => match[1]))]
}

function TemplateDialog({
  template,
  fields,
  onSave,
  onRemove,
  onClose,
}: {
  template: AlimtalkTemplate
  fields: AlimtalkSettings['fields']
  onSave: (template: AlimtalkTemplate) => void
  onRemove: (() => void) | null
  onClose: () => void
}) {
  const [draft, setDraft] = useState(template)
  const names = variablesIn(draft.body)
  const complete = draft.code.trim() !== '' && draft.body.trim() !== '' && names.every((name) => draft.variables[name])

  function submit(event: FormEvent) {
    event.preventDefault()
    // 본문에서 지운 변수의 매핑은 남기지 않는다
    onSave({ ...draft, variables: Object.fromEntries(names.map((name) => [name, draft.variables[name]])) })
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[90vh] max-w-xl overflow-y-auto">
        <DialogTitle className="mb-4 text-base font-semibold">알림톡 템플릿</DialogTitle>
        <form className="grid gap-3" onSubmit={submit}>
          <Field label="템플릿 코드" htmlFor="alimtalk-code">
            <Input
              id="alimtalk-code"
              value={draft.code}
              onChange={(event) => setDraft({ ...draft, code: event.target.value })}
            />
          </Field>
          <Field label="승인된 템플릿 본문" htmlFor="alimtalk-body">
            <Textarea
              id="alimtalk-body"
              rows={6}
              value={draft.body}
              onChange={(event) => setDraft({ ...draft, body: event.target.value })}
            />
          </Field>
          <p className="text-xs text-muted-fg">
            카카오 검수를 통과한 본문을 그대로 붙여 넣으세요. 글자가 하나라도 다르면 발송이 거절됩니다.
          </p>
          {names.map((name) => (
            <Field key={name} label={`#{${name}}`} htmlFor={`alimtalk-var-${name}`}>
              <Select
                id={`alimtalk-var-${name}`}
                value={draft.variables[name] ?? ''}
                onChange={(event) =>
                  setDraft({ ...draft, variables: { ...draft.variables, [name]: event.target.value } })
                }
              >
                <option value="">넣을 값 선택</option>
                {fields.map((field) => (
                  <option key={field.key} value={field.key}>
                    {field.label}
                  </option>
                ))}
              </Select>
            </Field>
          ))}
          <div className="mt-2 flex justify-between gap-2">
            {onRemove ? (
              <Button type="button" variant="ghost" onClick={onRemove}>
                템플릿 빼기
              </Button>
            ) : (
              <span />
            )}
            <div className="flex gap-2">
              <DialogClose asChild>
                <Button type="button" variant="outline">
                  취소
                </Button>
              </DialogClose>
              <Button type="submit" disabled={!complete}>
                저장
              </Button>
            </div>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}

/** 알림톡 승인 템플릿과 변수 매핑, 문자 대체 설정(FR-37·FR-38). 저장은 목록 전체를 바꾼다. */
export function AlimtalkTemplates() {
  const queryClient = useQueryClient()
  const settings = useQuery({ queryKey: ['alimtalk-templates'], queryFn: () => fetchAlimtalkSettings() })
  const [editing, setEditing] = useState<{ index: number | null; template: AlimtalkTemplate } | null>(null)
  const save = useMutation({
    mutationFn: saveAlimtalkSettings,
    onSuccess: (saved) => {
      setEditing(null)
      queryClient.setQueryData(['alimtalk-templates'], saved)
    },
  })

  const data = settings.data
  if (!data?.alimtalk) return null
  const labels = Object.fromEntries(data.fields.map((field) => [field.key, field.label]))

  function store(templates: AlimtalkTemplate[], fallback = data!.fallback_to_sms) {
    save.mutate({ fallback_to_sms: fallback, alimtalk: templates })
  }

  return (
    <Card className="mt-5">
      <CardHeader>
        <CardTitle>알림톡 템플릿</CardTitle>
        <p className="mt-1 text-xs text-muted-fg">
          카카오 검수를 통과한 템플릿만 보낼 수 있습니다. 템플릿의 #{'{변수}'}마다 채워 넣을 값을 정해 주세요.
        </p>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <label htmlFor="alimtalk-fallback" className="flex items-center gap-2 text-sm">
          <input
            id="alimtalk-fallback"
            type="checkbox"
            className="size-4 accent-brand"
            checked={data.fallback_to_sms}
            onChange={(event) => store(data.alimtalk, event.target.checked)}
          />
          알림톡이 실패하면 문자로 대체 발송
        </label>

        {data.alimtalk.length > 0 && (
          <div className="-mx-5">
            <Table aria-label="알림톡 템플릿">
              <TableHead>
                <TableRow>
                  <TableHeaderCell>코드</TableHeaderCell>
                  <TableHeaderCell>본문</TableHeaderCell>
                  <TableHeaderCell>변수</TableHeaderCell>
                  <TableHeaderCell />
                </TableRow>
              </TableHead>
              <TableBody>
                {data.alimtalk.map((template, index) => (
                  <TableRow key={template.code}>
                    <TableCell className="font-medium whitespace-nowrap">{template.code}</TableCell>
                    <TableCell className="max-w-72 truncate text-muted-fg">{template.body}</TableCell>
                    <TableCell className="text-muted-fg whitespace-nowrap">
                      <ul>
                        {Object.entries(template.variables).map(([name, key]) => (
                          <li key={name}>{`#{${name}} → ${labels[key] ?? key}`}</li>
                        ))}
                      </ul>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button type="button" size="sm" variant="outline" onClick={() => setEditing({ index, template })}>
                        수정
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}

        <div>
          <Button
            type="button"
            variant="outline"
            onClick={() => setEditing({ index: null, template: { code: '', body: '', variables: {} } })}
          >
            템플릿 추가
          </Button>
        </div>
        {save.isError && (
          <p role="alert" className="text-sm text-danger">
            {save.error.message}
          </p>
        )}
      </CardContent>

      {editing && (
        <TemplateDialog
          template={editing.template}
          fields={data.fields}
          onClose={() => setEditing(null)}
          onRemove={
            editing.index === null ? null : () => store(data.alimtalk.filter((_, i) => i !== editing.index))
          }
          onSave={(template) =>
            store(
              editing.index === null
                ? [...data.alimtalk, template]
                : data.alimtalk.map((current, i) => (i === editing.index ? template : current)),
            )
          }
        />
      )}
    </Card>
  )
}
