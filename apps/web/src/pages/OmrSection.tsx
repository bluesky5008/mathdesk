import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState, type FormEvent } from 'react'

import { Button } from '../components/ui/button'
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
import {
  applyOmr,
  fetchOmrScans,
  fetchStudents,
  fetchTask,
  omrImageUrl,
  updateOmrScan,
  uploadOmr,
  type OmrApplyResult,
  type OmrFlag,
  type OmrScan,
  type OmrScanPatch,
} from '../api'

const QUESTIONS = Array.from({ length: 30 }, (_, i) => String(i + 1))
const CODE_LABEL = { blank: '무마킹', multi: '복수마킹', low_confidence: '저신뢰', unmatched: '매칭 실패' }
const STATUS_LABEL = { needs_review: '검수 필요', read: '판독 완료', applied: '반영됨' }
const FORM_LABEL = { odd: '홀수형', even: '짝수형' }

function fieldLabel(field: string): string {
  if (/^\d+$/.test(field)) return `${field}번`
  return { exam_number: '수험번호', form: '문형', student: '학생', sheet: '답안지' }[field] ?? field
}

function flagLabel(flag: OmrFlag): string {
  if (flag.field === 'sheet') return '답안지 인식 실패'
  return `${fieldLabel(flag.field)} ${CODE_LABEL[flag.code]}`
}

function Upload({ examId }: { examId: number }) {
  const queryClient = useQueryClient()
  const [file, setFile] = useState<File | null>(null)
  const [taskId, setTaskId] = useState<number | null>(null)

  const start = useMutation({
    mutationFn: () => uploadOmr(examId, file!),
    onSuccess: (started) => setTaskId(started.task_id),
  })
  // 판독은 배경 작업이다. 끝날 때까지 상태를 폴링한다(DES-18)
  const task = useQuery({
    queryKey: ['task', taskId],
    queryFn: () => fetchTask(taskId!),
    enabled: taskId !== null,
    refetchInterval: (query) =>
      ['done', 'failed'].includes(query.state.data?.status ?? '') ? false : 1000,
  })
  const taskStatus = task.data?.status
  useEffect(() => {
    if (taskStatus === 'done') void queryClient.invalidateQueries({ queryKey: ['omr-scans', examId] })
  }, [taskStatus, examId, queryClient])

  const result = task.data?.result as { pages: number; failed: number } | null | undefined
  const running = taskId !== null && !['done', 'failed'].includes(taskStatus ?? '')

  function submit(event: FormEvent) {
    event.preventDefault()
    if (file) start.mutate()
  }

  return (
    <div className="px-5 pt-2 pb-4">
      <form className="flex flex-wrap items-end gap-3" onSubmit={submit}>
        <Field label="OMR 스캔 파일" htmlFor="omr-file" className="min-w-48 flex-1">
          <Input
            id="omr-file"
            type="file"
            accept=".pdf,.png,.jpg,.jpeg"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
        </Field>
        <Button type="submit" disabled={!file || start.isPending || running}>
          업로드 후 판독
        </Button>
      </form>
      <p className="mt-2 text-xs text-muted-fg">PDF 한 개(최대 20MB·30쪽) 또는 이미지. 한 쪽에 답안지 한 장입니다.</p>
      {running && (
        <p role="status" className="mt-3 text-sm text-muted-fg">
          답안지를 판독하는 중입니다 · {task.data?.progress ?? 0}%
        </p>
      )}
      {taskStatus === 'done' && result && (
        <p role="status" className="mt-3 text-sm text-muted-fg">
          {result.pages}쪽을 판독했습니다.
          {result.failed > 0 && ` 인식하지 못한 쪽이 ${result.failed}개 있습니다.`}
        </p>
      )}
      {(start.isError || taskStatus === 'failed') && (
        <p role="alert" className="mt-3 text-sm text-danger">
          {start.error?.message ?? task.data?.error}
        </p>
      )}
    </div>
  )
}

function Crop({ examId, scanId, field }: { examId: number; scanId: number; field: string }) {
  return (
    <img
      src={omrImageUrl(examId, scanId, field)}
      alt={`${fieldLabel(field)} 원본`}
      // 단답형·수험번호 크롭은 세로로 길다. 칸의 숫자가 읽힐 만큼 높이를 준다
      className="max-h-80 max-w-full rounded border bg-white"
    />
  )
}

