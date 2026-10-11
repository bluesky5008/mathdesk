import { useQuery } from '@tanstack/react-query'
import { useRef, useState, type MutableRefObject } from 'react'
import { Link, NavLink, Outlet, useOutletContext, useSearchParams } from 'react-router'

import { PageHeader } from '../components/PageHeader'
import { Field } from '../components/ui/field'
import { DatePickerButton, weekdayOf } from '../components/ui/month-calendar'
import { Select } from '../components/ui/select'
import { today } from '../lib/date'
import { fetchClasses, fetchDailyCalendar } from '../api'

const TABS = [
  { to: '/daily', label: '반별 정보' },
  { to: '/daily/students', label: '학생별 정보' },
]

export type DailySelection = {
  classId: number | null
  date: string
  studentId: number | null
  /** 반·날짜·학생을 바꾼다. 반이 바뀌면 학생 선택은 지운다 */
  select: (next: { classId?: number; date?: string; studentId?: number }) => void
  /** 떠나기 전 확인. 미저장 입력이 있는 탭이 등록하고, 거절(false)하면 이동하지 않는다 */
  guard: MutableRefObject<(() => boolean) | null>
}

export function useDailySelection(): DailySelection {
  return useOutletContext<DailySelection>()
}

/** 반별·학생별 탭이 함께 쓰는 "이 날짜에 배정된 학생 없음" 안내 */
export function EmptyRosterNotice() {
  return (
    <p className="px-5 py-6 text-sm text-muted-fg">
      이 날짜에 이 반에 배정된 학생이 없습니다.{' '}
      <Link to="/students/classes" className="font-medium text-brand underline">
        학생/반 관리 → 반
      </Link>{' '}
      탭의 [명단]에서 배정하세요.
    </p>
  )
}

/**
 * 일일 수업 & 성적 입력의 공통 머리말(반·날짜)과 탭(FR-45). 선택값의 정본은 주소 쿼리라서
 * 탭 전환·새로 고침·대시보드 링크(`/daily?class=&date=`)에서 그대로 유지된다.
 */
export function DailyLayout() {
  const classes = useQuery({ queryKey: ['classes'], queryFn: () => fetchClasses() })
  const [params, setParams] = useSearchParams()
  const classId = Number(params.get('class')) || classes.data?.[0]?.id || null
  const date = params.get('date') || today()
  const studentId = Number(params.get('student')) || null
  const guard = useRef<(() => boolean) | null>(null)
  const canLeave = () => guard.current?.() ?? true

  function select(next: { classId?: number; date?: string; studentId?: number }) {
    if (!canLeave()) return
    setParams((current) => {
      const query = new URLSearchParams(current)
      if (next.classId !== undefined) {
        query.set('class', String(next.classId))
        query.delete('student')
      }
      if (next.date !== undefined) query.set('date', next.date)
      if (next.studentId !== undefined) query.set('student', String(next.studentId))
      return query
    })
  }

  // 달력 표시: 수업 요일은 반 시간표에서, 기록이 있는 날은 보이는 달의 조회로(FR-46)
  const [month, setMonth] = useState(date.slice(0, 7))
  const calendar = useQuery({
    queryKey: ['daily-calendar', classId, month],
    queryFn: () => fetchDailyCalendar(classId!, month),
    enabled: classId !== null,
  })
  const lessonWeekdays = classes.data?.find((klass) => klass.id === classId)?.schedules.map((s) => s.weekday) ?? []
  const recorded = new Set(calendar.data?.recorded_dates ?? [])

  const search = params.toString() ? `?${params}` : ''
  const selection: DailySelection = { classId, date, studentId, select, guard }

  return (
    <section>
      <PageHeader title="일일 수업 & 성적 입력">
        <Field label="반" htmlFor="daily-class">
          <Select
            id="daily-class"
            value={classId ?? ''}
            onChange={(event) => select({ classId: Number(event.target.value) })}
          >
            {classes.data?.map((klass) => (
              <option key={klass.id} value={klass.id}>
                {klass.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="날짜" htmlFor="daily-date">
          <DatePickerButton
            id="daily-date"
            value={date}
            onChange={(next) => select({ date: next })}
            onMonthChange={setMonth}
            emphasized={(day) => lessonWeekdays.includes(weekdayOf(day)) || recorded.has(day)}
            dotted={(day) => recorded.has(day)}
          />
        </Field>
      </PageHeader>

      <nav aria-label="일일 입력" className="mb-5 flex gap-1 border-b">
        {TABS.map(({ to, label }) => (
          <NavLink
            key={to}
            to={`${to}${search}`}
            end
            onClick={(event) => {
              if (!canLeave()) event.preventDefault()
            }}
            className={({ isActive }) =>
              [
                '-mb-px border-b-2 px-3 py-2 text-sm outline-none focus-visible:outline-2 focus-visible:outline-ring',
                isActive ? 'border-brand font-medium text-fg' : 'border-transparent text-muted-fg hover:text-fg',
              ].join(' ')
            }
          >
            {label}
          </NavLink>
        ))}
      </nav>

      <Outlet context={selection} />
    </section>
  )
}
