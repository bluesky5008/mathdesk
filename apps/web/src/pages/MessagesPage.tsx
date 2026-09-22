import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

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

function today(): string {
  return new Date().toISOString().slice(0, 10)
}

export function MessagesPage() {
  const queryClient = useQueryClient()
  const classes = useQuery({ queryKey: ['classes'], queryFn: fetchClasses })
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
      <h2>알림문자 미리보기</h2>

      <div>
        <label htmlFor="message-class">반</label>
        <select
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
        </select>
        <label htmlFor="message-date">날짜</label>
        <input
          id="message-date"
          type="date"
          value={date}
          onChange={(event) => setDate(event.target.value)}
        />
        <label htmlFor="message-student">학생 선택</label>
        <select
          id="message-student"
          value={activeStudentId ?? ''}
          onChange={(event) => setStudentId(Number(event.target.value))}
        >
          {daily.data?.records.map((record) => (
            <option key={record.student_id} value={record.student_id}>
              {record.name}
            </option>
          ))}
        </select>
      </div>

      <div role="tablist">
        <button type="button" role="tab" aria-selected={tab === 'text'} onClick={() => setTab('text')}>
          문자 보기
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'report'}
          onClick={() => setTab('report')}
        >
          리포트 보기
        </button>
      </div>

      {tab === 'text' ? (
        <pre>{body}</pre>
      ) : (
        imageUrl && <img src={imageUrl} alt="리포트 카드" />
      )}

      <fieldset>
        <legend>문자 받을 대상</legend>
        {RECIPIENTS.map(([value, label]) => (
          <label key={value} htmlFor={`recipient-${value}`}>
            <input
              id={`recipient-${value}`}
              type="checkbox"
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
        <span>둘 다 체크하면 학생·학부모 모두에게 전송</span>
      </fieldset>

      <div>
        <button type="button" onClick={() => void copyText(body)} disabled={!body}>
          문자 복사
        </button>
        <button type="button" onClick={() => void copyImage(imageUrl)} disabled={!imageUrl}>
          이미지 복사
        </button>
        <button
          type="button"
          onClick={() => downloadImage(imageUrl, `리포트-${date}.png`)}
          disabled={!imageUrl}
        >
          리포트 이미지 저장
        </button>
        <button
          type="button"
          onClick={() => send.mutate()}
          disabled={recipients.length === 0 || sessionId === null || send.isPending}
        >
          문자 발송
        </button>
      </div>
      {send.isError && <p role="alert">{send.error.message}</p>}
      {send.isSuccess && <p role="status">{`${send.data.results.length}건 처리(${send.data.channel})`}</p>}

      <h3>발송 내역</h3>
      <table>
        <tbody>
          {logs.data?.map((log) => (
            <tr key={log.id}>
              <td>{log.requested_at.slice(0, 16).replace('T', ' ')}</td>
              <td>{log.recipient_phone}</td>
              <td>{log.channel}</td>
              <td>{log.is_test ? '테스트' : log.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
