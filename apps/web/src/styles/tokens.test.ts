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
