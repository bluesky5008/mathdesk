import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState, type FormEvent } from 'react'

import { PageHeader } from '../components/PageHeader'
import { OmrSection } from './OmrSection'
import { Button, buttonStyles } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Dialog, DialogClose, DialogContent, DialogTitle } from '../components/ui/dialog'
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
import { Textarea } from '../components/ui/textarea'
import {
  difficultyCardUrl,
  fetchExam,
  fetchExams,
  fetchQuestions,
  fetchTask,
  registerExam,
  updateExam,
  updateQuestions,
  type Difficulty,
  type ExamDetail,
  type ExamQuestion,
  type ExamRow,
  type QuestionPatch,
} from '../api'

const LEVELS: [Difficulty, string][] = [
  ['low', '하'],
  ['mid', '중'],
  ['high', '상'],
  ['top', '최상'],
]
const LEVEL_LABEL = Object.fromEntries(LEVELS) as Record<string, string>

/** 정답표 입력 "3 5 1" 또는 "3,5,1"을 숫자 목록으로 바꾼다. 숫자가 아니면 null. */
export function parseAnswerKey(text: string): number[] | null {
  const parts = text.split(/[\s,]+/).filter(Boolean)
  const values = parts.map(Number)
  return values.every((value) => Number.isInteger(value) && value >= 0 && value <= 999)
    ? values
    : null
}

function status(row: ExamRow): string {
  if (row.status === 'confirmed') return '확정'
  if (row.question_count === null) return '분석 전'
  return row.needs_review ? `확인 필요 ${row.needs_review}` : '분석 완료'
}

function Register({ onRegistered }: { onRegistered: (examId: number) => void }) {
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [pending, setPending] = useState<{ examId: number; taskId: number } | null>(null)

  const start = useMutation({
    mutationFn: () => registerExam(name, file!),
    onSuccess: (started) => setPending(started),
  })

  // 분석은 배경 작업이다. 끝날 때까지 상태를 폴링한다(DES-18)
  const task = useQuery({
    queryKey: ['task', pending?.taskId],
    queryFn: () => fetchTask(pending!.taskId),
    enabled: pending !== null,
    refetchInterval: (query) =>
      ['done', 'failed'].includes(query.state.data?.status ?? '') ? false : 1000,
  })
  const taskStatus = task.data?.status
  useEffect(() => {
    if (!pending || !taskStatus || !['done', 'failed'].includes(taskStatus)) return
    // 실패해도 시험은 등록되어 있다. 목록에 보이게 하고 사유는 아래에 남긴다
    void queryClient.invalidateQueries({ queryKey: ['exams'] })
    if (taskStatus === 'done') {
      onRegistered(pending.examId)
      setPending(null)
      setName('')
      setFile(null)
    }
  }, [pending, taskStatus, queryClient, onRegistered])

  function submit(event: FormEvent) {
    event.preventDefault()
    if (name && file) start.mutate()
  }

  return (
    <Card className="mb-5">
      <CardHeader>
        <CardTitle>시험지 등록</CardTitle>
      </CardHeader>
      <CardContent>
        <form className="flex flex-wrap items-end gap-3" onSubmit={submit}>
          <Field label="시험명" htmlFor="exam-name" className="min-w-48 flex-1">
            <Input id="exam-name" value={name} onChange={(event) => setName(event.target.value)} />
          </Field>
          <Field label="시험지 파일" htmlFor="exam-file" className="min-w-48 flex-1">
            <Input
              id="exam-file"
              type="file"
              accept=".pdf,.hwp,.hwpx,.png,.jpg,.jpeg"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
          </Field>
          <Button
            type="submit"
            disabled={!name || !file || start.isPending || (pending !== null && taskStatus !== 'failed')}
          >
            업로드 후 분석
          </Button>
        </form>
        <p className="mt-2 text-xs text-muted-fg">
          .hwpx·.pdf를 권장합니다. .hwp가 읽히지 않으면 한글에서 PDF로 저장해 올려 주세요.
        </p>
        {pending && taskStatus !== 'failed' && (
          <p role="status" className="mt-3 text-sm text-muted-fg">
            분석 초안을 만드는 중입니다 · {task.data?.progress ?? 0}%
          </p>
        )}
        {(start.isError || taskStatus === 'failed') && (
          <p role="alert" className="mt-3 text-sm text-danger">
            {start.error?.message ?? task.data?.error}
          </p>
        )}
      </CardContent>
    </Card>
  )
}

