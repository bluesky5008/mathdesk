import { useQuery } from '@tanstack/react-query'
import { createContext, useContext, useState } from 'react'
import { NavLink, Navigate, Route, Routes } from 'react-router'

import { fetchPortalStudents, type CurrentUser, type PortalStudent } from '../api'
import { PasswordChangeForm } from '../PasswordChange'
import { ThemeSelect } from '../components/ThemeSelect'
import { Button } from '../components/ui/button'
import { Dialog, DialogContent, DialogTitle } from '../components/ui/dialog'
import { Select } from '../components/ui/select'
import { ConsultsPage, ExamsPage, HomePage, MessagesPage, RecordsPage, TestsPage } from './pages'

/** 포털 셸을 보는 역할(ADR-014). 서버도 이 역할에는 포털 API만 연다 */
export const PORTAL_ROLES = ['student', 'guardian']

const TABS = [
  { to: '/portal', label: '홈' },
  { to: '/portal/records', label: '기록' },
  { to: '/portal/tests', label: '추이' },
  { to: '/portal/exams', label: '시험' },
  { to: '/portal/consults', label: '상담' },
  { to: '/portal/messages', label: '문자' },
]

const StudentContext = createContext<PortalStudent | null>(null)

/** 지금 보고 있는 학생(학부모는 고른 자녀). 포털 페이지는 이 값으로 조회한다 */
export function usePortalStudent(): PortalStudent {
  const student = useContext(StudentContext)
  if (!student) throw new Error('포털 학생이 없습니다')
  return student
}

/**
 * 학생·학부모 전용 셸(FR-49 상세, DCR-024). 원장·강사 메뉴는 없다.
 * 휴대폰 우선이라 탭을 아래에 고정하고 본문은 한 열이다(NFR-14 조회 부류).
 */
export function PortalApp({ user, onLogout }: { user: CurrentUser; onLogout: () => void }) {
  const students = useQuery({ queryKey: ['portal-students'], queryFn: fetchPortalStudents })
  const [selected, setSelected] = useState<number | null>(null)
  const [changing, setChanging] = useState(false)
  const list = students.data ?? []
  const student = list.find((s) => s.id === selected) ?? list[0] ?? null

  return (
    <div className="min-h-screen bg-bg pb-20">
      <header className="sticky top-0 z-10 border-b bg-surface">
        <div className="mx-auto flex h-14 max-w-lg items-center gap-3 px-4">
          <span className="shrink-0 text-base font-semibold tracking-tight text-brand">mathdesk</span>
          {list.length > 1 && (
            <Select
              aria-label="자녀"
              className="h-8 text-xs"
              value={student?.id ?? ''}
              onChange={(event) => setSelected(Number(event.target.value))}
            >
              {list.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </Select>
          )}
          <div className="ml-auto flex shrink-0 items-center gap-2">
            <ThemeSelect />
            <Button type="button" variant="ghost" size="sm" onClick={() => setChanging(true)}>
              비밀번호
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={onLogout}>
              로그아웃
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-lg px-4 py-4">
        {students.isError && (
          <p role="alert" className="text-sm text-danger">
            {students.error.message}
          </p>
        )}
        {students.isSuccess && !student && (
          <p className="text-sm text-muted-fg">연결된 학생이 없습니다. 학원에 문의해 주세요.</p>
        )}
        {student && (
          <StudentContext.Provider value={student}>
            <Routes>
              <Route path="/portal" element={<HomePage />} />
              <Route path="/portal/records" element={<RecordsPage />} />
              <Route path="/portal/tests" element={<TestsPage />} />
              <Route path="/portal/exams" element={<ExamsPage />} />
              <Route path="/portal/consults" element={<ConsultsPage />} />
              <Route path="/portal/messages" element={<MessagesPage />} />
              <Route path="*" element={<Navigate to="/portal" replace />} />
            </Routes>
          </StudentContext.Provider>
        )}
      </main>

      <nav aria-label="포털 메뉴" className="fixed inset-x-0 bottom-0 z-10 border-t bg-surface">
        <div className="mx-auto grid max-w-lg grid-cols-6">
          {TABS.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/portal'}
              className={({ isActive }) =>
                [
                  'flex h-14 items-center justify-center text-sm outline-none focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring',
                  isActive ? 'font-semibold text-brand' : 'text-muted-fg',
                ].join(' ')
              }
            >
              {label}
            </NavLink>
          ))}
        </div>
      </nav>

      <Dialog open={changing} onOpenChange={setChanging}>
        <DialogContent className="max-w-sm">
          <DialogTitle className="mb-4 text-base font-semibold">비밀번호 변경</DialogTitle>
          <p className="mb-3 text-xs text-muted-fg">{user.display_name}</p>
          <PasswordChangeForm onDone={() => setChanging(false)} />
        </DialogContent>
      </Dialog>
    </div>
  )
}
