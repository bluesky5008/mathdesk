import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import {
  fetchClasses,
  fetchDaily,
  fetchDashboard,
  saveDailyRecords,
  setAttendanceConfirmed,
  type RecordPatch,
} from '../api'
import { AttendanceButtons } from '../components/AttendanceButtons'

function today(): string {
  return new Date().toISOString().slice(0, 10)
}

function signed(value: number): string {
  return `${value >= 0 ? '+' : ''}${value}`
}

export function DashboardPage() {
  const queryClient = useQueryClient()
  const classes = useQuery({ queryKey: ['classes'], queryFn: fetchClasses })
  const [classId, setClassId] = useState<number | null>(null)
  const [date, setDate] = useState(today())
  const activeClassId = classId ?? classes.data?.[0]?.id ?? null

  const dashboard = useQuery({
    queryKey: ['dashboard', activeClassId, date],
    queryFn: () => fetchDashboard(activeClassId!, date),
    enabled: activeClassId !== null,
  })
  const daily = useQuery({
    queryKey: ['daily', activeClassId, date],
    queryFn: () => fetchDaily(activeClassId!, date),
    enabled: activeClassId !== null,
  })
  const session = daily.data?.session
  const locked = Boolean(session?.attendance_confirmed_at)

  const [drafts, setDrafts] = useState<Record<number, RecordPatch>>({})

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['daily', activeClassId, date] })
    void queryClient.invalidateQueries({ queryKey: ['dashboard', activeClassId, date] })
  }
  const saveRecords = useMutation({
    mutationFn: () => saveDailyRecords(session!.id, Object.values(drafts)),
    onSuccess: () => {
      setDrafts({})
      invalidate()
    },
  })
  const confirmation = useMutation({
    mutationFn: (confirmed: boolean) => setAttendanceConfirmed(session!.id, confirmed),
    onSuccess: invalidate,
  })

  const kpi = dashboard.data

  return (
    <section>
      <h2>종합 대시보드</h2>

      <div>
        <label htmlFor="dashboard-class">반</label>
        <select
          id="dashboard-class"
          value={activeClassId ?? ''}
          onChange={(event) => setClassId(Number(event.target.value))}
        >
          {classes.data?.map((klass) => (
            <option key={klass.id} value={klass.id}>
              {klass.name}
            </option>
          ))}
        </select>
        <label htmlFor="dashboard-date">날짜</label>
        <input
          id="dashboard-date"
          type="date"
          value={date}
          onChange={(event) => setDate(event.target.value)}
        />
      </div>

      {kpi && (
        <ul>
          <li>
            <h3>총 재원생 &amp; 반 현황</h3>
            <strong>{`${kpi.campus.enrolled_students}명`}</strong>
            <span>{`활성 ${kpi.campus.active_classes}개 반`}</span>
          </li>
          <li>
            <h3>선택한 반 등원 현황</h3>
            <strong>
              {kpi.attendance
                ? `${kpi.attendance.attending} / ${kpi.attendance.enrolled}명`
                : '—'}
            </strong>
            <span>출석 + 지각 + 조퇴 · 출결 체크에 따라 반영</span>
          </li>
          <li>
            <h3>금주 과제 완수율</h3>
            <strong>
              {kpi.homework.completion_rate === null ? '—' : `${kpi.homework.completion_rate}%`}
            </strong>
            {kpi.homework.delta_points !== null && (
              <span>{`전주 대비 ${signed(kpi.homework.delta_points)}%p`}</span>
            )}
            <span>{`미제출 ${kpi.homework.missing}건 · 재검사 대상 ${kpi.homework.recheck_targets}명`}</span>
          </li>
          <li>
            <h3>주간테스트 종합 평균</h3>
            <strong>{kpi.test.average === null ? '—' : `${kpi.test.average}점`}</strong>
            {kpi.test.average !== null && (
              <span>
                {`N=${kpi.test.count} · MAX ${kpi.test.max} (${kpi.test.max_count}명) · MIN ${kpi.test.min}`}
              </span>
            )}
          </li>
        </ul>
      )}

      <div>
        <h3>반별 출결 체크</h3>
        <p>선택한 출결을 다시 누르면 해제됩니다. 마지막에 확인을 눌러 출결을 확정해 주세요.</p>
        <table>
          <tbody>
            {daily.data?.records.map((record) => {
              const draft = drafts[record.student_id]
              const status = draft?.attendance_status ?? record.attendance_status
              return (
                <tr key={record.student_id}>
                  <td>{record.name}</td>
                  <td>
                    <AttendanceButtons
                      value={status}
                      disabled={locked}
                      onChange={(next) =>
                        setDrafts((current) => ({
                          ...current,
                          [record.student_id]: {
                            ...current[record.student_id],
                            student_id: record.student_id,
                            attendance_status: next,
                          },
                        }))
                      }
                    />
                    <input
                      aria-label={`${record.name} 사유`}
                      value={String(
                        draft?.attendance_reason ?? record.attendance_reason ?? '',
                      )}
                      disabled={locked}
                      onChange={(event) =>
                        setDrafts((current) => ({
                          ...current,
                          [record.student_id]: {
                            ...current[record.student_id],
                            student_id: record.student_id,
                            attendance_reason: event.target.value,
                          },
                        }))
                      }
                    />
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
        <button type="button" onClick={() => saveRecords.mutate()} disabled={!session || locked}>
          저장
        </button>
        <button
          type="button"
          onClick={() => confirmation.mutate(!locked)}
          disabled={!session}
        >
          {locked ? '편집' : '확인'}
        </button>
      </div>

      <div>
        <h3>지난 수업 진도 &amp; 과제</h3>
        {kpi?.last_session ? (
          <>
            <p>{kpi.last_session.session_date}</p>
            <ul>
              {kpi.last_session.progress.map((item) => (
                <li key={item.period}>{`[${item.period}교시] ${item.content ?? ''}`}</li>
              ))}
            </ul>
            <p>{kpi.last_session.homework}</p>
          </>
        ) : (
          <p>지난 수업 기록이 없습니다.</p>
        )}
      </div>
    </section>
  )
}