function keyText(key: (number | null)[] | null): string {
  return key ? key.map((value) => value ?? '').join(' ') : ''
}

function ExamInfo({ exam }: { exam: ExamDetail }) {
  const queryClient = useQueryClient()
  const [form, setForm] = useState({
    question_count: String(exam.question_count ?? ''),
    max_score: String(exam.max_score ?? ''),
    odd: keyText(exam.answer_key_odd),
    even: keyText(exam.answer_key_even),
  })
  const [invalid, setInvalid] = useState<string | null>(null)

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['exam', exam.id] })
    void queryClient.invalidateQueries({ queryKey: ['exams'] })
  }
  const save = useMutation({
    mutationFn: (payload: Parameters<typeof updateExam>[1]) => updateExam(exam.id, payload),
    onSuccess: refresh,
  })

  function submit(event: FormEvent) {
    event.preventDefault()
    const odd = form.odd.trim() ? parseAnswerKey(form.odd) : undefined
    const even = form.even.trim() ? parseAnswerKey(form.even) : undefined
    if (odd === null || even === null) {
      setInvalid('정답은 0~999 사이의 숫자를 띄어쓰기나 쉼표로 구분해 입력합니다.')
      return
    }
    setInvalid(null)
    save.mutate({
      ...(form.question_count && { question_count: Number(form.question_count) }),
      ...(form.max_score && { max_score: Number(form.max_score) }),
      ...(odd && { answer_key_odd: odd }),
      ...(even && { answer_key_even: even }),
    })
  }

  const confirmed = exam.status === 'confirmed'
  return (
    <Card className="mb-5">
      <CardHeader className="flex-row items-center justify-between gap-3">
        <CardTitle>
          {exam.name}
          {confirmed && <span className="ml-2 text-sm font-normal text-muted-fg">확정됨</span>}
        </CardTitle>
        <Button
          type="button"
          variant={confirmed ? 'outline' : 'primary'}
          onClick={() => save.mutate({ status: confirmed ? 'draft' : 'confirmed' })}
        >
          {confirmed ? '확정 해제' : '문항 확정'}
        </Button>
      </CardHeader>
      <CardContent>
        <form className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" onSubmit={submit}>
          <Field label="문항 수" htmlFor="exam-count">
            <Input
              id="exam-count"
              inputMode="numeric"
              value={form.question_count}
              onChange={(event) => setForm({ ...form, question_count: event.target.value })}
            />
          </Field>
          <Field label="만점" htmlFor="exam-max">
            <Input
              id="exam-max"
              inputMode="numeric"
              value={form.max_score}
              onChange={(event) => setForm({ ...form, max_score: event.target.value })}
            />
          </Field>
          <Field label="홀수형 정답" htmlFor="exam-odd" className="sm:col-span-2">
            <Input
              id="exam-odd"
              placeholder="3 5 1 2 4 …"
              value={form.odd}
              onChange={(event) => setForm({ ...form, odd: event.target.value })}
            />
          </Field>
          <Field label="짝수형 정답" htmlFor="exam-even" className="sm:col-span-2">
            <Input
              id="exam-even"
              placeholder="1 5 3 2 4 …"
              value={form.even}
              onChange={(event) => setForm({ ...form, even: event.target.value })}
            />
          </Field>
          <div className="flex items-end sm:col-span-2">
            <Button type="submit" variant="outline">
              시험 정보 저장
            </Button>
          </div>
        </form>
        {(invalid || save.isError) && (
          <p role="alert" className="mt-3 text-sm text-danger">
            {invalid ?? save.error?.message}
          </p>
        )}
      </CardContent>
    </Card>
  )
}

