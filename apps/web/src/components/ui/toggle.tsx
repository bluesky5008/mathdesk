import { Button, type ButtonProps } from './button'
import { cn } from '../../lib/utils'

// 눌림 상태를 색으로 구분한다. 일일 입력 화면은 표를 눈으로 훑는 일이 많아
// 출결·등급을 글자 대신 색으로 먼저 읽을 수 있어야 한다.
const TONE = {
  brand: 'bg-brand text-brand-fg',
  success: 'bg-success text-brand-fg',
  warning: 'bg-warning text-warning-fg',
  danger: 'bg-danger text-brand-fg',
  neutral: 'bg-muted-fg text-brand-fg',
} as const

export type Tone = keyof typeof TONE

export function Toggle({
  pressed,
  tone = 'brand',
  className,
  ...props
}: Omit<ButtonProps, 'variant'> & { pressed: boolean; tone?: Tone }) {
  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      aria-pressed={pressed}
      className={cn(pressed && `${TONE[tone]} border-transparent`, className)}
      {...props}
    />
  )
}
