import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import { PageHeader } from '../components/PageHeader'
import { Card, CardContent } from '../components/ui/card'
import { Field } from '../components/ui/field'
import { Select } from '../components/ui/select'
import { fetchTimetable, type TimetableClass, type TimetableSlot } from '../api'
import { WEEKDAYS } from './ClassesPage'

// 1분 = 1px. 한 시간 칸이 60px이라 120분 수업 블록이 두 칸을 채운다
const PX_PER_MINUTE = 1

const ALL = 'all'
const NONE = 'none'

function minutesOf(value: string): number {
  const [hours, minutes] = value.split(':').map(Number)
  return hours * 60 + minutes
}

function hhmm(value: string): string {
  return value.slice(0, 5)
}

function span(slot: TimetableSlot): string {
  return `${hhmm(slot.start_time)}~${hhmm(slot.end_time)}`
}

type Placed = { slot: TimetableSlot; start: number; lane: number; lanes: number }

/** 요일 하나의 수업을 겹치지 않는 줄(lane)에 나눠 담는다. 겹치는 수업은 열 안에서 나란히 선다. */
function placeDay(slots: TimetableSlot[], classMinutes: number): Placed[] {
  const laneEnds: number[] = []
  const placed = slots.map((slot) => {
    const start = minutesOf(slot.start_time)
    let lane = laneEnds.findIndex((end) => end <= start)
    if (lane === -1) lane = laneEnds.length
    laneEnds[lane] = start + classMinutes
    return { slot, start, lane, lanes: 0 }
  })
  return placed.map((item) => ({ ...item, lanes: laneEnds.length }))
}

function matches(item: TimetableClass, teacher: string): boolean {
  if (teacher === ALL) return true
  if (teacher === NONE) return item.teacher === null
  return String(item.teacher?.id) === teacher
}

function describe(item: TimetableClass, showTeacher: boolean): string {
  return [item.class_name, showTeacher ? item.teacher?.name : null].filter(Boolean).join(' · ')
}

