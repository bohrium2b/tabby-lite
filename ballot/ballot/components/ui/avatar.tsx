
import { cn } from "@/lib/utils"

type AvatarProps = {
  src?: string
  alt?: string
  className?: string
}

export function Avatar({ src, alt = "User avatar", className }: AvatarProps) {
  return (
    <div className={cn("size-8 rounded-full bg-surface-container-highest overflow-hidden", className)}>
      {src ? (
        <img alt={alt} src={src} className="w-full h-full object-cover" />
      ) : (
        <div className="flex h-full w-full items-center justify-center text-sm font-medium text-muted-foreground">U</div>
      )}
    </div>
  )
}

export default Avatar
