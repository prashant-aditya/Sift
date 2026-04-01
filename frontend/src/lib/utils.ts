import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"
import { format, formatDistanceToNow } from "date-fns"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(date: string | Date, formatStr = "MMM d, yyyy"): string {
  const d = typeof date === "string" ? new Date(date) : date
  return format(d, formatStr)
}

export function formatRelativeTime(date: string | Date): string {
  const d = typeof date === "string" ? new Date(date) : date
  return formatDistanceToNow(d, { addSuffix: true })
}

export function truncateUrl(url: string | null | undefined, maxLength = 50): string {
  if (!url) return ""

  try {
    const urlObj = new URL(url)
    const domain = urlObj.hostname.replace("www.", "")
    const path = urlObj.pathname + urlObj.search
    
    if (domain.length + path.length <= maxLength) {
      return domain + path
    }
    
    const availableLength = maxLength - domain.length - 3
    if (availableLength > 0) {
      return domain + path.slice(0, availableLength) + "..."
    }
    
    return domain.slice(0, maxLength - 3) + "..."
  } catch {
    return url.slice(0, maxLength) + (url.length > maxLength ? "..." : "")
  }
}
