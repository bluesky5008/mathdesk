import { useEffect, useState } from 'react'

import { applyTheme, readTheme, THEMES, type Theme } from '../theme'
import { Select } from './ui/select'

export function ThemeSelect() {
  const [theme, setTheme] = useState<Theme>(readTheme)

  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  return (
    <Select
      aria-label="테마"
      className="h-8 text-xs"
      value={theme}
      onChange={(event) => setTheme(event.target.value as Theme)}
    >
      {THEMES.map(([value, label]) => (
        <option key={value} value={value}>
          {label}
        </option>
      ))}
    </Select>
  )
}