function DifficultyTable({ exam }: { exam: ExamDetail }) {
  return (
    <Card className="mb-5">
      <CardHeader className="flex-row items-center justify-between gap-3">
        <div>
          <CardTitle>난이도 분석표</CardTitle>
          <p className="mt-1 text-xs text-muted-fg">AI 추정 난이도 · 실제 정답률과 별개입니다</p>
        </div>
        <a
          className={buttonStyles({ variant: 'outline', size: 'sm' })}
          href={difficultyCardUrl(exam.id)}
          download
        >
          이미지 저장
        </a>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {LEVELS.map(([level, label]) => (
          <div key={level} className="rounded-md bg-accent px-4 py-3">
            <div className="text-xs font-medium text-muted-fg">{label}</div>
            <div className="mt-1 text-xl font-semibold tabular-nums">
              {exam.difficulty[level]}문항
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

function QuestionDialog({
  question,
  onSave,
  onClose,
}: {
  question: ExamQuestion
  onSave: (patch: QuestionPatch) => void
  onClose: () => void
}) {
  const [form, setForm] = useState({
    unit: question.unit ?? '',
    sub_type: question.sub_type ?? '',
    difficulty: question.difficulty ?? 'mid',
    points: String(question.points ?? ''),
    rationale: question.rationale ?? '',
  })

  function submit(event: FormEvent) {
    event.preventDefault()
    onSave({
      no: question.no,
      unit: form.unit || null,
      sub_type: form.sub_type || null,
      difficulty: form.difficulty,
      points: form.points ? Number(form.points) : null,
      rationale: form.rationale || null,
    })
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogTitle className="mb-4 text-base font-semibold">{question.no}번 문항 수정</DialogTitle>
        <form className="grid grid-cols-2 gap-3" onSubmit={submit}>
          <Field label="단원" htmlFor="q-unit">
            <Input id="q-unit" value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} />
          </Field>
          <Field label="난이도" htmlFor="q-difficulty">
            <Select
              id="q-difficulty"
              className="w-full"
              value={form.difficulty}
              onChange={(e) => setForm({ ...form, difficulty: e.target.value })}
            >
              {LEVELS.map(([level, label]) => (
                <option key={level} value={level}>
                  {label}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="세부 유형" htmlFor="q-sub" className="col-span-2">
            <Input id="q-sub" value={form.sub_type} onChange={(e) => setForm({ ...form, sub_type: e.target.value })} />
          </Field>
          <Field label="배점" htmlFor="q-points">
            <Input
              id="q-points"
              inputMode="numeric"
              value={form.points}
              onChange={(e) => setForm({ ...form, points: e.target.value })}
            />
          </Field>
          <Field label="판단 근거" htmlFor="q-rationale" className="col-span-2">
            <Textarea
              id="q-rationale"
              value={form.rationale}
              onChange={(e) => setForm({ ...form, rationale: e.target.value })}
            />
          </Field>
          <div className="col-span-2 mt-2 flex justify-end gap-2">
            <DialogClose asChild>
              <Button type="button" variant="outline">
                취소
              </Button>
            </DialogClose>
            <Button type="submit">저장</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function QuestionTable({ examId }: { examId: number }) {
  const queryClient = useQueryClient()
  const questions = useQuery({ queryKey: ['questions', examId], queryFn: () => fetchQuestions(examId) })
  const [editing, setEditing] = useState<ExamQuestion | null>(null)

  // 사용자가 손댄 문항은 확인된 것으로 본다. 번호만 보내면 초안 그대로 확인한다(FR-29)
  const save = useMutation({
    mutationFn: (patch: QuestionPatch) => updateQuestions(examId, [patch]),
    onSuccess: () => {
      setEditing(null)
      void queryClient.invalidateQueries({ queryKey: ['questions', examId] })
      void queryClient.invalidateQueries({ queryKey: ['exam', examId] })
      void queryClient.invalidateQueries({ queryKey: ['exams'] })
    },
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>시험지 문항 분석</CardTitle>
        <p className="mt-1 text-xs text-muted-fg">
          번호별 출제 유형과 난이도 초안입니다. 확인 필요 문항은 원본과 대조해 주세요.
        </p>
      </CardHeader>
      <CardContent className="p-0">
        <Table aria-label="시험지 문항 분석">
          <TableHead>
            <TableRow>
              <TableHeaderCell>번호</TableHeaderCell>
              <TableHeaderCell>단원</TableHeaderCell>
              <TableHeaderCell>세부 유형</TableHeaderCell>
              <TableHeaderCell>난이도</TableHeaderCell>
              <TableHeaderCell>배점</TableHeaderCell>
              <TableHeaderCell>판단 근거</TableHeaderCell>
              <TableHeaderCell />
            </TableRow>
          </TableHead>
          <TableBody>
            {questions.data?.map((question) => (
              <TableRow key={question.no}>
                <TableCell className="tabular-nums">{question.no}</TableCell>
                <TableCell className="whitespace-nowrap">{question.unit ?? '—'}</TableCell>
                <TableCell className="text-muted-fg">{question.sub_type ?? '—'}</TableCell>
                <TableCell>{LEVEL_LABEL[question.difficulty ?? ''] ?? '—'}</TableCell>
                <TableCell className="tabular-nums">{question.points ?? ''}</TableCell>
                <TableCell className="min-w-64 text-muted-fg">
                  {question.rationale ?? '분석하지 못했습니다'}
                  {question.needs_review && (
                    <span className="ml-2 rounded bg-warning px-1.5 py-0.5 text-xs font-medium whitespace-nowrap text-warning-fg">
                      확인 필요
                    </span>
                  )}
                </TableCell>
                <TableCell className="text-right whitespace-nowrap">
                  {question.needs_review && (
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="mr-1"
                      onClick={() => save.mutate({ no: question.no })}
                    >
                      확인
                    </Button>
                  )}
                  <Button type="button" size="sm" variant="ghost" onClick={() => setEditing(question)}>
                    수정
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {save.isError && (
          <p role="alert" className="px-5 py-3 text-sm text-danger">
            {save.error.message}
          </p>
        )}
      </CardContent>
      {editing && (
        <QuestionDialog question={editing} onSave={(patch) => save.mutate(patch)} onClose={() => setEditing(null)} />
      )}
    </Card>
  )
}

export function ExamsPage() {
  const exams = useQuery({ queryKey: ['exams'], queryFn: fetchExams })
  const [selected, setSelected] = useState<number | null>(null)
  const activeId = selected ?? exams.data?.[0]?.id ?? null
  const exam = useQuery({
    queryKey: ['exam', activeId],
    queryFn: () => fetchExam(activeId!),
    enabled: activeId !== null,
  })

  return (
    <section className="mb-8">
      <PageHeader title="시험지 · 오답 분석" />

      <Register onRegistered={setSelected} />

      {exams.data && exams.data.length > 0 && (
        <Card className="mb-5">
          <CardHeader>
            <CardTitle>최근 등록한 시험지</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {exams.data.map((row) => (
              <button
                key={row.id}
                type="button"
                aria-pressed={row.id === activeId}
                onClick={() => setSelected(row.id)}
                className={[
                  'rounded-md border px-4 py-3 text-left transition-colors hover:bg-accent',
                  'outline-none focus-visible:outline-2 focus-visible:outline-ring',
                  row.id === activeId ? 'border-brand' : '',
                ].join(' ')}
              >
                <div className="text-sm font-medium">{row.name}</div>
                <div className="mt-1 text-xs text-muted-fg">
                  {[row.exam_date, status(row)].filter(Boolean).join(' · ')}
                </div>
              </button>
            ))}
          </CardContent>
        </Card>
      )}

      {exam.data && (
        <>
          <ExamInfo key={`${exam.data.id}-${exam.data.status}`} exam={exam.data} />
          <DifficultyTable exam={exam.data} />
          <QuestionTable examId={exam.data.id} />
          <OmrSection examId={exam.data.id} />
        </>
      )}
    </section>
  )
}
