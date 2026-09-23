import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it } from 'vitest'

import { ThemeSelect } from './ThemeSelect'

afterEach(() => {
  localStorage.clear()
  delete document.documentElement.dataset.theme
})

// AC-33 / VER-33 — 테마를 고르면 화면 색이 바뀌고 다시 접속해도 유지된다.
it('테마를 고르면 data-theme가 바뀌고 저장된다', async () => {
  const user = userEvent.setup()
  render(<ThemeSelect />)

  await user.selectOptions(screen.getByLabelText('테마'), 'pink')

  expect(document.documentElement.dataset.theme).toBe('pink')
  expect(localStorage.getItem('mathdesk-theme')).toBe('pink')
})

it('저장된 테마로 시작한다', () => {
  localStorage.setItem('mathdesk-theme', 'green')
  render(<ThemeSelect />)

  expect(screen.getByLabelText('테마')).toHaveValue('green')
  expect(document.documentElement.dataset.theme).toBe('green')
})

it('저장값이 알 수 없는 테마면 라이트로 떨어진다', () => {
  localStorage.setItem('mathdesk-theme', '없는테마')
  render(<ThemeSelect />)

  expect(screen.getByLabelText('테마')).toHaveValue('light')
})

it('다섯 가지 테마를 모두 고를 수 있다', () => {
  render(<ThemeSelect />)

  expect(
    Array.from(screen.getByLabelText('테마').querySelectorAll('option'), (o) => o.value),
  ).toEqual(['light', 'dark', 'blue', 'green', 'pink'])
})
