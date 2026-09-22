import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it } from 'vitest'

import { KeyboardGrid } from './keyboard-grid'
import { Table, TableBody, TableCell, TableRow } from './table'

// NFR-13: 일일 입력 화면은 마우스 이동을 최소화하는 키보드 이동을 지원해야 하며,
// 그 동작은 저장소가 소유하는 공통 컴포넌트가 구현한다.

function Grid() {
  return (
    <KeyboardGrid>
      <Table>
        <TableBody>
          {[1, 2, 3].map((row) => (
            <TableRow key={row}>
              <TableCell>
                <button type="button">{`${row}행 버튼`}</button>
              </TableCell>
              <TableCell>
                <input aria-label={`${row}행 점수`} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </KeyboardGrid>
  )
}

it('같은 열을 유지한 채 아래위 행으로 포커스를 옮긴다', async () => {
  const user = userEvent.setup()
  render(<Grid />)

  await user.click(screen.getByLabelText('1행 점수'))
  await user.keyboard('{ArrowDown}')
  expect(screen.getByLabelText('2행 점수')).toHaveFocus()

  await user.keyboard('{ArrowDown}')
  expect(screen.getByLabelText('3행 점수')).toHaveFocus()

  await user.keyboard('{ArrowUp}')
  expect(screen.getByLabelText('2행 점수')).toHaveFocus()
})

it('마지막 행에서 아래로 나가지 않는다', async () => {
  const user = userEvent.setup()
  render(<Grid />)

  await user.click(screen.getByLabelText('3행 점수'))
  await user.keyboard('{ArrowDown}')
  expect(screen.getByLabelText('3행 점수')).toHaveFocus()
})

it('입력란에서 Enter는 다음 행으로 내려간다', async () => {
  const user = userEvent.setup()
  render(<Grid />)

  await user.click(screen.getByLabelText('1행 점수'))
  await user.keyboard('{Enter}')
  expect(screen.getByLabelText('2행 점수')).toHaveFocus()
})

// 버튼에서 Enter를 가로채면 키보드로 버튼을 누를 수 없게 된다.
it('버튼에서 Enter는 가로채지 않고 버튼을 누른다', async () => {
  const user = userEvent.setup()
  const pressed: string[] = []
  render(
    <KeyboardGrid>
      <Table>
        <TableBody>
          {[1, 2].map((row) => (
            <TableRow key={row}>
              <TableCell>
                <button type="button" onClick={() => pressed.push(`${row}행`)}>
                  {`${row}행 버튼`}
                </button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </KeyboardGrid>,
  )

  await user.click(screen.getByRole('button', { name: '1행 버튼' }))
  await user.keyboard('{Enter}')
  expect(pressed).toEqual(['1행', '1행'])
  expect(screen.getByRole('button', { name: '1행 버튼' })).toHaveFocus()
})

it('버튼에서도 방향키로는 행을 옮긴다', async () => {
  const user = userEvent.setup()
  render(<Grid />)

  await user.click(screen.getByRole('button', { name: '1행 버튼' }))
  await user.keyboard('{ArrowDown}')
  expect(screen.getByRole('button', { name: '2행 버튼' })).toHaveFocus()
})
