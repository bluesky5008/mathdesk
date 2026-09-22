import type { KeyboardEvent, ReactNode } from 'react'

const FOCUSABLE =
  'input:not([disabled]), textarea:not([disabled]), select:not([disabled]), button:not([disabled])'

/**
 * 표 기반 입력의 키보드 이동을 소유하는 공통 컴포넌트다(NFR-13).
 * 외부 UI 라이브러리의 동작에 맞추지 않고 저장소가 직접 규칙을 정한다.
 *
 * - ArrowDown/ArrowUp: 같은 열을 유지한 채 행을 옮긴다.
 * - Enter: 입력란에서만 다음 행으로 내려간다. 버튼에서 가로채면 키보드로 버튼을 누를 수 없다.
 * - 좌우 방향키는 다루지 않는다. 입력란 안의 커서 이동이 우선이고, 가로 이동은 Tab이 이미 한다.
 *
 * 열 기준을 포커스 가능한 요소의 순번이 아니라 `td`의 위치로 잡는 이유는,
 * 행마다 버튼 개수가 다를 수 있어(예: 재검사 대상만 합격/불합격 버튼) 순번이 어긋나기 때문이다.
 */
export function KeyboardGrid({ children }: { children: ReactNode }) {
  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const target = event.target as HTMLElement
    // select는 방향키가 옵션 선택에 쓰인다
    if (target instanceof HTMLSelectElement) return

    const down =
      event.key === 'ArrowDown' || (event.key === 'Enter' && target instanceof HTMLInputElement)
    const up = event.key === 'ArrowUp'
    if (!down && !up) return

    const cell = target.closest('td, th') as HTMLTableCellElement | null
    const row = cell?.closest('tr')
    if (!cell || !row) return

    const sibling = down ? row.nextElementSibling : row.previousElementSibling
    const next = (sibling as HTMLTableRowElement | null)?.cells[cell.cellIndex]?.querySelector<HTMLElement>(
      FOCUSABLE,
    )
    if (!next) return

    event.preventDefault()
    next.focus()
  }

  return <div onKeyDown={handleKeyDown}>{children}</div>
}
