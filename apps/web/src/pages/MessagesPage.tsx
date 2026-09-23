import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { PageHeader } from '../components/PageHeader'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
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
import { today } from '../lib/date'
import { cn } from '../lib/utils'
import {
  fetchClasses,
  fetchDaily,
  fetchMessageLogs,
  fetchMessagePreview,
  reportImageUrl,
  sendMessage,
} from '../api'
import { copyImage, copyText, downloadImage } from '../clipboard'

const RECIPIENTS = [
  ['student', '학생'],
  ['guardian', '학부모'],
] as const

const TABS = [
  ['text', '문자 보기'],
  ['report', '리포트 보기'],
] as const

export function MessagesPage() {
  const queryClient = useQueryClient()
  const classes = useQuery({ queryKey: ['classes'], queryFn: () => fetchClasses() })
  const [classId, setClassId] = useState<number | null>(null)
  const [date, setDate] = useState(today())
  const activeClassId = classId ?? classes.data?.[0]?.id ?? null

  const daily = useQuery({
    queryKey: ['daily', activeClassId, date],
    queryFn: () => fetchDaily(activeClassId!, date),
    enabled: activeClassId !== null,
  })
  const [studentId, setStudentId] = useState<number | null>(null)
  const activeStudentId = studentId ?? daily.data?.records[0]?.student_id ?? null
  const sessionId = daily.data?.session.id ?? null

  const preview = useQuery({
    queryKey: ['preview', sessionId, activeStudentId],
    queryFn: () => fetchMessagePreview(sessionId!, activeStudentId!),
    enabled: sessionId !== null && activeStudentId !== null,
  })
  const logs = useQuery({ queryKey: ['message-logs'], queryFn: fetchMessageLogs })

  const [tab, setTab] = useState<'text' | 'report'>('text')
  const [recipients, setRecipients] = useState<string[]>([])

  const send = useMutation({
    mutationFn: () => sendMessage(sessionId!, activeStudentId!, recipients),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['message-logs'] }),
  })

  const imageUrl =
    sessionId !== null && activeStudentId !== null ? reportImageUrl(sessionId, activeStudentId) : ''
  const body = preview.data?.body ?? ''

  return (
    <section>
      <PageHeader title="알림문자 미리보기">
        <Field label="반" htmlFor="message-class">
          <Select
            id="message-class"
            value={activeClassId ?? ''}
            onChange={(event) => {
              setClassId(Number(event.target.value))
              setStudentId(null)
            }}
          >
            {classes.data?.map((klass) => (
              <option key={klass.id} value={klass.id}>
                {klass.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="날짜" htmlFor="message-date">
          <Input
            id="message-date"
            type="date"
            className="w-40"
            value={date}
            onChange={(event) => setDate(event.target.value)}
          />
        </Field>
        <Field label="학생 선택" htmlFor="message-student">
          <Select
            id="message-student"
            value={activeStudentId ?? ''}
            onChange={(event) => setStudentId(Number(event.target.value))}
          >
            {daily.data?.records.map((record) => (
              <option key={record.student_id} value={record.student_id}>
                {record.name}
              </option>
            ))}
          </Select>
        </Field>
      </PageHeader>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_320px] xl:items-start">
        <Card>
          <CardContent className="p-0">
            <div role="tablist" className="flex gap-1 border-b px-3 pt-3">
              {TABS.map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  role="tab"
                  aria-selected={tab === value}
                  onClick={() => setTab(value)}
                  className={cn(
                    'rounded-t-md px-3 py-2 text-sm transition-colors',
                    'outline-none focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring',
                    tab === value
                      ? 'border-b-2 border-brand font-medium text-fg'
                      : 'text-muted-fg hover:text-fg',
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
            <div className="p-5">
              {tab === 'text' ? (
                <pre className="font-sans text-sm leading-normal whitespace-pre-wrap">{body}</pre>
              ) : (
                imageUrl && (
                  <img
                    src={imageUrl}
                    alt="리포트 카드"
                    className="max-w-full rounded-md border shadow-sm"
                  />
                )
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>발송</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4 pt-4">
            <fieldset className="flex flex-col gap-2">
              <legend className="mb-2 text-xs font-medium text-muted-fg">문자 받을 대상</legend>
              {RECIPIENTS.map(([value, label]) => (
                <label
                  key={value}
                  htmlFor={`recipient-${value}`}
                  className="flex items-center gap-2 text-sm"
                >
                  <input
                    id={`recipient-${value}`}
                    type="checkbox"
                    className="size-4 accent-brand"
                    checked={recipients.includes(value)}
                    onChange={(event) =>
                      setRecipients((current) =>
                        event.target.checked
                          ? [...current, value]
                          : current.filter((item) => item !== value),
                      )
                    }
                  />
                  {label}
                </label>
              ))}
              <span className="text-xs text-muted-fg">
                둘 다 체크하면 학생·학부모 모두에게 전송
              </span>
            </fieldset>

            <div className="flex flex-col gap-2 border-t pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={() => void copyText(body)}
                disabled={!body}
              >
                문자 복사
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => void copyImage(imageUrl)}
                disabled={!imageUrl}
              >
                이미지 복사
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => downloadImage(imageUrl, `리포트-${date}.png`)}
                disabled={!imageUrl}
              >
                리포트 이미지 저장
              </Button>
              <Button
                type="button"
                size="lg"
                onClick={() => send.mutate()}
                disabled={recipients.length === 0 || sessionId === null || send.isPending}
              >
                문자 발송
              </Button>
            </div>

            {send.isError && (
              <p role="alert" className="text-sm text-danger">
                {send.error.message}
              </p>
            )}
            {send.isSuccess && (
              <p role="status" className="text-sm text-success">
                {`${send.data.results.length}건 처리(${send.data.channel})`}
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="mt-5">
        <CardHeader>
          <CardTitle>발송 내역</CardTitle>
        </CardHeader>
        <CardContent className="px-0 pt-4 pb-0">
          <Table>
            <TableHead>
              <TableRow>
                <TableHeaderCell>요청 시각</TableHeaderCell>
                <TableHeaderCell>수신 번호</TableHeaderCell>
                <TableHeaderCell>채널</TableHeaderCell>
                <TableHeaderCell>상태</TableHeaderCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {logs.data?.map((log) => (
                <TableRow key={log.id}>
                  <TableCell className="tabular-nums">
                    {log.requested_at.slice(0, 16).replace('T', ' ')}
                  </TableCell>
                  <TableCell className="tabular-nums">{log.recipient_phone}</TableCell>
                  <TableCell className="text-muted-fg">{log.channel}</TableCell>
                  <TableCell>{log.is_test ? '테스트' : log.status}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </section>
  )
}
