import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

/** 조건부 클래스를 합치고 Tailwind 충돌은 뒤에 온 쪽이 이기게 한다. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
