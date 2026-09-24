import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Stat } from '../components/ui/stat'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from '../components/ui/table'
import { fetchExamResults, fetchQuestionStats, type QuestionStats } from '../api'

const FOCUS_RATE = 40 // 서버의 집중 해설 기준과 같다
const CIRCLED = ['①', '②', '③', '④', '⑤']
const FORM_LABEL = { odd: '홀수형', even: '짝수형' }
const TABS = ['문항별 정오답', '학생별 성적', '오답 유형 통계'] as const

function percent(value: number | null): string {
  return value === null ? '—' : `${value.toFixed(1)}%`
}

/** 선택 분포. 객관식은 ①~⑤, 단답형은 값 그대로 쓴다. */
function spread(question: QuestionStats['questions'][number]): string {
  const multipleChoice = (question.answer ?? 0) <= 5 && Object.keys(question.choices).every((v) => Number(v) <= 5)
  return Object.entries(question.choices)
    .map(([value, count]) => `${multipleChoice ? CIRCLED[Number(value) - 1] : `${value} `}${count}명`)
    .join(' · ')
}

/** 화면 ④의 시험 KPI와 탭(FR-36). 반영된 답안지가 없으면 그리지 않는다. */
export function ExamResultsCard({ examId }: { examId: number }) {
  const results = useQuery({ queryKey: ['exam-results', examId], queryFn: () => fetchExamResults(examId) })
  const stats = useQuery({ queryKey: ['question-stats', examId], queryFn: () => fetchQuestionStats(examId) })
  const [tab, setTab] = useState<(typeof TABS)[number]>(TABS[0])

  // 결과가 없거나 모양이 다르면 카드를 빼고 나머지 화면은 그대로 둔다
  if (!results.data?.summary?.attempts) return null
  const { summary, students, score_basis } = results.data
  const focus = new Set(summary.focus_questions)

  return (
    <Card className="mt-5">
      <CardHeader>
        <CardTitle>시험 결과</CardTitle>
        {score_basis === 'ratio' && (
          <p className="mt-1 text-xs text-muted-fg">
            배점이 없는 문항이 있어 맞힌 비율 × 만점으로 점수를 냈습니다. 모든 문항에 배점이 있으면 배점 합으로 계산합니다(다시 반영 필요).
          </p>
        )}
      </CardHeader>
      <CardContent>
        <div className="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Stat
            title="응시 현황"
            value={summary.enrolled === null ? `${summary.attempts}명` : `${summary.attempts}/${summary.enrolled}`}
          />
          <Stat title="반 평균 성적" value={summary.average === null ? '—' : summary.average.toFixed(1)}>
            <span>
              최고 {summary.highest} · 최저 {summary.lowest}
            </span>
          </Stat>
          <Stat title="반 평균 정답률" value={percent(summary.average_correct_rate)} />
          <Stat title="집중 해설 문항" value={`${summary.focus_questions.length}문항`}>
            <span>정답률 {FOCUS_RATE}% 미만</span>
          </Stat>
        </div>

        <div role="tablist" aria-label="시험 결과 보기" className="mb-3 flex gap-1 border-b">
          {TABS.map((name) => (
            <button
              key={name}
              type="button"
              role="tab"
              aria-selected={tab === name}
              onClick={() => setTab(name)}
              className={[
                '-mb-px border-b-2 px-3 py-2 text-sm outline-none focus-visible:outline-2 focus-visible:outline-ring',
                tab === name ? 'border-brand font-medium text-fg' : 'border-transparent text-muted-fg hover:text-fg',
              ].join(' ')}
            >
              {name}
            </button>
          ))}
        </div>

        <div role="tabpanel" aria-label={tab} className="-mx-5">
          {tab === '문항별 정오답' && (
            <Table aria-label="문항별 정오답">
              <TableHead>
                <TableRow>
                  <TableHeaderCell>번호</TableHeaderCell>
                  <TableHeaderCell>정답(홀/짝)</TableHeaderCell>
                  <TableHeaderCell>정답률</TableHeaderCell>
                  <TableHeaderCell>선택 분포</TableHeaderCell>
                  <TableHeaderCell>단원</TableHeaderCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {stats.data?.questions.map((question) => (
                  <TableRow key={question.no}>
                    <TableCell className="tabular-nums">{question.no}</TableCell>
                    <TableCell className="tabular-nums">
                      {question.answer ?? '—'} / {question.answer_even ?? '—'}
                    </TableCell>
                    <TableCell className="whitespace-nowrap tabular-nums">
                      {percent(question.correct_rate)}
                      {focus.has(question.no) && (
                        <span className="ml-2 rounded bg-warning px-1.5 py-0.5 text-xs font-medium text-warning-fg">
                          집중 해설
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="text-muted-fg">{spread(question)}</TableCell>
                    <TableCell className="text-muted-fg">{question.unit ?? '—'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
          {tab === '학생별 성적' && (
            <Table aria-label="학생별 성적">
              <TableHead>
                <TableRow>
                  <TableHeaderCell>학생</TableHeaderCell>
                  <TableHeaderCell>문형</TableHeaderCell>
                  <TableHeaderCell>점수</TableHeaderCell>
                  <TableHeaderCell>맞힌 문항</TableHeaderCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {students.map((row) => (
                  <TableRow key={row.student.id}>
                    <TableCell className="whitespace-nowrap">{row.student.name}</TableCell>
                    <TableCell className="whitespace-nowrap">{row.form ? FORM_LABEL[row.form] : '—'}</TableCell>
                    <TableCell className="tabular-nums">{row.score ?? '—'}</TableCell>
                    <TableCell className="tabular-nums">{row.correct}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
          {tab === '오답 유형 통계' && (
            <Table aria-label="오답 유형 통계">
              <TableHead>
                <TableRow>
                  <TableHeaderCell>단원</TableHeaderCell>
                  <TableHeaderCell>문항 수</TableHeaderCell>
                  <TableHeaderCell>오답률</TableHeaderCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {stats.data?.units.map((unit) => (
                  <TableRow key={unit.unit}>
                    <TableCell>{unit.unit}</TableCell>
                    <TableCell className="tabular-nums">{unit.questions}</TableCell>
                    <TableCell className="tabular-nums">{percent(unit.wrong_rate)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
