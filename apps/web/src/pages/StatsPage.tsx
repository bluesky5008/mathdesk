import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useSearchParams } from 'react-router'

import { ATTENDANCE } from '../components/AttendanceButtons'
import { TrendChart } from '../components/TrendChart'
import { PageHeader } from '../components/PageHeader'
import { buttonStyles } from '../components/ui/button'
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
import {
  fetchClasses,
  fetchClassStats,
  fetchStudentHistory,
  statsExportUrl,
  type StudentRound,
} from '../api'
import { today } from '../lib/date'

function weeksAgo(count: number): string {
  const day = new Date()
  day.setDate(day.getDate() - 7 * count)
  return `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, '0')}-${String(day.getDate()).padStart(2, '0')}`
}

const num = (value: number | null) => (value === null ? '—' : String(value))

const pct = (value: number | null) => (value === null ? '—' : `${value}%`)

const attendance = (status: string | null) =>
  ATTENDANCE.find(([value]) => value === status)?.[1] ?? '—'

export function StatsPage() {
  const classes = useQuery({ queryKey: ['classes'], queryFn: () => fetchClasses() })
  // 대시보드의 과제·테스트 KPI 링크는 반과 그 주 범위를 주소로 넘긴다
  const [params] = useSearchParams()
  const [classId, setClassId] = useState<number | null>(Number(params.get('class')) || null)
  const [start, setStart] = useState(params.get('start') || weeksAgo(8))
  const [end, setEnd] = useState(params.get('end') || today())
  const [studentId, setStudentId] = useState<number | null>(null)
  const [rounds, setRounds] = useState<10 | 20>(10)

  const activeClassId = classId ?? classes.data?.[0]?.id ?? null
  const stats = useQuery({
    queryKey: ['class-stats', activeClassId, start, end],
    queryFn: () => fetchClassStats(activeClassId!, start, end),
    enabled: activeClassId !== null,
  })

  const rows = stats.data?.period.students ?? []
  const activeStudentId = studentId ?? rows[0]?.student_id ?? null
  const history = useQuery({
    queryKey: ['student-history', activeStudentId, end, activeClassId, rounds],
    queryFn: () => fetchStudentHistory(activeStudentId!, end, activeClassId!, rounds),
    enabled: activeStudentId !== null && activeClassId !== null,
  })
  // 전체 회차가 10 이하이면 10회로 고정한다(DCR-018)
  const fixedAtTen = (history.data?.total ?? 0) <= 10
  const slots = fixedAtTen ? 10 : rounds

  return (
    <section className="mb-8">
      <PageHeader title="성적 통계">
        <Field label="반" htmlFor="stats-class" className="min-w-36 flex-1 sm:flex-none">
          <Select
            id="stats-class"
            className="w-full sm:w-auto"
            value={activeClassId ?? ''}
            onChange={(event) => {
              setClassId(Number(event.target.value))
              setStudentId(null)
              setRounds(10)
            }}
          >
            {classes.data?.map((klass) => (
              <option key={klass.id} value={klass.id}>
                {klass.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="시작" htmlFor="stats-start" className="min-w-32 flex-1 sm:flex-none">
          <Input
            id="stats-start"
            type="date"
            className="w-full sm:w-40"
            value={start}
            onChange={(event) => setStart(event.target.value)}
          />
        </Field>
        <Field label="종료" htmlFor="stats-end" className="min-w-32 flex-1 sm:flex-none">
          <Input
            id="stats-end"
            type="date"
            className="w-full sm:w-40"
            value={end}
            onChange={(event) => setEnd(event.target.value)}
          />
        </Field>
      </PageHeader>

      {rows.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-fg">
            표본이 없습니다.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-5 xl:grid-cols-2">
          <Card className="min-w-0">
            <CardHeader className="flex-row items-center justify-between gap-3">
              <CardTitle>반 통계</CardTitle>
              {activeClassId !== null && (
                <a
                  className={buttonStyles({ variant: 'outline', size: 'sm' })}
                  href={statsExportUrl(activeClassId, start, end)}
                >
                  엑셀 내려받기
                </a>
              )}
            </CardHeader>
            <CardContent className="p-0">
              <Table aria-label="학생별 통계">
                <TableHead>
                  <TableRow>
                    <TableHeaderCell>학생</TableHeaderCell>
                    <TableHeaderCell>테스트 평균</TableHeaderCell>
                    <TableHeaderCell>과제 완수율</TableHeaderCell>
                    <TableHeaderCell>출결률</TableHeaderCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {rows.map((row) => (
                    <TableRow key={row.student_id}>
                      <TableCell className="font-medium whitespace-nowrap">{row.name}</TableCell>
                      <TableCell className="tabular-nums">{num(row.test_average)}</TableCell>
                      <TableCell className="tabular-nums">{pct(row.homework_completion)}</TableCell>
                      <TableCell className="tabular-nums">{pct(row.attendance_rate)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <Card className="min-w-0">
            <CardHeader className="flex-row items-center justify-between gap-3">
              <CardTitle>회차별 성적 추이</CardTitle>
              <div className="flex gap-3">
                <Field label="학생" htmlFor="stats-student">
                  <Select
                    id="stats-student"
                    value={activeStudentId ?? ''}
                    onChange={(event) => {
                      setStudentId(Number(event.target.value))
                      setRounds(10)
                    }}
                  >
                    {rows.map((row) => (
                      <option key={row.student_id} value={row.student_id}>
                        {row.name}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field label="회차" htmlFor="stats-rounds">
                  <Select
                    id="stats-rounds"
                    value={slots}
                    disabled={fixedAtTen}
                    onChange={(event) => setRounds(Number(event.target.value) as 10 | 20)}
                  >
                    <option value={10}>10회</option>
                    <option value={20}>20회</option>
                  </Select>
                </Field>
              </div>
            </CardHeader>
            <CardContent>
              <TrendChart rounds={history.data?.rounds ?? []} slots={slots} />
              <Table aria-label="회차별 성적 추이" className="mt-4">
                <TableHead>
                  <TableRow>
                    <TableHeaderCell>날짜</TableHeaderCell>
                    <TableHeaderCell>시험명</TableHeaderCell>
                    <TableHeaderCell>내 점수</TableHeaderCell>
                    <TableHeaderCell>반 평균</TableHeaderCell>
                    <TableHeaderCell>과제 등급</TableHeaderCell>
                    <TableHeaderCell>출결</TableHeaderCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {(history.data?.rounds ?? []).map((round, index) => (
                    <TableRow key={index}>
                      <TableCell className="whitespace-nowrap">{round.date}</TableCell>
                      <TableCell className="whitespace-nowrap">{round.name}</TableCell>
                      <TableCell className="tabular-nums">{num(round.score)}</TableCell>
                      <TableCell className="tabular-nums">{num(round.class_average)}</TableCell>
                      <TableCell>{round.homework_grade ?? '—'}</TableCell>
                      <TableCell className="whitespace-nowrap">{attendance(round.attendance_status)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </div>
      )}
    </section>
  )
}