// FR-42 — 강사는 담당 반만, 원장은 캠퍼스 전체를 본다(서버가 거른다). 원장은 강사별로 좁혀 본다
export function TimetablePage({ isDirector = false }: { isDirector?: boolean } = {}) {
  const timetable = useQuery({ queryKey: ['timetable'], queryFn: fetchTimetable })
  const [teacher, setTeacher] = useState(ALL)

  const data = timetable.data
  const slots = (data?.slots ?? []).filter((slot) => matches(slot, teacher))
  const unscheduled = (data?.unscheduled ?? []).filter((item) => matches(item, teacher))
  const teachers = [
    ...new Map(
      [...(data?.slots ?? []), ...(data?.unscheduled ?? [])]
        .flatMap((item) => (item.teacher ? [item.teacher] : []))
        .map((t) => [t.id, t]),
    ).values(),
  ].sort((a, b) => a.name.localeCompare(b.name, 'ko'))

  const classMinutes = data?.class_minutes ?? 120
  const starts = slots.map((slot) => minutesOf(slot.start_time))
  const axisStart = Math.floor(Math.min(...starts) / 60) * 60
  // 자정을 넘기는 수업은 24시에서 자른다
  const axisEnd = Math.min(24 * 60, Math.ceil((Math.max(...starts) + classMinutes) / 60) * 60)
  const hours = Array.from({ length: (axisEnd - axisStart) / 60 }, (_, i) => axisStart / 60 + i)
  const days = WEEKDAYS.map((label, weekday) => ({
    label,
    placed: placeDay(
      slots.filter((slot) => slot.weekday === weekday),
      classMinutes,
    ),
  }))

  return (
    <section>
      <PageHeader title="주간 시간표">
        {isDirector && (
          <Field label="강사" htmlFor="timetable-teacher">
            <Select id="timetable-teacher" value={teacher} onChange={(e) => setTeacher(e.target.value)}>
              <option value={ALL}>전체</option>
              {teachers.map((t) => (
                <option key={t.id} value={String(t.id)}>
                  {t.name}
                </option>
              ))}
              <option value={NONE}>담당 없음</option>
            </Select>
          </Field>
        )}
      </PageHeader>

      {data && (
        <p className="mb-3 text-sm text-muted-fg">
          수업 길이 {classMinutes}분 기준입니다.{isDirector && ' 학원 설정에서 바꿀 수 있습니다.'}
        </p>
      )}

      {data && slots.length === 0 && (
        <Card className="mb-5">
          <CardContent className="py-6 text-sm text-muted-fg">등록된 수업이 없습니다</CardContent>
        </Card>
      )}

      {slots.length > 0 && (
        <>
          {/* 넓은 화면: 요일 열 × 시간 행 격자 */}
          <Card className="mb-5 hidden md:block">
            <CardContent className="p-4">
              <section aria-label="주간 시간표 격자" className="flex gap-2">
                <div className="w-12 shrink-0 pt-7">
                  <ul aria-label="시각">
                    {hours.map((hour) => (
                      <li
                        key={hour}
                        className="text-xs text-muted-fg tabular-nums"
                        style={{ height: 60 * PX_PER_MINUTE }}
                      >
                        {`${String(hour).padStart(2, '0')}:00`}
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="grid min-w-0 flex-1 grid-cols-7 gap-1">
                  {days.map(({ label, placed }) => (
                    <div key={label} className="min-w-0">
                      <p className="h-7 text-center text-sm font-medium">{label}</p>
                      <ul
                        aria-label={`${label}요일 수업`}
                        className="relative rounded-md border bg-bg"
                        style={{
                          height: (axisEnd - axisStart) * PX_PER_MINUTE,
                          // 한 시간마다 옅은 가로줄
                          backgroundImage: `repeating-linear-gradient(to bottom, transparent 0, transparent ${60 * PX_PER_MINUTE - 1}px, var(--md-color-border) ${60 * PX_PER_MINUTE - 1}px, var(--md-color-border) ${60 * PX_PER_MINUTE}px)`,
                        }}
                      >
                        {placed.map(({ slot, start, lane, lanes }) => (
                          <li
                            key={`${slot.class_id}-${slot.start_time}`}
                            className="absolute overflow-hidden rounded-md border-l-2 border-brand bg-surface px-1.5 py-1 text-xs shadow-sm"
                            style={{
                              top: `${(start - axisStart) * PX_PER_MINUTE}px`,
                              height: `${classMinutes * PX_PER_MINUTE}px`,
                              left: `${(lane * 100) / lanes}%`,
                              width: `${100 / lanes}%`,
                            }}
                          >
                            <span className="block truncate font-medium">{slot.class_name}</span>
                            {/* 겹친 수업이 나란히 서면 폭이 좁아진다 — 시각이 잘리지 않게 "~" 뒤에서 줄을 바꾼다 */}
                            <span className="block text-muted-fg tabular-nums">
                              {hhmm(slot.start_time)}~<wbr />
                              {hhmm(slot.end_time)}
                            </span>
                            {isDirector && slot.teacher && (
                              <span className="block truncate text-muted-fg">{slot.teacher.name}</span>
                            )}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              </section>
            </CardContent>
          </Card>

          {/* 좁은 화면: 7열이 들어가지 않으므로 요일별 목록 */}
          <Card className="mb-5 md:hidden">
            <CardContent className="p-0">
              <section aria-label="요일별 시간표" className="divide-y">
                {days
                  .filter(({ placed }) => placed.length > 0)
                  .map(({ label, placed }) => (
                    <div key={label} className="px-4 py-3">
                      <h3 className="mb-1 text-sm font-semibold">{label}</h3>
                      <ul className="grid gap-1 text-sm">
                        {placed.map(({ slot }) => (
                          <li key={`${slot.class_id}-${slot.start_time}`} className="flex gap-3">
                            <span className="shrink-0 text-muted-fg tabular-nums">{span(slot)}</span>
                            <span className="min-w-0">{describe(slot, isDirector)}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
              </section>
            </CardContent>
          </Card>
        </>
      )}

      {unscheduled.length > 0 && (
        <Card>
          <CardContent className="py-4">
            <section aria-label="시간표 미등록">
              <h3 className="mb-2 text-sm font-semibold">시간표 미등록</h3>
              <p className="text-sm text-muted-fg">
                {unscheduled.map((item) => describe(item, isDirector)).join(', ')}
              </p>
            </section>
          </CardContent>
        </Card>
      )}
    </section>
  )
}
