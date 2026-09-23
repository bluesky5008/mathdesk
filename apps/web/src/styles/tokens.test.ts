import { readFileSync } from 'node:fs'

import { describe, expect, it } from 'vitest'

const read = (name: string) => readFileSync(new URL(name, import.meta.url), 'utf8')

// VER-30 (웹 측) — AC-31 / NFR-18.
// tokens.css는 웹(Tailwind v4)과 리포트 카드 템플릿(ADR-011)이 함께 읽는 단일 소스다.
// 카드 렌더러는 이 파일을 <style>에 그대로 인라인하므로 프레임워크 문법이 없어야 하고
// 외부 파일 없이 스스로 완결되어야 한다.
describe('디자인 토큰 단일 소스', () => {
  const tokens = read('./tokens.css')

  it('프레임워크 전용 문법 없이 순수 CSS로만 작성된다', () => {
    for (const directive of ['@tailwind', '@apply', '@theme', '@plugin', '@utility', '@variant', '@config', '@import']) {
      expect(tokens).not.toContain(directive)
    }
    expect(tokens).not.toMatch(/\btheme\(/)
  })

  it('색·타이포·간격·라운드·그림자 토큰을 정의한다', () => {
    const required = [
      '--md-color-bg',
      '--md-color-surface',
      '--md-color-fg',
      '--md-color-muted-fg',
      '--md-color-border',
      '--md-color-brand',
      '--md-color-brand-fg',
      '--md-color-accent',
      '--md-color-ring',
      '--md-color-success',
      '--md-color-warning',
      '--md-color-danger',
      '--md-color-chart-1',
      '--md-color-chart-2',
      '--md-font-sans',
      '--md-text-xs',
      '--md-text-sm',
      '--md-text-base',
      '--md-text-lg',
      '--md-text-xl',
      '--md-text-2xl',
      '--md-text-3xl',
      '--md-space-1',
      '--md-space-2',
      '--md-space-3',
      '--md-space-4',
      '--md-space-6',
      '--md-space-8',
      '--md-radius-sm',
      '--md-radius-md',
      '--md-radius-lg',
      '--md-shadow-sm',
      '--md-shadow-md',
    ]
    for (const name of required) {
      expect(tokens).toMatch(new RegExp(`^\\s*${name}\\s*:`, 'm'))
    }
  })

  it('참조하는 변수를 모두 자기 파일 안에서 정의한다', () => {
    const declared = new Set(Array.from(tokens.matchAll(/^\s*(--[\w-]+)\s*:/gm), (m) => m[1]))
    const referenced = Array.from(tokens.matchAll(/var\(\s*(--[\w-]+)/g), (m) => m[1])
    for (const name of referenced) {
      expect(declared).toContain(name)
    }
  })

  it('웹 스타일시트가 같은 토큰 파일을 참조한다', () => {
    expect(read('./app.css')).toContain('./tokens.css')
  })
})

// AC-34 / VER-32, AC-31 / VER-30 — ADR-012.
// 팔레트는 색만 덮어쓰고 스케일은 건드리지 않는다. 스케일이 웹과 카드의 공유 기반이므로
// 팔레트가 스케일을 재정의하는 순간 NFR-18이 깨진다.
describe('테마 팔레트', () => {
  const tokens = read('./tokens.css')
  const THEMES = ['dark', 'blue', 'green', 'pink']

  /** 선택자 블록 안에서 선언된 토큰 이름을 모은다. */
  const declaredIn = (selector: string) => {
    const match = tokens.match(new RegExp(`${selector}\\s*\\{([^}]*)\\}`))
    if (!match) return null
    return new Set(Array.from(match[1].matchAll(/^\s*(--[\w-]+)\s*:/gm), (m) => m[1]))
  }

  const isColor = (name: string) => name.startsWith('--md-color-')

  it('라이트는 :root이고 나머지 테마는 data-theme 속성으로 전환한다', () => {
    expect(declaredIn(':root')).not.toBeNull()
    for (const theme of THEMES) {
      expect(declaredIn(`\\[data-theme='${theme}'\\]`), `${theme} 팔레트가 없다`).not.toBeNull()
    }
  })

  it('5개 팔레트가 동일한 색 토큰 집합을 정의한다', () => {
    const base = [...declaredIn(':root')!].filter(isColor).sort()
    expect(base.length).toBeGreaterThan(0)
    for (const theme of THEMES) {
      const palette = [...declaredIn(`\\[data-theme='${theme}'\\]`)!].filter(isColor).sort()
      expect(palette, `${theme} 팔레트의 색 토큰이 라이트와 다르다`).toEqual(base)
    }
  })

  it('팔레트는 타이포·간격·라운드·그림자 스케일을 재정의하지 않는다', () => {
    for (const theme of THEMES) {
      const offenders = [...declaredIn(`\\[data-theme='${theme}'\\]`)!].filter((n) => !isColor(n))
      expect(offenders, `${theme} 팔레트가 스케일을 덮어쓴다`).toEqual([])
    }
  })
})
