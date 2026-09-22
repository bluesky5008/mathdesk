import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import { AttendanceButtons } from '../components/AttendanceButtons'
import {
  fetchClasses,
  fetchDaily,
  saveDailyNotes,
  saveDailyRecords,
  saveRecheck,
  setAttendanceConfirmed,
  type DailyRecord,
  type NotesPatch,
  type RecordPatch,
} from '../api'

const GRADES = ['A+', 'A', 'B', 'C', 'D', 'F']
const PERIODS = [1, 2, 3, 4]
const EMPTY_NOTES: NotesPatch = {}

function today(): string {
  return new Date().toISOString().slice(0, 10)
}

function describeRecheck(record: DailyRecord): string {
  if (!record.recheck.prev_grade || !record.recheck.prev_date) {
    return '재검사 대상 아님'
  }
  return `직전 ${record.recheck.prev_grade} · ${record.recheck.prev_date.slice(5).replace('-', '/')}`
}

export function DailyPage() {
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
  const session = daily.data?.session

  // 표 편집과 메모 편집은 서로 다른 저장 단위다. 한쪽 저장이 다른 쪽 미저장 입력을 지우면 안 된다.
  const [drafts, setDrafts] = useState<Record<number, RecordPatch>>({})
  const [notes, setNotes] = useState<NotesPatch>(EMPTY_NOTES)

  useEffect(() => {
    setDrafts({})
    setNotes(EMPTY_NOTES)
  }, [activeClassId, date])

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['daily', activeClassId, date] })

  const saveRecords = useMutation({
    mutationFn: () => saveDailyRecords(session!.id, Object.values(drafts)),
    onSuccess: () => {
      setDrafts({})
      void invalidate()
    },
  })
  const saveNotes = useMutation({
    mutationFn: () => saveDailyNotes(session!.id, notes),
    onSuccess: () => {
      setNotes(EMPTY_NOTES)
      void invalidate()
    },
  })
  const recheck = useMutation({
    mutationFn: (input: { studentId: number; result: string | null }) =>
      saveRecheck(session!.id, input.studentId, input.result),
    onSuccess: () => void invalidate(),
  })
  const confirmation = useMutation({
    mutationFn: (confirmed: boolean) => setAttendanceConfirmed(session!.id, confirmed),
    onSuccess: () => void invalidate(),
  })

  const dirty = Object.keys(drafts).length > 0 || Object.keys(notes).length > 0

  function patch(studentId: number, change: Omit<RecordPatch, 'student_id'>) {
    setDrafts((current) => ({
      ...current,
      [studentId]: { ...current[studentId], student_id: studentId, ...change },
    }))
  }

  function valueOf<K extends keyof RecordPatch>(record: DailyRecord, field: K) {
    const draft = drafts[record.student_id]
    return draft && field in draft ? draft[field] : (record[field as keyof DailyRecord] as never)
  }

  function change(next: { classId?: number; date?: string }) {
    if (dirty && !window.confirm('저장하지 않은 입력이 있습니다. 이동할까요?')) {
      return
    }
    if (next.classId !== undefined) setClassId(next.classId)
    if (next.date !== undefined) setDate(next.date)
  }

  const locked = Boolean(session?.attendance_confirmed_at)

  return (
    <section>
      <h2>일일 수업 &amp; 성적 입력</h2>

      <div>
        <label htmlFor="daily-class">반</label>
        <select
          id="daily-class"
          value={activeClassId ?? ''}
          onChange={(event) => change({ classId: Number(event.target.value) })}
        >
          {classes.data?.map((klass) => (
            <option key={klass.id} value={klass.id}>
              {klass.name}
            </option>
          ))}
        </select>
        <label htmlFor="daily-date">날짜</label>
        <input
          id="daily-date"
          type="date"
          value={date}
          onChange={(event) => change({ date: event.target.value })}
        />
      </div>

      {daily.data && (
        <p>
          등원 현황{' '}
          <strong>{`${daily.data.summary.attending} / ${daily.data.summary.enrolled}명`}</strong> ·
          당일 테스트 평균 <strong>{daily.data.summary.test_average ?? '—'}</strong>
        </p>
      )}

      <div>
        <table>
          <thead>
            <tr>
              <th>학생</th>
              <th>출결 상태</th>
              <th>이전 과제 재검사</th>
              <th>과제피드백</th>
              <th>테스트</th>
            </tr>
          </thead>
          <tbody>
            {daily.data?.records.map((record) => (
              <tr key={record.student_id}>
                <td>{record.name}</td>
                <td>
                  <AttendanceButtons
                    value={String(valueOf(record, 'attendance_status'))}
                    disabled={locked}
                    onChange={(next) => patch(record.student_id, { attendance_status: next })}
                  />
                  <input
                    aria-label={`${record.name} 사유`}
                    value={String(valueOf(record, 'attendance_reason') ?? '')}
                    disabled={locked}
                    onChange={(event) =>
                      patch(record.student_id, { attendance_reason: event.target.value })
                    }
                  />
                </td>
                <td>
                  <span>{describeRecheck(record)}</span>
                  {record.recheck.target &&
                    (
                      [
                        ['pass', '합격'],
                        ['fail', '불합격'],
                      ] as const
                    ).map(([value, label]) => (
                      <button
                        key={value}
                        type="button"
                        aria-pressed={record.recheck.result === value}
                        onClick={() =>
                          recheck.mutate({
                            studentId: record.student_id,
                            result: record.recheck.result === value ? null : value,
                          })
                        }
                      >
                        {label}
                      </button>
                    ))}
                </td>
                <td>
                  {GRADES.map((grade) => (
                    <button
                      key={grade}
                      type="button"
                      aria-pressed={valueOf(record, 'homework_grade') === grade}
                      onClick={() =>
                        patch(record.student_id, {
                          homework_grade:
                            valueOf(record, 'homework_grade') === grade ? null : grade,
                        })
                      }
                    >
                      {grade}
                    </button>
                  ))}
                </td>
                <td>
                  <input
                    aria-label={`${record.name} 점수`}
                    inputMode="numeric"
                    value={String(valueOf(record, 'test_score_num') ?? '')}
                    onChange={(event) =>
                      patch(record.student_id, {
                        test_score_num: event.target.value === '' ? null : Number(event.target.value),
                      })
                    }
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <button type="button" onClick={() => saveRecords.mutate()} disabled={!session}>
          표 저장
        </button>
        <button
          type="button"
          onClick={() => confirmation.mutate(!locked)}
          disabled={!session}
        >
          {locked ? '편집' : '확인'}
        </button>
        {saveRecords.isError && <p role="alert">{saveRecords.error.message}</p>}
      </div>

      <div>
        <h3>오늘 진도 &amp; 코멘트</h3>
        {PERIODS.map((period) => (
          <label key={period} htmlFor={`period-${period}`}>
            {period}교시
            <textarea
              id={`period-${period}`}
              value={
                notes.progress?.find((item) => item.period === period)?.content ??
                session?.progress.find((item) => item.period === period)?.content ??
                ''
              }
              onChange={(event) =>
                setNotes((current) => {
                  const base =
                    current.progress ??
                    PERIODS.map((value) => ({
                      period: value,
                      content:
                        session?.progress.find((item) => item.period === value)?.content ?? null,
                    }))
                  return {
                    ...current,
                    progress: base.map((item) =>
                      item.period === period ? { ...item, content: event.target.value } : item,
                    ),
                  }
                })
              }
            />
          </label>
        ))}
        {(
          [
            ['homework', '오늘의 과제'],
            ['video_url', '수업 영상 링크'],
            ['teacher_note', '강사 첨언'],
          ] as const
        ).map(([field, label]) => (
          <label key={field} htmlFor={`notes-${field}`}>
            {label}
            <textarea
              id={`notes-${field}`}
              value={String(notes[field] ?? session?.[field] ?? '')}
              onChange={(event) => setNotes({ ...notes, [field]: event.target.value })}
            />
          </label>
        ))}
        <button type="button" onClick={() => saveNotes.mutate()} disabled={!session}>
          메모 저장
        </button>
      </div>
    </section>
  )
}