function ReviewDialog({ examId, scan, onClose }: { examId: number; scan: OmrScan; onClose: () => void }) {
  const queryClient = useQueryClient()
  const flagged = new Set(scan.flags.map((flag) => flag.field))
  const unreadable = scan.error !== null
  const unmatched = flagged.has('student')
  // 인식하지 못한 쪽은 30문항 전체를, 아니면 플래그가 붙은 문항만 묻는다
  const questions = unreadable ? QUESTIONS : QUESTIONS.filter((q) => flagged.has(q))
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(questions.map((q) => [q, String(scan.answers[q] ?? '')])),
  )
  const [form, setForm] = useState<string>(scan.form ?? '')
  const [examNumber, setExamNumber] = useState(scan.exam_number ?? '')
  const [studentId, setStudentId] = useState('')
  const students = useQuery({ queryKey: ['students'], queryFn: () => fetchStudents(), enabled: unmatched })

  const save = useMutation({
    mutationFn: (patch: OmrScanPatch) => updateOmrScan(examId, scan.id, patch),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['omr-scans', examId] })
      onClose()
    },
  })

  function submit(event: FormEvent) {
    event.preventDefault()
    const patch: OmrScanPatch = {}
    if (questions.length > 0) {
      // 비워 둔 칸은 무응답으로 확인한다. 판독값 그대로 보내면 그 값을 확인한 것이다
      patch.answers = Object.fromEntries(questions.map((q) => [q, values[q] === '' ? null : Number(values[q])]))
    }
    if ((unreadable || flagged.has('form')) && form) patch.form = form as 'odd' | 'even'
    if (flagged.has('exam_number') && examNumber) patch.exam_number = examNumber
    if (unmatched && studentId) patch.student_id = Number(studentId)
    save.mutate(patch)
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[90vh] max-w-2xl overflow-y-auto">
        <DialogTitle className="mb-4 text-base font-semibold">
          OMR 검수 · {scan.page_no}쪽 {scan.student?.name ?? '학생 미지정'}
        </DialogTitle>
        <form className="grid gap-4" onSubmit={submit}>
          {unreadable && (
            <div>
              <p className="mb-2 text-sm text-danger">
                답안지를 인식하지 못했습니다({scan.error}). 다시 스캔해 올리거나 문형과 30문항을 모두 입력해 주세요.
              </p>
              <img src={omrImageUrl(examId, scan.id)} alt="답안지 원본" className="w-full rounded border bg-white" />
            </div>
          )}

          {(unmatched || flagged.has('exam_number')) && (
            <div className="flex flex-wrap items-end gap-3">
              {!unreadable && <Crop examId={examId} scanId={scan.id} field="exam_number" />}
              <div className="grid flex-1 gap-3">
                {flagged.has('exam_number') && (
                  <Field label="수험번호" htmlFor="omr-exam-number">
                    <Input
                      id="omr-exam-number"
                      inputMode="numeric"
                      maxLength={8}
                      value={examNumber}
                      onChange={(event) => setExamNumber(event.target.value)}
                    />
                  </Field>
                )}
                {unmatched && (
                  <Field label="학생" htmlFor="omr-student">
                    <Select
                      id="omr-student"
                      className="w-full"
                      value={studentId}
                      onChange={(event) => setStudentId(event.target.value)}
                    >
                      <option value="">판독 번호 {scan.exam_number ?? '없음'} — 학생 선택</option>
                      {students.data?.map((student) => (
                        <option key={student.id} value={student.id}>
                          {student.name}
                          {student.omr_number ? ` (${student.omr_number})` : ''}
                        </option>
                      ))}
                    </Select>
                  </Field>
                )}
              </div>
            </div>
          )}

          {(unreadable || flagged.has('form')) && (
            <div className="flex flex-wrap items-end gap-3">
              {!unreadable && <Crop examId={examId} scanId={scan.id} field="form" />}
              <Field label="문형" htmlFor="omr-form">
                <Select id="omr-form" value={form} onChange={(event) => setForm(event.target.value)}>
                  <option value="">선택</option>
                  <option value="odd">홀수형</option>
                  <option value="even">짝수형</option>
                </Select>
              </Field>
            </div>
          )}

          {questions.length > 0 && (
            <div className={unreadable ? 'grid grid-cols-3 gap-2 sm:grid-cols-6' : 'grid gap-3'}>
              {questions.map((q) => (
                <div key={q} className="flex flex-wrap items-end gap-3">
                  {!unreadable && <Crop examId={examId} scanId={scan.id} field={q} />}
                  <Field label={`${q}번 답`} htmlFor={`omr-q-${q}`}>
                    <Input
                      id={`omr-q-${q}`}
                      inputMode="numeric"
                      className="w-20"
                      value={values[q]}
                      onChange={(event) => setValues({ ...values, [q]: event.target.value })}
                    />
                  </Field>
                </div>
              ))}
            </div>
          )}

          {save.isError && (
            <p role="alert" className="text-sm text-danger">
              {save.error.message}
            </p>
          )}
          <div className="flex justify-end gap-2">
            <DialogClose asChild>
              <Button type="button" variant="outline">
                취소
              </Button>
            </DialogClose>
            <Button type="submit" disabled={save.isPending}>
              검수 완료
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}

