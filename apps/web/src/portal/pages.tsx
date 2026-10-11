import { useQuery } from '@tanstack/react-query'
import { Suspense, lazy, useState, type ReactNode } from 'react'

import {
  fetchPortalCalendar,
  fetchPortalConsults,
  fetchPortalExam,
  fetchPortalExams,
  fetchPortalMessages,
  fetchPortalSessions,
  fetchPortalSessionsOn,
  fetchPortalSummary,
  fetchPortalTestTrend,
  type PortalSession,
} from '../api'
import { ATTENDANCE } from '../components/AttendanceButtons'
import { Button } from '../components/ui/button'
import { Card, CardContent } from '../components/ui/card'
import { Field } from '../components/ui/field'
import { MonthCalendar, WEEKDAYS, weekdayOf } from '../components/ui/month-calendar'
import { Select } from '../components/ui/select'
import { Stat } from '../components/ui/stat'
import { Table, TableBody, TableCell, TableHead, TableHeaderCell, TableRow } from '../components/ui/table'
import { TONE } from '../components/ui/toggle'
import { today } from '../lib/date'
import { usePortalStudent } from './PortalApp'

// 그래프 라이브러리는 추이 탭을 열 때만 받는다(통계 화면과 같은 이유)
const TrendChart = lazy(() => import('../components/TrendChart').then((m) => ({ default: m.TrendChart })))

const RECHECK_RESULT: Record<string, string> = { pass: '합격', fail: '불합격' }

function shortDate(date: string): string {
  return `${Number(date.slice(5, 7))}/${Number(date.slice(8, 10))}(${WEEKDAYS[weekdayOf(date)]})`
}

function hhmm(time: string): string {
  return time.slice(0, 5)
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <h4 className="text-xs font-medium text-muted-fg">{title}</h4>
      <div className="text-sm break-keep whitespace-pre-wrap">{children}</div>
    </div>
  )
}

function Loading({ query, children }: { query: { isPending: boolean; isError: boolean; error: Error | null }; children: ReactNode }) {
  if (query.isPending) return <p className="text-sm text-muted-fg">불러오는 중</p>
  if (query.isError) return <p role="alert" className="text-sm text-danger">{query.error?.message}</p>
  return <>{children}</>
}

function Empty({ children }: { children: ReactNode }) {
  return <p className="py-6 text-center text-sm text-muted-fg">{children}</p>
}

/** 수업일 기록 카드 — 문자 본문(FR-18 상세)과 같은 구획, 같은 순서. 값이 없는 구획은 뺀다 */
export function SessionCard({ row }: { row: PortalSession }) {
  const title = `${shortDate(row.date)} ${row.class_name}`
  const progress = row.progress.filter((item) => item.content)
  const attendance = ATTENDANCE.find(([status]) => status === row.attendance)
  return (
    <Card>
      <CardContent className="flex flex-col gap-3 p-4">
        <h3 className="text-base font-semibold" id={`session-${row.date}-${row.class_name}`}>
          {title}
        </h3>
        <article aria-label={title} className="flex flex-col gap-3">
          {progress.length > 0 && (
            <Section title="수업진도">
              {progress.map((item) => (
                <div key={item.period}>{`[${item.period}교시] ${item.content}`}</div>
              ))}
            </Section>
          )}
          {row.test_name && <Section title="오늘의 테스트">{row.test_name}</Section>}
          {row.homework && <Section title="오늘의 과제">{row.homework}</Section>}
          {row.video_url && (
            <Section title="수업 영상 링크">
              <a href={row.video_url} target="_blank" rel="noreferrer" className="break-all text-brand underline underline-offset-2">
                {row.video_url}
              </a>
            </Section>
          )}
          {row.teacher_note && <Section title="선생님 코멘트">{row.teacher_note}</Section>}
          <Section title="출결">
            {attendance ? (
              <span className="flex items-center gap-2">
                <span className={`inline-flex h-6 items-center rounded-md px-2 text-xs font-medium ${TONE[attendance[2]]}`}>
                  {attendance[1]}
                </span>
                {row.attendance_reason && <span className="text-xs text-muted-fg">{row.attendance_reason}</span>}
              </span>
            ) : (
              <span className="text-muted-fg">미확인</span>
            )}
          </Section>
          {row.homework_grade && (
            <Section title="과제피드백">
              <span className="font-medium">{row.homework_grade}</span>
              {row.grade_comment && <div className="text-muted-fg">{row.grade_comment}</div>}
            </Section>
          )}
          {row.recheck && (
            <Section title="이전 과제 재검사">
              {`직전 ${row.recheck.prev_grade} (${shortDate(row.recheck.prev_date).slice(0, -3)}) · ${
                row.recheck.result ? RECHECK_RESULT[row.recheck.result] : '미입력'
              }`}
            </Section>
          )}
          {row.test_score !== null && (
            <Section title="테스트 점수">
              <span className="font-medium tabular-nums">{row.test_score}점</span>
              {row.class_average !== null && <div className="text-muted-fg">반평균 {row.class_average}점</div>}
            </Section>
          )}
          {row.comment && <Section title="개별 코멘트">{row.comment}</Section>}
        </article>
      </CardContent>
    </Card>
  )
}

