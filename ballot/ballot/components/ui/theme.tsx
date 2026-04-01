import * as React from "react"

type ThemeProviderProps = {
  children: React.ReactNode
}

export function ThemeProvider({ children }: ThemeProviderProps) {
  return (
    <div className="min-h-screen bg-slate-10 dark:bg-slate-950 text-slate-900 dark:text-slate-50">
      {children}
    </div>
  )
}

export const designTokens = {
  colors: {
    background: "bg-slate-10",
    backgroundDark: "dark:bg-slate-950",
    surfaceHighest: "bg-surface-container-highest",
  },
}

export default ThemeProvider
