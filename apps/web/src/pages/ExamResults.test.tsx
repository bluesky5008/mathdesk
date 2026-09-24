import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ExamResults, QuestionStats } from '../api'
import { ExamResultsCard } from './ExamResults'

function renderCard() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <ExamResultsCard examId={5} />
    </QueryClientProvider>,
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
})

const results: ExamResults = {
  score_basis: 'points',
  summary: {
    attempts: 3,
    enrolled: 4,
    average: 91.33,
    highest: 100,
    lowest: 85,
    average_correct_rate: 90,
    focus_questions: [1, 2, 16],
  },
  students: [
    { student: { id: 1, name: '가' }, form: 'odd', source: 'omr', score: 100, correct: 30, answers: [] },
    { student: { id: 2, name: '나' }, form: 'even', source: 'omr', score: 85, correct: 25, answers: [] },
  ],
}

const stats: QuestionStats = {
  questions: [
    { no: 1, answer: 1, answer_even: 5, correct_rate: 33.3, choices: { '1': 1, '2': 2 }, unit: '수열', sub_type: null, difficulty: 'mid' },
    { no: 2, answer: 3, answer_even: 2, correct_rate: 100, choices: { '3': 3 }, unit: '수열', sub_type: null, difficulty: 'low' },
  ],
  units: [
    { unit: '수열', questions: 10, wrong_rate: 5 },
    { unit: '미분', questions: 20, wrong_rate: 2.5 },
  ],
}

function stub(body: { results: ExamResults; stats: QuestionStats }) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      if (url.endsWith('/results')) return Response.json(body.results)
      if (url.endsWith('/question-stats')) return Response.json(body.stats)
      return Response.json({})
    }),
  )
}

describe('ExamResultsCard', () => {
  it('shows the exam KPIs of screen ④', async () => {
    stub({ results, stats })
    renderCard()

    expect(await screen.findByRole('heading', { name: '응시 현황' })).toBeInTheDocument()
    expect(screen.getByText('3/4')).toBeInTheDocument()
    expect(screen.getByText('91.3')).toBeInTheDocument()
    expect(screen.getByText('최고 100 · 최저 85')).toBeInTheDocument()
    expect(screen.getByText('90.0%')).toBeInTheDocument()
    expect(screen.getByText('3문항')).toBeInTheDocument()
  })

  it('switches between per-question, per-student and wrong-type tabs', async () => {
    stub({ results, stats })
    const user = userEvent.setup()
    renderCard()

    const questions = await screen.findByRole('table', { name: '문항별 정오답' })
    const first = within(questions).getAllByRole('row')[1]
    expect(within(first).getByText('33.3%')).toBeInTheDocument()
    expect(within(first).getByText('집중 해설')).toBeInTheDocument()
    expect(within(first).getByText('①1명 · ②2명')).toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: '학생별 성적' }))
    const students = screen.getByRole('table', { name: '학생별 성적' })
    expect(within(students).getByText('짝수형')).toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: '오답 유형 통계' }))
    const units = screen.getByRole('table', { name: '오답 유형 통계' })
    expect(within(within(units).getAllByRole('row')[1]).getByText('수열')).toBeInTheDocument()
  })

  it('says how the score was computed when points are missing', async () => {
    stub({ results: { ...results, score_basis: 'ratio' }, stats })
    renderCard()

    expect(await screen.findByText(/배점이 없는 문항이 있어/)).toBeInTheDocument()
  })

  it('renders nothing before any sheet is applied', async () => {
    stub({ results: { ...results, students: [], summary: { ...results.summary, attempts: 0 } }, stats })
    const { container } = renderCard()

    await vi.waitFor(() => expect(vi.mocked(fetch)).toHaveBeenCalled())
    expect(container).toBeEmptyDOMElement()
  })
})
