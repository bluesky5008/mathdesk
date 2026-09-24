import { NavLink, Outlet } from 'react-router'

const TABS = [
  { to: '/students', label: '학생' },
  { to: '/students/classes', label: '반' },
]

/** 학생/반 관리의 하위 탭. 탭마다 주소가 있어 새로 고침·뒤로 가기에도 탭이 유지된다. */
export function ManageTabs() {
  return (
    <>
      <nav aria-label="학생/반 관리" className="mb-5 flex gap-1 border-b">
        {TABS.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            end
            className={({ isActive }) =>
              [
                '-mb-px border-b-2 px-3 py-2 text-sm outline-none focus-visible:outline-2 focus-visible:outline-ring',
                isActive ? 'border-brand font-medium text-fg' : 'border-transparent text-muted-fg hover:text-fg',
              ].join(' ')
            }
          >
            {label}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </>
  )
}
