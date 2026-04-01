import { Outlet } from "react-router"

import ThemeProvider from "@/components/ui/theme"
import TopBar from "@/components/ui/topbar"

export default function Layout() {
  return (
    <ThemeProvider>
      <TopBar />
      <main className="pt-16">
        <Outlet />
      </main>
    </ThemeProvider>
  )
}

export const LayoutErrorBoundary = () => {
  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-4">Page Not Found</h1>
      <p className="text-lg text-slate-700 dark:text-slate-300">
        The page you are looking for does not exist. Please check the URL and try
        again.
      </p>
    </div>
  )
}
