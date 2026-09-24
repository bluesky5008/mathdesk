import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'

import { Button } from '../components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
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
  createUser,
  fetchUsers,
  resetUserPassword,
  updateUser,
  type AppUserAccount,
} from '../api'

const ROLES = { director: '원장', teacher: '강사' } as const

const NEW_ACCOUNT = { login_id: '', display_name: '', role: 'teacher', password: '' }

type Edit = { id: number; display_name: string; role: string; is_active: boolean }

function RoleSelect({ id, value, onChange }: { id: string; value: string; onChange: (role: string) => void }) {
  return (
    <Select id={id} className="w-full" value={value} onChange={(event) => onChange(event.target.value)}>
      {Object.entries(ROLES).map(([role, label]) => (
        <option key={role} value={role}>
          {label}
        </option>
      ))}
    </Select>
  )
}

function DialogButtons({ submitLabel, pending }: { submitLabel: string; pending: boolean }) {
  return (
    <div className="mt-2 flex justify-end gap-2">
      <DialogClose asChild>
        <Button type="button" variant="outline">
          취소
        </Button>
      </DialogClose>
      <Button type="submit" disabled={pending}>
        {submitLabel}
      </Button>
    </div>
  )
}

function ErrorLine({ error }: { error: Error | null }) {
  return error ? (
    <p role="alert" className="text-sm text-danger">
      {error.message}
    </p>
  ) : null
}

