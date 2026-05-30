import { useEffect } from 'react'

export default function Toast({ message, onClose, ms = 2800 }) {
  useEffect(() => {
    if (!message) return
    const t = setTimeout(onClose, ms)
    return () => clearTimeout(t)
  }, [message, ms, onClose])
  if (!message) return null
  return <div className="toast" role="status">{message}</div>
}
