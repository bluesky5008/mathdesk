import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { Button } from '../components/ui/button'
import {
  fetchPortalAccounts,
  issuePortalAccount,
  reissuePortalAccount,
  type ExistingAccount,
  type IssuedAccount,
  type PortalAccount,
  type PortalState,
} from '../api'

export const PORTAL_STATE: Record<PortalState, string> = {
  none: '미발급',
  pending: '변경 대기',
  active: '사용 중',
  expired: '만료',
  inactive: '비활성',
}

function describe(kind: 'student' | 'guardian', issued: IssuedAccount): string {
  const who = kind === 'student' ? '학생' : '학부모'
  if (issued.linked) return `기존 학부모 계정(${issued.login_id})에 연결했습니다. 형제가 같은 계정으로 봅니다.`
  return `${who} 아이디·초기 비밀번호: ${issued.login_id} — 7일 안에 로그인해 비밀번호를 바꿔야 합니다.`
}

function AccountRow({
  studentId,
  kind,
  account,
  phone,
  isDirector,
  existing,
}: {
  studentId: number
  kind: 'student' | 'guardian'
  account: PortalAccount
  phone: string | null
  isDirector: boolean
  existing?: ExistingAccount | null
}) {
  const queryClient = useQueryClient()
  const [notice, setNotice] = useState('')
  const [confirming, setConfirming] = useState(false)
  const label = kind === 'student' ? '학생 계정' : '학부모 계정'
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['portal-accounts', studentId] })
    void queryClient.invalidateQueries({ queryKey: ['students'] })
  }
  const issue = useMutation({
    mutationFn: (confirmLink: boolean) => issuePortalAccount(studentId, kind, confirmLink),
    onSuccess: (issued) => {
      setConfirming(false)
      setNotice(describe(kind, issued))
      refresh()
    },
  })
  // 기존 학부모 계정에 연결하는 경우는 이름을 보고 확인한 뒤에만 보낸다(DCR-026)
  const start = () => (existing ? setConfirming(true) : issue.mutate(false))
  const reissue = useMutation({
    mutationFn: () => reissuePortalAccount(studentId, account.user_id!),
    onSuccess: () => {
      setNotice(`${label}을 재발급했습니다. 아이디·초기 비밀번호: ${account.login_id} — 기존 로그인은 모두 끊겼습니다.`)
      refresh()
    },
  })
  const issued = account.state !== 'none'
  const error = issue.error ?? reissue.error
  return (
    <div className="flex flex-col gap-1">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium">{label}</span>
        <span className="text-sm text-muted-fg">
          {PORTAL_STATE[account.state]}
          {account.login_id && ` · ${account.login_id}`}
        </span>
        {isDirector && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="ml-auto"
            disabled={!phone || issue.isPending || reissue.isPending}
            onClick={() => (issued ? reissue.mutate() : start())}
          >
            {issued ? `${label} 재발급` : `${label} 발급`}
          </Button>
        )}
      </div>
      {isDirector && !phone && (
        <p className="text-xs text-muted-fg">{kind === 'student' ? '학생 연락처를 먼저 등록하세요.' : '학부모 연락처를 먼저 등록하세요.'}</p>
      )}
      {existing && !confirming && (
        <p className="text-xs break-keep text-warning-fg">
          {`이 번호는 ${existing.students.join('·')} 학생의 학부모 계정과 같습니다.`}
        </p>
      )}
      {existing && confirming && (
        <div
          role="alertdialog"
          aria-label="형제 연결 확인"
          className="flex flex-col gap-2 rounded-md border border-warning bg-warning/20 px-3 py-2"
        >
          <p className="text-sm break-keep">
            {`${existing.students.join('·')} 학생의 학부모 계정(${existing.login_id})에 이 학생을 연결합니다. 번호가 맞고 형제가 맞습니까?`}
          </p>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" size="sm" onClick={() => setConfirming(false)}>
              취소
            </Button>
            <Button type="button" size="sm" disabled={issue.isPending} onClick={() => issue.mutate(true)}>
              형제가 맞습니다, 연결
            </Button>
          </div>
        </div>
      )}
      {notice && (
        <p role="status" className="text-xs break-keep text-success">
          {notice}
        </p>
      )}
      {error && (
        <p role="alert" className="text-xs text-danger">
          {error.message}
        </p>
      )}
    </div>
  )
}

/**
 * 학생 [수정] 창의 포털 계정 구획(FR-48 상세, DCR-024). 원장은 발급·재발급하고 강사는 상태만 본다.
 * 연락처는 저장된 값 기준이다 — 수정 창에서 고친 번호는 저장한 뒤에야 발급할 수 있다.
 */
export function PortalAccountsSection({
  studentId,
  phone,
  guardianPhone,
  isDirector,
}: {
  studentId: number
  phone: string | null
  guardianPhone: string | null
  isDirector: boolean
}) {
  const accounts = useQuery({ queryKey: ['portal-accounts', studentId], queryFn: () => fetchPortalAccounts(studentId) })
  // 다른 화면 테스트의 가짜 응답처럼 모양이 다르면 구획을 그리지 않는다
  if (!accounts.data?.student) return null
  const guardian = accounts.data.guardians[0] ?? { state: 'none' as const, login_id: null, user_id: null }
  return (
    <section aria-label="포털 계정" className="col-span-2 flex flex-col gap-2 rounded-md border px-3 py-2">
      <AccountRow studentId={studentId} kind="student" account={accounts.data.student} phone={phone} isDirector={isDirector} />
      <AccountRow
        studentId={studentId}
        kind="guardian"
        account={guardian}
        phone={guardianPhone}
        isDirector={isDirector}
        existing={accounts.data.guardians[0]?.existing ?? null}
      />
    </section>
  )
}
