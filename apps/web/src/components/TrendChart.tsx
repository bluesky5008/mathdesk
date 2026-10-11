import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import type { StudentRound } from '../api'

/** 계열색은 브랜드색이 아니라 차트 전용 토큰을 쓴다. 테마가 바뀌어도 두 계열의 간격이 유지된다. */
const MINE = 'var(--md-color-chart-1)'
const CLASS_AVERAGE = 'var(--md-color-chart-2)'
const AXIS = 'var(--md-color-muted-fg)'
const GRID = 'var(--md-color-border)'

const CHART_MARGIN = { top: 8, right: 16, bottom: 0, left: -20 }

function axisProps() {
  return {
    stroke: AXIS,
    tick: { fill: AXIS, fontSize: 11 },
    tickLine: false,
    axisLine: { stroke: GRID },
  }
}

/**
 * 회차별 점수 추이(FR-24, DCR-018). 성적 통계 화면과 포털 추이 탭(DCR-025)이 같은 그래프를 쓴다.
 * 가로축은 고른 회차 수만큼 칸을 둔다. 회차가 적으면 왼쪽부터 채워 점 간격이 회차 수에 따라 달라지지 않게 한다.
 */
export function TrendChart({ rounds, slots }: { rounds: StudentRound[]; slots: number }) {
  const data = Array.from({ length: slots }, (_, index) => {
    const round = rounds[index]
    return round
      ? { label: round.date.slice(5), name: round.name, mine: round.score, klass: round.class_average }
      : { label: '' }
  })
  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data} margin={CHART_MARGIN}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="label" {...axisProps()} />
        <YAxis domain={[0, 100]} {...axisProps()} />
        <Tooltip
          labelFormatter={(label, payload) => [label, payload[0]?.payload.name].filter(Boolean).join(' ')}
        />
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
