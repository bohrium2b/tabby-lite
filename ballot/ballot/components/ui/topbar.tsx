
import { IconNotification, IconSettings } from "@tabler/icons-react"
import { NavLink } from "react-router"

import { Button } from "@/components/ui/button"
import Avatar from "@/components/ui/avatar"
import { cn } from "@/lib/utils"

export default function TopBar() {
  return (
    <header
      className={cn(
        "fixed top-0 w-full z-50 bg-slate-50/80 dark:bg-slate-950/80 backdrop-blur-xl shadow-sm shadow-slate-200/10 h-16 px-8 flex justify-between items-center w-full"
      )}
    >
      <div className="flex items-center gap-8">
        <span className="text-2xl font-bold tracking-tighter text-slate-900 dark:text-slate-50">Ballot</span>
        <nav className="hidden md:flex gap-6 font-manrope text-sm tracking-tight">
          <NavLink className={"text-slate-900 dark:text-slate-50 font-semibold border-b-2 border-slate-900 dark:border-slate-50 transition-colors duration-200"} to="/">
            Rounds
          </NavLink>
        </nav>
      </div>
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" aria-label="Notifications">
          <IconNotification data-icon="inline-start" />
        </Button>
        <Button variant="ghost" size="icon" aria-label="Settings">
          <IconSettings data-icon="inline-start" />
        </Button>
        <Avatar src="https://lh3.googleusercontent.com/aida-public/AB6AXuAJ80ggwT2x0evYPeAXYHXgOsjrOg8gi6IDsnVxfgdnFrC4wVqYTR8BmkfgReuoJK4F-TE2guiR0tQuBLKHb7Zfgi6ix042GwfMUFFYQQjNRi1bvOJhrizJxJfeJS0bZ7StcCB254RfjkwxKJXiJoHEFmazfI7Ziw667Jq0jaE6eyaV63-xzb0ZalSTAMXJza4eUe1nSyVMlgtApPA7DzZRT8qoOi2b7udFa28coHyHSBwCqy-RhIIVGP6iP70euHJs8C4yas8EX-g" />
      </div>
    </header>
  )
}
