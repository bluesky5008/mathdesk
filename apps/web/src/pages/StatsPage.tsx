import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useSearchParams } from 'react-router'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

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
  type StudentWeek,
} from '../api'
import { today } from '../lib/date'

/** 계열색은 브랜드색이 아니라 차트 전용 토큰을 쓴다. 테마가 바뀌어도 두 계열의 간격이 유지된다. */
const MINE = 'var(--md-color-chart-1)'
const CLASS_AVERAGE = 'var(--md-color-chart-2)'
const AXIS = 'var(--md-color-muted-fg)'
const GRID = 'var(--md-color-border)'

function weeksAgo(count: number): string {
  const day = new Date()
  day.setDate(day.getDate() - 7 * count)
  return `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, '0')}-${String(day.getDate()).padStart(2, '0')}`
}

const num = (value: number | null) => (value === null ? '—' : String(value))
const pct = (value: number | null) => (value === null ? '—' : `${value}%`)

const CHART_MARGIN = { top: 8, right: 16, bottom: 0, left: -20 }

function axisProps() {
  return {
    stroke: AXIS,
    tick: { fill: AXIS, fontSize: 11 },
    tickLine: false,
    axisLine: { stroke: GRID },
  }
}

function TrendChart({ weeks }: { weeks: StudentWeek[] }) {
  const data = weeks.map((week) => ({
    week: week.week_start.slice(5),
    mine: week.test_average,
    klass: week.class_test_average,
  }))
  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data} margin={CHART_MARGIN}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="week" {...axisProps()} />
        <YAxis domain={[0, 100]} {...axisProps()} />
        <Tooltip />
        <Legend />
        <Line
          type="monotone"
          name="내 점수"
          dataKey="mine"
          stroke={MINE}
          strokeWidth={2}
          dot={{ r: 4, strokeWidth: 2 }}
          connectNulls
          isAnimationActive={false}
        />
        <Line
          type="monotone"
          name="반 평균"
          dataKey="klass"
          stroke={CLASS_AVERAGE}
          strokeWidth={2}
          dot={{ r: 4, strokeWidth: 2 }}
          connectNulls
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

function DistributionChart({ data }: { data: { bucket: string; count: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} margin={CHART_MARGIN}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="bucket" {...axisProps()} />
        <YAxis allowDecimals={false} {...axisProps()} />
        <Tooltip />
        <Bar name="학생 수" dataKey="count" fill={MINE} radius={[4, 4, 0, 0]} isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  )
}

export function StatsPage() {
  const classes = useQuery({ queryKey: ['classes'], queryFn: () => fetchClasses() })
  // 대시보드의 과제·테스트 KPI 링크는 반과 그 주 범위를 주소로 넘긴다
  const [params] = useSearchParams()
  const [classId, setClassId] = useState<number | null>(Number(params.get('class')) || null)
  const [start, setStart] = useState(params.get('start') || weeksAgo(8))
  const [end, setEnd] = useState(params.get('end') || today())
  const [studentId, setStudentId] = useState<number | null>(null)

  const activeClassId = classId ?? classes.data?.[0]?.id ?? null
  const stats = useQuery({
    queryKey: ['class-stats', activeClassId, start, end],
    queryFn: () => fetchClassStats(activeClassId!, start, end),
    enabled: activeClassId !== null,
  })

  const rows = stats.data?.period.students ?? []
  const activeStudentId = studentId ?? rows[0]?.student_id ?? null
  const history = useQuery({
    queryKey: ['student-history', activeStudentId, end, activeClassId],
    queryFn: () => fetchStudentHistory(activeStudentId!, end, activeClassId!),
    enabled: activeStudentId !== null && activeClassId !== null,
  })

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
              <div className="px-5 py-4">
                <p className="mb-2 text-xs text-muted-fg">점수 분포 (학생 수)</p>
                <DistributionChart data={stats.data?.period.test.distribution ?? []} />
              </div>
            </CardContent>
          </Card>

          <Card className="min-w-0">
            <CardHeader className="flex-row items-center justify-between gap-3">
              <CardTitle>학생 주간 추이</CardTitle>
              <Field label="학생" htmlFor="stats-student">
                <Select
                  id="stats-student"
                  value={activeStudentId ?? ''}
                  onChange={(event) => setStudentId(Number(event.target.value))}
                >
                  {rows.map((row) => (
                    <option key={row.student_id} value={row.student_id}>
                      {row.name}
                    </option>
                  ))}
                </Select>
              </Field>
            </CardHeader>
            <CardContent>
              <TrendChart weeks={history.data?.weeks ?? []} />
              <Table aria-label="주간 추이" className="mt-4">
                <TableHead>
                  <TableRow>
                    <TableHeaderCell>주 시작</TableHeaderCell>
                    <TableHeaderCell>내 점수</TableHeaderCell>
                    <TableHeaderCell>반 평균</TableHeaderCell>
                    <TableHeaderCell>과제 완수율</TableHeaderCell>
                    <TableHeaderCell>출결률</TableHeaderCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {(history.data?.weeks ?? []).map((week) => (
                    <TableRow key={week.week_start}>
                      <TableCell className="whitespace-nowrap">{week.week_start}</TableCell>
                      <TableCell className="tabular-nums">{num(week.test_average)}</TableCell>
                      <TableCell className="tabular-nums">{num(week.class_test_average)}</TableCell>
                      <TableCell className="tabular-nums">{pct(week.homework_completion)}</TableCell>
                      <TableCell className="tabular-nums">{pct(week.attendance_rate)}</TableCell>
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
