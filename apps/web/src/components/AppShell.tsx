import type { ReactNode } from 'react'
import { NavLink } from 'react-router'

import { ThemeSelect } from './ThemeSelect'
import { Button } from './ui/button'

const NAV = [
  { to: '/', label: '종합 대시보드' },
  { to: '/daily', label: '일일 수업 & 성적 입력' },
  { to: '/students', label: '학생/반 관리' },
  { to: '/stats', label: '성적 통계' },
  { to: '/messages', label: '알림문자' },
  { to: '/settings', label: '학원 설정' },
]

export function AppShell({
  userName,
  userRole,
  onLogout,
  children,
}: {
  userName: string
  userRole: string
  onLogout: () => void
  children: ReactNode
}) {
  return (
    <div className="min-h-screen bg-bg">
      <header className="sticky top-0 z-10 border-b bg-surface">
        {/* 화면이 좁아도 메뉴가 한 줄을 유지한다. 폭이 모자라면 줄을 접지 않고 가로로 스크롤한다 */}
        <div className="mx-auto flex h-14 max-w-[1440px] items-center gap-8 overflow-x-auto px-6">
          <span className="shrink-0 text-lg font-semibold tracking-tight text-brand">mathdesk</span>

          <nav className="flex shrink-0 items-center gap-1">
            {NAV.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  [
                    'rounded-md px-3 py-1.5 text-sm whitespace-nowrap transition-colors',
                    'outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring',
                    isActive
                      ? 'bg-accent font-medium text-fg'
                      : 'text-muted-fg hover:bg-accent hover:text-fg',
                  ].join(' ')
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>

          <div className="ml-auto flex shrink-0 items-center gap-3">
            <ThemeSelect />
            <span className="text-sm whitespace-nowrap text-muted-fg">
              {userName} ({userRole})
            </span>
            <Button type="button" variant="outline" size="sm" onClick={onLogout}>
              로그아웃
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1440px] px-6 py-6">{children}</main>
    </div>
  )
}