// FR-02 — 원장이 같은 캠퍼스의 계정을 만들고 고치고 비밀번호를 재설정한다(DCR-009)
export function AccountsSection({ currentUserId }: { currentUserId: number }) {
  const queryClient = useQueryClient()
  const users = useQuery({ queryKey: ['users'], queryFn: fetchUsers })
  const [adding, setAdding] = useState<typeof NEW_ACCOUNT | null>(null)
  const [edit, setEdit] = useState<Edit | null>(null)
  const [resetting, setResetting] = useState<{ user: AppUserAccount; password: string } | null>(null)
  const [notice, setNotice] = useState('')

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['users'] })

  const create = useMutation({
    mutationFn: createUser,
    onSuccess: (user) => {
      setAdding(null)
      setNotice(`${user.display_name} 계정을 만들었습니다. 첫 로그인에서 새 비밀번호를 정하게 됩니다.`)
      void refresh()
    },
  })

  const save = useMutation({
    mutationFn: ({ id, ...payload }: Edit) => updateUser(id, payload),
    onSuccess: () => {
      setEdit(null)
      void refresh()
    },
  })

  const reset = useMutation({
    mutationFn: ({ user, password }: { user: AppUserAccount; password: string }) =>
      resetUserPassword(user.id, password),
    onSuccess: (_, { user }) => {
      setResetting(null)
      setNotice(`${user.display_name}의 비밀번호를 재설정했습니다. 임시 비밀번호를 본인에게 전해 주세요.`)
    },
  })

  function submitNew(event: FormEvent) {
    event.preventDefault()
    if (adding) create.mutate(adding)
  }

  function submitEdit(event: FormEvent) {
    event.preventDefault()
    if (edit) save.mutate(edit)
  }

  function submitReset(event: FormEvent) {
    event.preventDefault()
    if (resetting) reset.mutate(resetting)
  }

  return (
    <Card className="mt-5 max-w-3xl">
      <CardHeader className="flex flex-row items-start justify-between gap-3 pb-4">
        <div>
          <CardTitle>계정 관리</CardTitle>
          <CardDescription>
            강사 계정을 만들고 역할·사용 여부를 바꿉니다. 원장이 정한 비밀번호는 첫 로그인에서 본인이
            새로 정합니다.
          </CardDescription>
        </div>
        <Button
          type="button"
          size="sm"
          onClick={() => {
            create.reset()
            setAdding(NEW_ACCOUNT)
          }}
        >
          계정 추가
        </Button>
      </CardHeader>
      <CardContent className="p-0">
        {notice && (
          <p role="status" className="border-b px-5 py-3 text-sm text-success">
            {notice}
          </p>
        )}
        <Table>
          <TableHead>
            <TableRow>
              <TableHeaderCell>이름</TableHeaderCell>
              <TableHeaderCell>아이디</TableHeaderCell>
              <TableHeaderCell>역할</TableHeaderCell>
              <TableHeaderCell>상태</TableHeaderCell>
              <TableHeaderCell />
            </TableRow>
          </TableHead>
          <TableBody>
            {(users.data ?? []).map((user) => (
              <TableRow key={user.id}>
                <TableCell className="font-medium whitespace-nowrap">{user.display_name}</TableCell>
                <TableCell className="text-muted-fg">{user.login_id}</TableCell>
                <TableCell className="whitespace-nowrap">{ROLES[user.role as keyof typeof ROLES] ?? user.role}</TableCell>
                <TableCell className="whitespace-nowrap text-muted-fg">{user.is_active ? '사용' : '사용 안 함'}</TableCell>
                <TableCell className="text-right whitespace-nowrap">
                  {/* 본인 비밀번호는 상단의 [비밀번호 변경]으로 바꾼다 — 서버도 본인 재설정을 거부한다 */}
                  {user.id !== currentUserId && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="mr-1"
                      aria-label={`${user.display_name} 비밀번호 재설정`}
                      onClick={() => {
                        reset.reset()
                        setResetting({ user, password: '' })
                      }}
                    >
                      비밀번호 재설정
                    </Button>
                  )}
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    aria-label={`${user.display_name} 수정`}
                    onClick={() => {
                      save.reset()
                      setEdit({
                        id: user.id,
                        display_name: user.display_name,
                        role: user.role,
                        is_active: user.is_active,
                      })
                    }}
                  >
                    수정
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>

      <Dialog open={adding !== null} onOpenChange={(open) => !open && setAdding(null)}>
        <DialogContent>
          <DialogTitle className="mb-4 text-base font-semibold">계정 추가</DialogTitle>
          {adding && (
            <form className="flex flex-col gap-3" onSubmit={submitNew}>
              <Field label="아이디" htmlFor="account-login">
                <Input
                  id="account-login"
                  autoComplete="off"
                  value={adding.login_id}
                  onChange={(event) => setAdding({ ...adding, login_id: event.target.value })}
                />
              </Field>
              <Field label="이름" htmlFor="account-name">
                <Input
                  id="account-name"
                  value={adding.display_name}
                  onChange={(event) => setAdding({ ...adding, display_name: event.target.value })}
                />
              </Field>
              <Field label="역할" htmlFor="account-role">
                <RoleSelect
                  id="account-role"
                  value={adding.role}
                  onChange={(role) => setAdding({ ...adding, role })}
                />
              </Field>
              <Field label="임시 비밀번호" htmlFor="account-password">
                <Input
                  id="account-password"
                  type="password"
                  autoComplete="new-password"
                  minLength={8}
                  value={adding.password}
                  onChange={(event) => setAdding({ ...adding, password: event.target.value })}
                />
              </Field>
              <ErrorLine error={create.error} />
              <DialogButtons submitLabel="저장" pending={create.isPending} />
            </form>
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={edit !== null} onOpenChange={(open) => !open && setEdit(null)}>
        <DialogContent>
          <DialogTitle className="mb-4 text-base font-semibold">계정 수정</DialogTitle>
          {edit && (
            <form className="flex flex-col gap-3" onSubmit={submitEdit}>
              <Field label="이름" htmlFor="edit-account-name">
                <Input
                  id="edit-account-name"
                  value={edit.display_name}
                  onChange={(event) => setEdit({ ...edit, display_name: event.target.value })}
                />
              </Field>
              <Field label="역할" htmlFor="edit-account-role">
                <RoleSelect
                  id="edit-account-role"
                  value={edit.role}
                  onChange={(role) => setEdit({ ...edit, role })}
                />
              </Field>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={edit.is_active}
                  onChange={(event) => setEdit({ ...edit, is_active: event.target.checked })}
                />
                사용
              </label>
              <p className="text-xs text-muted-fg">
                사용을 끄면 그 계정으로 로그인할 수 없습니다. 기록은 그대로 남습니다.
              </p>
              <ErrorLine error={save.error} />
              <DialogButtons submitLabel="저장" pending={save.isPending} />
            </form>
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={resetting !== null} onOpenChange={(open) => !open && setResetting(null)}>
        <DialogContent>
          <DialogTitle className="mb-2 text-base font-semibold">
            {resetting?.user.display_name} 비밀번호 재설정
          </DialogTitle>
          {resetting && (
            <form className="flex flex-col gap-3" onSubmit={submitReset}>
              <p className="text-sm text-muted-fg">
                재설정하면 이 계정의 기존 로그인은 모두 끊기고, 임시 비밀번호로 로그인한 뒤 본인이 새
                비밀번호를 정해야 합니다.
              </p>
              <Field label="임시 비밀번호" htmlFor="reset-password">
                <Input
                  id="reset-password"
                  type="password"
                  autoComplete="new-password"
                  minLength={8}
                  value={resetting.password}
                  onChange={(event) => setResetting({ ...resetting, password: event.target.value })}
                />
              </Field>
              <ErrorLine error={reset.error} />
              <DialogButtons submitLabel="재설정" pending={reset.isPending} />
            </form>
          )}
        </DialogContent>
      </Dialog>
    </Card>
  )
}
