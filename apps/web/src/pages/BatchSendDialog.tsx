import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import { Button } from '../components/ui/button'
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogTitle } from '../components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from '../components/ui/table'
import { fetchTask, previewBatch, startBatch, type BatchStudentResult } from '../api'

const SKIP_REASON: Record<string, string> = { no_recipient: '연락처 없음', already_sent: '이미 보냄' }
const RESULT_LABEL: Record<string, string> = { sent: '접수', failed: '실패', test: '테스트', skipped: '건너뜀' }
const RECIPIENT_LABEL: Record<string, string> = { student: '학생', guardian: '학부모' }

/**
 * 반 단위 일괄 발송(FR-47). 확인 → 작업 등록 → 진행률 폴링 → 학생별 결과·실패만 다시 보내기.
 * 수신 대상·알림톡 템플릿은 발송 카드에서 고른 값을 그대로 쓴다.
 */
export function BatchSendDialog({
  sessionId,
  recipients,
  templateCode,
  onClose,
  onFinished,
}: {
  sessionId: number
  recipients: string[]
  templateCode?: string
  onClose: () => void
  onFinished: () => void
}) {
  const [includeSent, setIncludeSent] = useState(false)
  const [taskId, setTaskId] = useState<number | null>(null)

  const plan = useQuery({
    queryKey: ['batch-preview', sessionId, recipients, includeSent],
    queryFn: () => previewBatch(sessionId, recipients, includeSent),
    enabled: taskId === null,
  })
  const start = useMutation({
    mutationFn: (studentIds?: number[]) => startBatch(sessionId, recipients, includeSent, templateCode, studentIds),
    onSuccess: (started) => setTaskId(started.task_id),
  })
  const task = useQuery({
    queryKey: ['task', taskId],
    queryFn: () => fetchTask(taskId!),
    enabled: taskId !== null,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (status === 'done' || status === 'failed') {
        onFinished()
        return false
      }
      return 1500
    },
  })

  const result = task.data?.result as
    | { sent: number; failed: number; test: number; skipped: number; students: BatchStudentResult[] }
    | null
    | undefined
  const students = result?.students ?? []
  const failedIds = students.filter((s) => s.status === 'failed').map((s) => s.student_id)
  const finished = task.data?.status === 'done' || task.data?.status === 'failed'

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[90vh] max-w-xl overflow-y-auto">
        <DialogTitle className="mb-1 text-base font-semibold">반 전체 발송</DialogTitle>
        <DialogDescription className="mb-4 text-sm text-muted-fg">
          받을 대상: {recipients.map((kind) => RECIPIENT_LABEL[kind] ?? kind).join('·')} ·{' '}
          {templateCode ? `알림톡 ${templateCode}` : '문자'}. 본문은 학생마다 따로 만들어집니다.
        </DialogDescription>

        {taskId === null ? (
          <div className="flex flex-col gap-4">
            {plan.data && (
              <>
                <p className="text-sm">
                  <strong>대상 {plan.data.planned.length}명</strong>
                  {plan.data.skipped.length > 0 && (
                    <span className="text-muted-fg">{` · 제외 ${plan.data.skipped.length}명`}</span>
                  )}
                </p>
                {plan.data.skipped.length > 0 && (
                  <ul className="flex flex-col gap-1 text-sm text-muted-fg">
                    {plan.data.skipped.map((item) => (
                      <li key={item.student_id}>
                        {item.name} — {SKIP_REASON[item.reason] ?? item.reason}
                      </li>
                    ))}
                  </ul>
                )}
                <label htmlFor="batch-include-sent" className="flex items-center gap-2 text-sm">
                  <input
                    id="batch-include-sent"
                    type="checkbox"
                    className="size-4 accent-brand"
                    checked={includeSent}
                    onChange={(event) => setIncludeSent(event.target.checked)}
                  />
                  이미 보낸 학생도 포함
                </label>
              </>
            )}
            {plan.isError && (
              <p role="alert" className="text-sm text-danger">
                {plan.error.message}
              </p>
            )}
            {start.isError && (
              <p role="alert" className="text-sm text-danger">
                {start.error.message}
              </p>
            )}
            <div className="flex justify-end gap-2">
              <DialogClose asChild>
                <Button type="button" variant="outline">
                  닫기
                </Button>
              </DialogClose>
              <Button
                type="button"
                onClick={() => start.mutate(undefined)}
                disabled={!plan.data || plan.data.planned.length === 0 || start.isPending}
              >
                {`${plan.data?.planned.length ?? 0}명에게 보내기`}
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            <p className="text-sm" role="status">
              {finished
                ? `완료 — 접수 ${result?.sent ?? 0} · 실패 ${result?.failed ?? 0} · 테스트 ${result?.test ?? 0} · 건너뜀 ${result?.skipped ?? 0}`
                : `보내는 중 ${task.data?.progress ?? 0}%`}
            </p>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-accent">
              <div className="h-full bg-brand transition-all" style={{ width: `${task.data?.progress ?? 0}%` }} />
            </div>
            {task.data?.error && (
              <p role="alert" className="text-sm text-danger">
                {task.data.error}
              </p>
            )}
            {students.length > 0 && (
              <Table>
                <TableHead>
                  <TableRow>
                    <TableHeaderCell>학생</TableHeaderCell>
                    <TableHeaderCell>상태</TableHeaderCell>
                    <TableHeaderCell>사유</TableHeaderCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {students.map((student) => (
                    <TableRow key={student.student_id}>
                      <TableCell>{student.name}</TableCell>
                      <TableCell className={student.status === 'failed' ? 'text-danger' : undefined}>
                        {RESULT_LABEL[student.status] ?? student.status}
                      </TableCell>
                      <TableCell className="text-muted-fg">{student.error}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
            <div className="flex justify-end gap-2">
              <DialogClose asChild>
                <Button type="button" variant="outline">
                  닫기
                </Button>
              </DialogClose>
              {finished && failedIds.length > 0 && (
                <Button type="button" onClick={() => start.mutate(failedIds)} disabled={start.isPending}>
                  실패만 다시 보내기
                </Button>
              )}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