export function HomePage() {
  const student = usePortalStudent()
  const summary = useQuery({ queryKey: ['portal-summary', student.id], queryFn: () => fetchPortalSummary(student.id) })
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-xl font-semibold">{student.name}</h2>
        <p className="text-sm text-muted-fg">
          {[student.grade, ...student.classes.map((k) => (k.teacher_name ? `${k.name} · ${k.teacher_name} 선생님` : k.name))]
            .filter(Boolean)
            .join(' / ') || '배정된 반이 없습니다'}
        </p>
      </div>
      <Loading query={summary}>
        {summary.data && (
          <>
            <div className="grid grid-cols-2 gap-3">
              <Stat title="출석 (최근 30일)" value={`${summary.data.attendance.last_30_days.present} / ${summary.data.attendance.last_30_days.total}회`} />
              <Stat title="출석 (전체)" value={`${summary.data.attendance.all_time.present} / ${summary.data.attendance.all_time.total}회`} />
            </div>
            {summary.data.timetable.length > 0 && (
              <Card>
                <CardContent className="p-4">
                  <h3 className="mb-2 text-xs font-medium text-muted-fg">수업 시간</h3>
                  <ul className="flex flex-col gap-1 text-sm">
                    {summary.data.timetable.map((slot) => (
                      <li key={`${slot.class_name}-${slot.weekday}-${slot.start_time}`} className="flex justify-between gap-3">
                        <span>{slot.class_name}</span>
                        <span className="tabular-nums">{`${WEEKDAYS[slot.weekday]} ${hhmm(slot.start_time)}~${hhmm(slot.end_time)}`}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            )}
            {summary.data.latest_tests.length > 0 && (
              <Card>
                <CardContent className="p-4">
                  <h3 className="mb-2 text-xs font-medium text-muted-fg">최근 테스트</h3>
                  <ul className="flex flex-col gap-1 text-sm">
                    {summary.data.latest_tests.map((round) => (
                      <li key={`${round.date}-${round.name}`} className="flex justify-between gap-3">
                        <span className="break-keep">{`${shortDate(round.date)} ${round.name}`}</span>
                        <span className="tabular-nums whitespace-nowrap">
                          {round.score ?? '—'}점{round.class_average !== null && ` / 반평균 ${round.class_average}`}
                        </span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            )}
            {summary.data.latest_session ? (
              <>
                <h3 className="text-xs font-medium text-muted-fg">최근 수업</h3>
                <SessionCard row={summary.data.latest_session} />
              </>
            ) : (
              <Empty>아직 수업 기록이 없습니다.</Empty>
            )}
          </>
        )}
      </Loading>
    </div>
  )
}

/** [기록] 탭(FR-49 상세 기록 탭, DCR-025): 달력 → 선택한 날의 기록 → 전체 기록 한 줄 표 */
export function RecordsPage() {
  const student = usePortalStudent()
  const [picked, setPicked] = useState<string | null>(null)
  const [pickedMonth, setPickedMonth] = useState<string | null>(null)
  const [limit, setLimit] = useState(20)
  // 최초 선택은 가장 최근 기록일
  const latest = useQuery({
    queryKey: ['portal-sessions', student.id, 1],
    queryFn: () => fetchPortalSessions(student.id, undefined, 1),
  })
  const selected = picked ?? latest.data?.[0]?.date ?? (latest.isSuccess ? today() : null)
  const month = pickedMonth ?? selected?.slice(0, 7) ?? null
  const calendar = useQuery({
    queryKey: ['portal-calendar', student.id, month],
    queryFn: () => fetchPortalCalendar(student.id, month!),
    enabled: month !== null,
  })
  const day = useQuery({
    queryKey: ['portal-sessions-on', student.id, selected],
    queryFn: () => fetchPortalSessionsOn(student.id, selected!),
    enabled: selected !== null,
  })
  const all = useQuery({
    queryKey: ['portal-sessions', student.id, limit],
    queryFn: () => fetchPortalSessions(student.id, undefined, limit),
  })
  const recorded = new Set(calendar.data?.recorded_dates ?? [])
  const rows = all.data ?? []

  function pick(date: string) {
    setPicked(date)
    setPickedMonth(date.slice(0, 7))
  }

  return (
    <div className="flex flex-col gap-3">
      <h2 className="text-lg font-semibold">{student.name} 수업 기록</h2>
      <Card>
        <CardContent className="flex justify-center p-3">
          {month && (
            <MonthCalendar
              month={month}
              selected={selected}
              onSelect={pick}
              onMonthChange={setPickedMonth}
              emphasized={(date) => recorded.has(date)}
              dotted={(date) => recorded.has(date)}
            />
          )}
        </CardContent>
      </Card>
      {selected && (
        <Loading query={day}>
          {(day.data ?? []).length === 0 && <Empty>이 날은 기록이 없습니다.</Empty>}
          {(day.data ?? []).map((row) => (
            <SessionCard key={`${row.date}-${row.class_name}`} row={row} />
          ))}
        </Loading>
      )}
      {latest.isSuccess && latest.data.length === 0 && <Empty>아직 수업 기록이 없습니다.</Empty>}

      <Card>
        <CardContent className="p-0">
          <h3 className="px-4 pt-3 pb-1 text-xs font-medium text-muted-fg">전체 기록</h3>
          <Table aria-label="전체 기록">
            <TableHead>
              <TableRow>
                <TableHeaderCell>날짜</TableHeaderCell>
                <TableHeaderCell>출결</TableHeaderCell>
                <TableHeaderCell>과제</TableHeaderCell>
                <TableHeaderCell>테스트</TableHeaderCell>
                <TableHeaderCell>코멘트</TableHeaderCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((row) => {
                const attendance = ATTENDANCE.find(([status]) => status === row.attendance)
                return (
                  <TableRow key={`${row.date}-${row.class_name}`}>
                    <TableCell className="whitespace-nowrap">
                      <button
                        type="button"
                        className="font-medium text-brand underline-offset-2 hover:underline"
                        onClick={() => pick(row.date)}
                      >
                        {shortDate(row.date)}
                      </button>
                      <div className="text-xs text-muted-fg">{row.class_name}</div>
                    </TableCell>
                    <TableCell className="whitespace-nowrap">{attendance ? attendance[1] : '미확인'}</TableCell>
                    <TableCell className="tabular-nums">{row.homework_grade ?? '—'}</TableCell>
                    <TableCell className="tabular-nums whitespace-nowrap">
                      {row.test_score === null ? '—' : `${row.test_score} / ${row.class_average ?? '—'}`}
                    </TableCell>
                    <TableCell className="max-w-40 truncate text-xs" title={row.comment ?? undefined}>
                      {row.comment}
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
          {all.isSuccess && rows.length === 0 && <Empty>아직 수업 기록이 없습니다.</Empty>}
          {rows.length === limit && limit < 50 && (
            <div className="p-3">
              <Button type="button" variant="outline" className="w-full" onClick={() => setLimit(Math.min(50, limit + 20))}>
                더 보기
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export function TestsPage() {
  const student = usePortalStudent()
  const [count, setCount] = useState<10 | 20>(10)
  const trend = useQuery({ queryKey: ['portal-trend', student.id, count], queryFn: () => fetchPortalTestTrend(student.id, count) })
  const rounds = trend.data?.rounds ?? []
  // 전체 회차가 10 이하이면 10회로 고정한다(FR-24, DCR-018과 같은 규칙)
  const fixedAtTen = (trend.data?.total ?? 0) <= 10
  const slots = fixedAtTen ? 10 : count
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-end justify-between gap-3">
        <h2 className="text-lg font-semibold">{student.name} 테스트 추이</h2>
        <Field label="회차" htmlFor="portal-rounds">
          <Select
            id="portal-rounds"
            value={slots}
            disabled={fixedAtTen}
            onChange={(event) => setCount(Number(event.target.value) as 10 | 20)}
          >
            <option value={10}>10회</option>
            <option value={20}>20회</option>
          </Select>
        </Field>
      </div>
      <Loading query={trend}>
        {rounds.length === 0 ? (
          <Empty>아직 테스트 기록이 없습니다.</Empty>
        ) : (
          <>
          <Card>
            <CardContent className="p-3">
              <figure aria-label="회차별 성적 추이 그래프" className="m-0">
                <Suspense fallback={<p className="text-sm text-muted-fg">그래프 불러오는 중</p>}>
                  <TrendChart rounds={rounds} slots={slots} />
                </Suspense>
              </figure>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHead>
                  <TableRow>
                    <TableHeaderCell>날짜</TableHeaderCell>
                    <TableHeaderCell>테스트</TableHeaderCell>
                    <TableHeaderCell className="text-right">점수</TableHeaderCell>
                    <TableHeaderCell className="text-right">반평균</TableHeaderCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {rounds.map((round) => (
                    <TableRow key={`${round.date}-${round.source}-${round.name}`}>
                      <TableCell className="whitespace-nowrap">{shortDate(round.date)}</TableCell>
                      <TableCell className="break-keep">{round.name}</TableCell>
                      <TableCell className="text-right tabular-nums">{round.score ?? '—'}</TableCell>
                      <TableCell className="text-right tabular-nums text-muted-fg">{round.class_average ?? '—'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
          </>
        )}
      </Loading>
    </div>
  )
}

export function ExamsPage() {
  const student = usePortalStudent()
  const [examId, setExamId] = useState<number | null>(null)
  const exams = useQuery({ queryKey: ['portal-exams', student.id], queryFn: () => fetchPortalExams(student.id) })
  const detail = useQuery({
    queryKey: ['portal-exam', student.id, examId],
    queryFn: () => fetchPortalExam(student.id, examId!),
    enabled: examId !== null,
  })
  if (examId !== null) {
    return (
      <div className="flex flex-col gap-3">
        <Button type="button" variant="ghost" size="sm" className="self-start" onClick={() => setExamId(null)}>
          ← 시험 목록
        </Button>
        <Loading query={detail}>
          {detail.data && (
            <>
              <h2 className="text-lg font-semibold">{detail.data.name}</h2>
              <p className="text-sm text-muted-fg">
                {detail.data.exam_date ?? ''} · {detail.data.score ?? '—'}점{detail.data.max_score !== null && ` / ${detail.data.max_score}점`}
              </p>
              <Card>
                <CardContent className="p-0">
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableHeaderCell>번호</TableHeaderCell>
                        <TableHeaderCell>답</TableHeaderCell>
                        <TableHeaderCell>정오</TableHeaderCell>
                        <TableHeaderCell className="text-right">배점</TableHeaderCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {detail.data.answers.map((answer) => (
                        <TableRow key={answer.no}>
                          <TableCell className="tabular-nums">{answer.no}</TableCell>
                          <TableCell className="tabular-nums">{answer.raw_value ?? '—'}</TableCell>
                          <TableCell className={answer.is_correct === false ? 'text-danger' : answer.is_correct ? 'text-success' : 'text-muted-fg'}>
                            {answer.is_correct === null ? '—' : answer.is_correct ? 'O' : 'X'}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">{answer.points ?? '—'}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </>
          )}
        </Loading>
      </div>
    )
  }
  return (
    <div className="flex flex-col gap-3">
      <h2 className="text-lg font-semibold">{student.name} 시험 결과</h2>
      <Loading query={exams}>
        {(exams.data ?? []).length === 0 && <Empty>아직 채점된 시험이 없습니다.</Empty>}
        {(exams.data ?? []).map((exam) => (
          <button
            key={exam.exam_id}
            type="button"
            className="rounded-lg border bg-surface px-4 py-3 text-left shadow-sm outline-none hover:border-brand focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
            onClick={() => setExamId(exam.exam_id)}
          >
            <span className="flex items-center justify-between gap-3">
              <span className="break-keep">{exam.name}</span>
              <span className="tabular-nums whitespace-nowrap">
                {exam.score ?? '—'}점{exam.max_score !== null && ` / ${exam.max_score}`}
              </span>
            </span>
            {exam.exam_date && <span className="text-xs text-muted-fg">{exam.exam_date}</span>}
          </button>
        ))}
      </Loading>
    </div>
  )
}

export function ConsultsPage() {
  const student = usePortalStudent()
  const consults = useQuery({ queryKey: ['portal-consults', student.id], queryFn: () => fetchPortalConsults(student.id) })
  return (
    <div className="flex flex-col gap-3">
      <h2 className="text-lg font-semibold">{student.name} 상담 기록</h2>
      <Loading query={consults}>
        {(consults.data ?? []).length === 0 && <Empty>아직 상담 기록이 없습니다.</Empty>}
        {(consults.data ?? []).map((consult, index) => (
          <Card key={`${consult.consulted_on}-${index}`}>
            <CardContent className="flex flex-col gap-2 p-4">
              <h3 className="text-sm font-semibold">{consult.consulted_on}</h3>
              <p className="text-sm break-keep whitespace-pre-wrap">{consult.content}</p>
              {consult.follow_up && <Section title="후속 조치">{consult.follow_up}</Section>}
            </CardContent>
          </Card>
        ))}
      </Loading>
    </div>
  )
}

export function MessagesPage() {
  const student = usePortalStudent()
  const messages = useQuery({ queryKey: ['portal-messages', student.id], queryFn: () => fetchPortalMessages(student.id) })
  return (
    <div className="flex flex-col gap-3">
      <h2 className="text-lg font-semibold">{student.name} 받은 문자</h2>
      <Loading query={messages}>
        {(messages.data ?? []).length === 0 && <Empty>아직 받은 문자가 없습니다.</Empty>}
        {(messages.data ?? []).map((message) => (
          <Card key={message.sent_at}>
            <CardContent className="flex flex-col gap-2 p-4">
              <h3 className="text-xs font-medium text-muted-fg">{message.sent_at.slice(0, 16).replace('T', ' ')}</h3>
              <p className="text-sm break-keep whitespace-pre-wrap">{message.body}</p>
            </CardContent>
          </Card>
        ))}
      </Loading>
    </div>
  )
}
