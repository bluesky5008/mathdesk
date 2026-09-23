/** 테마는 사용자 개인 설정이다(FR-41, ADR-012). 서버에 보내지 않고 브라우저에만 둔다. */
export const THEMES = [
  ['light', '라이트'],
  ['dark', '다크'],
  ['blue', '블루'],
  ['green', '그린'],
  ['pink', '핑크'],
] as const

export type Theme = (typeof THEMES)[number][0]

// 값을 바꾸면 index.html의 첫 페인트 스크립트도 함께 고쳐야 한다.
export const THEME_STORAGE_KEY = 'mathdesk-theme'

const DEFAULT: Theme = 'light'

export function readTheme(): Theme {
  const stored = localStorage.getItem(THEME_STORAGE_KEY)
  return THEMES.some(([name]) => name === stored) ? (stored as Theme) : DEFAULT
}

export function applyTheme(theme: Theme) {
  localStorage.setItem(THEME_STORAGE_KEY, theme)
  document.documentElement.dataset.theme = theme
}