/** 시험 한 건의 OMR 업로드·판독 결과·검수(FR-32~FR-35). 채점 반영은 TASK-36에서 붙는다. */
export function OmrSection({ examId }: { examId: number }) {
  const scans = useQuery({ queryKey: ['omr-scans', examId], queryFn: () => fetchOmrScans(examId) })
  const [reviewing, setReviewing] = useState<OmrScan | null>(null)
  const waiting = scans.data?.filter((scan) => scan.status === 'needs_review').length ?? 0
  const queryClient = useQueryClient()
  const [applied, setApplied] = useState<OmrApplyResult | null>(null)
  const apply = useMutation({
    mutationFn: () => applyOmr(examId),
    onSuccess: (result) => {
      setApplied(result)
      for (const key of ['omr-scans', 'exam-results', 'question-stats']) {
        void queryClient.invalidateQueries({ queryKey: [key, examId] })
      }
    },
  })

  return (
    <Card className="mt-5">
      <CardHeader>
        <CardTitle>OMR 채점</CardTitle>
        <p className="mt-1 text-xs text-muted-fg">
          표시된 항목은 원본과 대조해 확인해 주세요. 검수를 마치기 전에는 채점에 반영하지 않습니다.
        </p>
      </CardHeader>
      <Upload examId={examId} />
      {scans.data && scans.data.length > 0 && (
        <CardContent className="p-0">
          <div className="flex flex-wrap items-center justify-between gap-2 px-5 pb-2">
            <p className="text-sm font-medium">
              검수 대기 {waiting} / 전체 {scans.data.length}
            </p>
            {/* 검수를 마친 답안지만 반영한다. 다시 누르면 현재 상태로 다시 계산한다 */}
            <Button type="button" size="sm" disabled={apply.isPending} onClick={() => apply.mutate()}>
              채점 반영
            </Button>
          </div>
          {applied && (
            <p role="status" className="px-5 pb-2 text-sm text-muted-fg">
              {applied.applied}명을 반영했습니다.
              {applied.waiting > 0 && ` 검수 대기 ${applied.waiting}장은 제외했습니다.`}
            </p>
          )}
          {(applied?.conflicts.length ?? 0) > 0 && (
            <p role="alert" className="px-5 pb-2 text-sm text-danger">
              {applied!.conflicts
                .map((c) => `${c.student.name}: ${c.pages.join('·')}쪽이 같은 학생으로 매칭되어 보류했습니다`)
                .join(' / ')}
              . 검수에서 학생을 바로잡은 뒤 다시 반영해 주세요.
            </p>
          )}
          {apply.isError && (
            <p role="alert" className="px-5 pb-2 text-sm text-danger">
              {apply.error.message}
            </p>
          )}
          <Table aria-label="OMR 스캔">
            <TableHead>
              <TableRow>
                <TableHeaderCell>쪽</TableHeaderCell>
                <TableHeaderCell>수험번호</TableHeaderCell>
                <TableHeaderCell>학생</TableHeaderCell>
                <TableHeaderCell>문형</TableHeaderCell>
                <TableHeaderCell>상태</TableHeaderCell>
                <TableHeaderCell>확인할 항목</TableHeaderCell>
                <TableHeaderCell />
              </TableRow>
            </TableHead>
            <TableBody>
              {scans.data.map((scan) => (
                <TableRow key={scan.id}>
                  <TableCell className="tabular-nums">{scan.page_no}</TableCell>
                  <TableCell className="tabular-nums">{scan.exam_number ?? '—'}</TableCell>
                  <TableCell className="whitespace-nowrap">{scan.student?.name ?? '—'}</TableCell>
                  <TableCell className="whitespace-nowrap">{scan.form ? FORM_LABEL[scan.form] : '—'}</TableCell>
                  <TableCell className="whitespace-nowrap">
                    {scan.status === 'needs_review' ? (
                      <span className="rounded bg-warning px-1.5 py-0.5 text-xs font-medium text-warning-fg">
                        {STATUS_LABEL[scan.status]}
                      </span>
                    ) : (
                      STATUS_LABEL[scan.status]
                    )}
                  </TableCell>
                  <TableCell className="min-w-48 text-muted-fg">
                    <ul className="flex flex-wrap gap-x-3">
                      {scan.flags.map((flag) => (
                        <li key={flag.field}>{flagLabel(flag)}</li>
                      ))}
                    </ul>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button type="button" size="sm" variant="outline" onClick={() => setReviewing(scan)}>
                      검수
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      )}
      {reviewing && <ReviewDialog examId={examId} scan={reviewing} onClose={() => setReviewing(null)} />}
    </Card>
  )
}
